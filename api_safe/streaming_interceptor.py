import json
import asyncio
import uuid
import time
from typing import AsyncGenerator, Any, Dict, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from logger_config import main_logger
from safe_api_client import safe_api_client
from config import settings


class StreamingInterceptor:
    """流式响应拦截器"""
    
    def __init__(self):
        # 注意：安全响应消息由主API统一管理，这里不需要存储
        pass
    
    async def intercept_stream(self, stream_generator: AsyncGenerator[str, None], 
                             request_id: str) -> AsyncGenerator[str, None]:
        """拦截流式响应"""
        if not settings.enable_post_intercept:
            # 如果未启用后拦截，直接转发
            async for chunk in stream_generator:
                yield chunk
            return
        
        # 收集完整响应内容
        collected_content = ""
        chunks = []
        
        try:
            async for chunk in stream_generator:
                chunks.append(chunk)
                
                # 解析chunk内容
                if chunk.startswith("data: "):
                    data_str = chunk[6:].strip()
                    if data_str == "[DONE]":
                        continue
                    
                    try:
                        chunk_data = json.loads(data_str)
                        if "choices" in chunk_data and chunk_data["choices"]:
                            choice = chunk_data["choices"][0]
                            if "delta" in choice and "content" in choice["delta"]:
                                content = choice["delta"]["content"]
                                if content:
                                    collected_content += content
                    except json.JSONDecodeError:
                        continue
            
            # 执行后拦截检查
            if collected_content.strip():
                main_logger.info(f"Request {request_id}: 执行流式响应后拦截检查")
                post_intercept_result = await safe_api_client.post_intercept(collected_content)
                
                if not post_intercept_result.is_safe:
                    main_logger.info(f"Request {request_id}: 流式响应后拦截触发 - {post_intercept_result.reason}")
                    if post_intercept_result.score is not None:
                        main_logger.info(f"Request {request_id}: BERT置信度: {post_intercept_result.score:.4f}")
                    
                    # 如果后拦截触发，返回安全响应（使用主API的统一消息）
                    safety_message = settings.safety_response_message
                    safety_chunks = self._create_safety_stream_chunks(safety_message)
                    for safety_chunk in safety_chunks:
                        yield safety_chunk
                    return
            
            # 如果后拦截通过，返回原始内容
            for chunk in chunks:
                yield chunk
                
        except Exception as e:
            main_logger.error(f"Request {request_id}: 流式响应后拦截检查出错: {e}")
            
            # 出错时返回安全响应
            safety_chunks = self._create_safety_stream_chunks(
                f"后拦截检查出错，为确保安全已中断响应。"
            )
            for safety_chunk in safety_chunks:
                yield safety_chunk
    
    def _create_safety_stream_chunks(self, safety_message: str) -> list:
        """创建安全响应的流式chunks"""
        chunks = []
        
        # 创建初始chunk
        initial_chunk = {
            "id": f"chatcmpl-{str(uuid.uuid4())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "safety-filter",
            "choices": [{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": None
            }]
        }
        chunks.append(f"data: {json.dumps(initial_chunk)}\n\n")
        
        # 将安全消息分块发送
        for char in safety_message:
            content_chunk = {
                "id": initial_chunk["id"],
                "object": "chat.completion.chunk",
                "created": initial_chunk["created"],
                "model": "safety-filter",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": char
                    },
                    "finish_reason": None
                }]
            }
            chunks.append(f"data: {json.dumps(content_chunk)}\n\n")
        
        # 创建结束chunk
        final_chunk = {
            "id": initial_chunk["id"],
            "object": "chat.completion.chunk",
            "created": initial_chunk["created"],
            "model": "safety-filter",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "content_filter"
            }]
        }
        chunks.append(f"data: {json.dumps(final_chunk)}\n\n")
        chunks.append("data: [DONE]\n\n")
        
        return chunks


# 创建全局实例
streaming_interceptor = StreamingInterceptor()
