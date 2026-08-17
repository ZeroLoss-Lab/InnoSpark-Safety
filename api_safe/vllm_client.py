import httpx
import json
import time
import uuid
from typing import AsyncIterator, Dict, Any, Callable, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from config import settings
from models import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse
from logger_config import main_logger


class VLLMClient:
    def __init__(self):
        self.base_url = settings.vllm_api_base.rstrip('/')
        self.api_key = settings.vllm_api_key
        
        # 根据并发数动态调整超时 - 高并发时适当延长超时
        if settings.max_connections >= 600:
            self.timeout = 600.0  # 10分钟超时，适应高并发场景
        else:
            self.timeout = 300.0  # 5分钟超时
        
        # 配置连接池限制以支持高并发
        self.limits = httpx.Limits(
            max_keepalive_connections=settings.max_keepalive_connections,  # 从配置读取
            max_connections=settings.max_connections,                      # 从配置读取  
            keepalive_expiry=30.0                                          # 连接保持时间
        )
        
        # 创建持久化的异步客户端，复用连接
        self._client = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建AsyncClient实例"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=self.limits,
                http2=True  # 启用HTTP/2支持（如果后端支持）
            )
        return self._client
    
    async def close(self):
        """关闭客户端连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    def _prepare_vllm_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        """将请求转换为vLLM API格式"""
        # 处理消息，排除None值
        messages = []
        for msg in request.messages:
            msg_dict = msg.model_dump(exclude_none=True)
            messages.append(msg_dict)
        
        vllm_request = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream,
        }
        
        # 添加可选参数
        if request.max_tokens is not None:
            vllm_request["max_tokens"] = request.max_tokens
        if request.stop is not None:
            vllm_request["stop"] = request.stop
        if request.presence_penalty is not None:
            vllm_request["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            vllm_request["frequency_penalty"] = request.frequency_penalty
        if request.logit_bias is not None:
            vllm_request["logit_bias"] = request.logit_bias
        if request.user is not None:
            vllm_request["user"] = request.user
            
        return vllm_request
    
    async def create_chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """创建聊天完成（非流式）"""
        vllm_request = self._prepare_vllm_request(request)
        vllm_request["stream"] = False
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=vllm_request,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return ChatCompletionResponse(**response.json())
                
        except httpx.HTTPStatusError as e:
            main_logger.error(f"vLLM API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"vLLM API error: {e.response.text}"
            )
        except Exception as e:
            main_logger.error(f"Unexpected error calling vLLM API: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def create_chat_completion_stream(
        self, 
        request: ChatCompletionRequest,
        log_callback: Optional[Callable[[float, int, str, str, Optional[str]], None]] = None
    ) -> StreamingResponse:
        """创建聊天完成（流式）"""
        vllm_request = self._prepare_vllm_request(request)
        vllm_request["stream"] = True
        
        async def stream_generator():
            start_time = time.time()
            full_content = ""
            finish_reason = None
            total_tokens = 0
            error_occurred = None
            
            try:
                client = await self._get_client()
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json=vllm_request,
                    headers=self._get_headers()
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data = line[6:]  # 移除 "data: " 前缀
                                if data.strip() == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                try:
                                    # 验证和解析JSON
                                    chunk_data = json.loads(data)
                                    
                                    # 提取内容和相关信息
                                    if "choices" in chunk_data and chunk_data["choices"]:
                                        choice = chunk_data["choices"][0]
                                        if "delta" in choice and "content" in choice["delta"]:
                                            content = choice["delta"]["content"]
                                            if content:
                                                full_content += content
                                        
                                        # 检查finish_reason
                                        if "finish_reason" in choice and choice["finish_reason"]:
                                            finish_reason = choice["finish_reason"]
                                            # 流式响应结束，立即记录日志
                                            if log_callback and finish_reason:
                                                response_time = time.time() - start_time
                                                # 估算token数量
                                                total_tokens = len(full_content) if any('\u4e00' <= c <= '\u9fff' for c in full_content) else int(len(full_content.split()) * 1.3)
                                                log_callback(response_time, total_tokens, full_content, finish_reason, None)
                                    
                                    yield f"data: {data}\n\n"
                                    
                                except json.JSONDecodeError:
                                    main_logger.warning(f"Invalid JSON in stream: {data}")
                                    continue
                                    
            except httpx.HTTPStatusError as e:
                error_occurred = f"vLLM API error: {e.response.status_code}"
                main_logger.error(f"vLLM API stream error: {e.response.status_code}")
                error_data = {
                    "error": {
                        "message": f"vLLM API error: {e.response.status_code}",
                        "type": "api_error",
                        "code": e.response.status_code
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except Exception as e:
                error_occurred = f"Internal server error: {str(e)}"
                main_logger.error(f"Unexpected error in stream: {str(e)}")
                error_data = {
                    "error": {
                        "message": f"Internal server error: {str(e)}",
                        "type": "internal_error",
                        "code": 500
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            finally:
                # 如果发生错误且还没有记录日志，则记录错误日志
                if log_callback and error_occurred:
                    response_time = time.time() - start_time
                    log_callback(response_time, 0, "", "", error_occurred)
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        ) 