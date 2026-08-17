import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from config import settings
from models import ChatCompletionRequest, UserRequestLog
from vllm_client import VLLMClient
from logger_config import main_logger, user_logger
from conversation_manager import conversation_manager
from api_key_manager import api_key_manager

# 延迟导入拦截器，避免在显示帮助时因为缺少依赖而失败
front_interceptor = None
post_interceptor = None
streaming_interceptor = None
enhanced_front_interceptor = None
enhanced_post_interceptor = None
rag_enhanced_interceptor = None  # 添加RAG增强拦截器全局变量

# 创建FastAPI应用 - 根据配置控制文档端点
app = FastAPI(
    title="vLLM Proxy API",
    description="OpenAI兼容的vLLM代理API，支持基于Session的多轮对话管理",
    version="1.0.0",
    docs_url=None,  # 禁用默认的 /docs
    redoc_url=None,  # 禁用默认的 /redoc
    openapi_url=None if not settings.enable_docs else "/openapi.json"  # 根据配置控制OpenAPI schema
)

# 添加应用生命周期事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global front_interceptor, post_interceptor, streaming_interceptor
    global enhanced_front_interceptor, enhanced_post_interceptor, rag_enhanced_interceptor
    
    main_logger.info("vLLM Proxy API starting up...")
    
    # 初始化拦截器（使用统一的safe_api架构）
    # 总是尝试导入，避免运行时 NameError
    try:
        # 使用新的统一架构：RAG增强拦截器 + safe_api客户端
        from rag_interceptor import rag_enhanced_interceptor as rei
        from safe_api_client import safe_api_client as sac
        
        # 全局变量设置
        rag_enhanced_interceptor = rei
        front_interceptor = sac
        post_interceptor = sac
        enhanced_front_interceptor = rei
        enhanced_post_interceptor = rei
        
        main_logger.info("统一拦截架构已启用")
        main_logger.info(f"拦截模式: {'本地集成' if settings.use_local_intercept else '远程API'}")
        main_logger.info(f"前拦截: {'启用' if settings.enable_front_intercept else '禁用'}")
        main_logger.info(f"后拦截: {'启用' if settings.enable_post_intercept else '禁用'}")
        main_logger.info(f"RAG系统: {'启用' if settings.enable_rag else '禁用'}")
        
    except ImportError as e:
        main_logger.error(f"拦截器导入失败: {e}")
        main_logger.error("请确保拦截器模块正确安装")
        # 设置为 None，在使用时进行检查
        rag_enhanced_interceptor = None
        front_interceptor = None
        post_interceptor = None
        enhanced_front_interceptor = None
        enhanced_post_interceptor = None
        
        # 如果拦截器导入失败，禁用拦截功能
        if settings.enable_front_intercept or settings.enable_post_intercept:
            main_logger.warning("由于拦截器导入失败，将禁用拦截功能")
            settings.enable_front_intercept = False
            settings.enable_post_intercept = False

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    main_logger.info("vLLM Proxy API shutting down...")
    # 关闭vLLM客户端连接
    await vllm_client.close()

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全认证（可选）
security = HTTPBearer(auto_error=False)
vllm_client = VLLMClient()


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """验证API密钥（支持单个key和多key文件）"""
    # 如果禁用了API key验证，直接返回
    if settings.api_key is None and not settings.enable_multi_api_keys:
        return None
    
    if credentials is None:
        raise HTTPException(
            status_code=401, 
            detail="API key required. Please provide Authorization header with Bearer token."
        )
    
    api_key = credentials.credentials
    
    # 首先检查单个API key（向后兼容）
    if settings.api_key and api_key == settings.api_key:
        return api_key
    
    # 然后检查多API key文件
    if settings.enable_multi_api_keys:
        if api_key_manager.verify_api_key(api_key):
            return api_key
    
    # 如果都不匹配，返回错误
    raise HTTPException(
        status_code=401, 
        detail="Invalid API key. Please check your authorization token."
    )


def get_user_id_from_request(request: ChatCompletionRequest) -> str:
    """从请求中获取用户ID"""
    # 优先使用显式的user_id参数
    if request.user_id:
        return request.user_id
    
    # 向后兼容：如果没有user_id，尝试使用user字段
    if request.user:
        return request.user
    
    # 如果都没有，使用匿名用户
    return "anonymous"


async def create_safety_response(reason: str, safety_response: str = None) -> dict:
    """创建安全响应"""
    if safety_response is None:
        safety_response = settings.safety_response_message
    
    return {
        "id": f"chatcmpl-{str(uuid.uuid4())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "safety-filter",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": safety_response
            },
            "finish_reason": "content_filter"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(safety_response),
            "total_tokens": len(safety_response)
        }
    }


def log_user_request(request: ChatCompletionRequest, user_id: str, request_id: str, 
                    api_key: Optional[str] = None, response_time: Optional[float] = None, 
                    tokens_used: Optional[int] = None, response_content: Optional[str] = None, 
                    finish_reason: Optional[str] = None, error: Optional[str] = None, 
                    with_context: bool = False, context_turns: int = 0):
    """记录用户请求日志"""
    # 清理消息，移除None值
    clean_messages = []
    for msg in request.messages:
        msg_dict = msg.model_dump(exclude_none=True)
        clean_messages.append(msg_dict)
    
    # 获取用户统计信息
    user_stats = conversation_manager.get_user_stats(user_id)
    
    # 获取session统计信息（如果有session_id）
    session_stats = None
    if request.session_id:
        session_stats = conversation_manager.get_session_stats(request.session_id)
    
    log_data = UserRequestLog(
        timestamp=datetime.now().isoformat(),
        user_id=user_id,
        session_id=request.session_id,
        request_id=request_id,
        model=request.model,
        messages=clean_messages,  # 使用清理后的消息
        parameters={
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
            "stop": request.stop,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "enable_context": request.enable_context,
            "max_context_turns": request.max_context_turns,
            "user_id": request.user_id,  # 记录用户ID
        },
        api_key=api_key,  # 记录使用的API key
        response_time=response_time,
        tokens_used=tokens_used,
        response_content=response_content,
        finish_reason=finish_reason,
        error=error
    )
    
    # 扩展日志数据，包含用户统计和上下文信息
    log_dict = log_data.model_dump()
    log_dict.update({
        "user_stats": user_stats,
        "session_stats": session_stats,
        "with_context": with_context,
        "context_turns": context_turns,
        "total_user_turns": user_stats["total_turns"],
        "total_user_tokens": user_stats["total_tokens"]
    })
    
    user_logger.info("User request", extra=log_dict)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """请求中间件，记录请求日志"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    main_logger.info(f"Request {request_id}: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    main_logger.info(f"Request {request_id} completed in {process_time:.3f}s with status {response.status_code}")
    
    return response


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# 受保护的文档端点
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema(request: Request):
    """获取 OpenAPI schema（根据配置决定是否需要认证）"""
    if not settings.enable_docs:
        raise HTTPException(
            status_code=404,
            detail="API documentation is disabled"
        )
    
    # 如果需要认证，验证API key
    if settings.docs_require_auth and (settings.api_key or settings.enable_multi_api_keys):
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="API documentation requires authentication. Please provide Authorization header."
            )
        
        token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else ""
        
        # 检查单个API key
        if settings.api_key and token == settings.api_key:
            pass
        # 检查多API key文件
        elif settings.enable_multi_api_keys and api_key_manager.verify_api_key(token):
            pass
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key for documentation access"
            )
    
    return app.openapi()


@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(request: Request):
    """受保护的 Swagger UI 文档"""
    if not settings.enable_docs:
        raise HTTPException(
            status_code=404,
            detail="API documentation is disabled"
        )
    
    # 如果需要认证，验证API key
    if settings.docs_require_auth and settings.api_key:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="API documentation requires authentication. Please provide Authorization header."
            )
        
        token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else ""
        if token != settings.api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key for documentation access"
            )
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(request: Request):
    """受保护的 ReDoc 文档"""
    if not settings.enable_docs:
        raise HTTPException(
            status_code=404,
            detail="API documentation is disabled"
        )
    
    # 如果需要认证，验证API key
    if settings.docs_require_auth and (settings.api_key or settings.enable_multi_api_keys):
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="API documentation requires authentication. Please provide Authorization header."
            )
        
        token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else ""
        
        # 检查单个API key
        if settings.api_key and token == settings.api_key:
            pass
        # 检查多API key文件
        elif settings.enable_multi_api_keys and api_key_manager.verify_api_key(token):
            pass
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key for documentation access"
            )
    
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
    )


@app.get("/v1/models")
async def list_models(api_key: Optional[str] = Depends(verify_api_key)):
    """列出可用模型（转发到vLLM）"""
    try:
        client = await vllm_client._get_client()
        response = await client.get(
            f"{settings.vllm_api_base}/v1/models",
            headers=vllm_client._get_headers()
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        main_logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")


@app.get("/v1/users/{user_id}/stats")
async def get_user_stats(user_id: str, api_key: Optional[str] = Depends(verify_api_key)):
    """获取用户统计信息"""
    stats = conversation_manager.get_user_stats(user_id)
    return stats


@app.get("/v1/users/{user_id}/sessions")
async def get_user_sessions(user_id: str, api_key: Optional[str] = Depends(verify_api_key)):
    """获取用户的所有会话"""
    sessions = conversation_manager.get_user_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions}


@app.get("/v1/sessions/{session_id}/stats")
async def get_session_stats(session_id: str, api_key: Optional[str] = Depends(verify_api_key)):
    """获取会话统计信息"""
    stats = conversation_manager.get_session_stats(session_id)
    return stats


@app.get("/v1/sessions/{session_id}/history")
async def get_session_history(
    session_id: str, 
    max_turns: int = 10,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """获取会话对话历史"""
    history = conversation_manager.get_session_history(session_id, max_turns)
    return {"session_id": session_id, "history": [msg.model_dump() for msg in history]}


# API Key 管理端点
@app.get("/v1/admin/api-keys")
async def list_api_keys(api_key: Optional[str] = Depends(verify_api_key)):
    """获取所有API key信息（管理员功能）"""
    keys_info = api_key_manager.get_all_keys_info()
    # 隐藏完整的API key，只显示前8位
    for key, info in keys_info.items():
        info["key_preview"] = key[:8] + "..." if len(key) > 8 else key
        info["full_key"] = key  # 保留完整key用于管理
    return {"api_keys": keys_info}


@app.get("/v1/admin/api-keys/stats")
async def get_api_keys_stats(api_key: Optional[str] = Depends(verify_api_key)):
    """获取API key统计信息（管理员功能）"""
    return api_key_manager.get_stats()


@app.post("/v1/admin/api-keys")
async def add_api_key(
    key: str,
    description: str = "",
    api_key: Optional[str] = Depends(verify_api_key)
):
    """添加新的API key（管理员功能）"""
    success = api_key_manager.add_api_key(key, description)
    if success:
        return {"message": "API key added successfully", "key_preview": key[:8] + "..."}
    else:
        raise HTTPException(status_code=400, detail="Failed to add API key or key already exists")


@app.delete("/v1/admin/api-keys/{key}")
async def remove_api_key(
    key: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """移除API key（管理员功能）"""
    success = api_key_manager.remove_api_key(key)
    if success:
        return {"message": "API key removed successfully"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")


@app.put("/v1/admin/api-keys/{key}/disable")
async def disable_api_key(
    key: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """禁用API key（管理员功能）"""
    success = api_key_manager.disable_api_key(key)
    if success:
        return {"message": "API key disabled successfully"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")


@app.put("/v1/admin/api-keys/{key}/enable")
async def enable_api_key(
    key: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """启用API key（管理员功能）"""
    success = api_key_manager.enable_api_key(key)
    if success:
        return {"message": "API key enabled successfully"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")


@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """创建聊天完成接口（兼容OpenAI格式）"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 获取用户ID（使用API key或匿名）
    user_id = get_user_id_from_request(request)
    
    # 判断是否启用多轮对话上下文
    enable_context = request.enable_context or False  # 默认为False（单轮对话）
    session_id = request.session_id
    max_context_turns = request.max_context_turns or 5
    
    # 验证多轮对话参数
    if enable_context and not session_id:
        raise HTTPException(
            status_code=400, 
            detail="session_id is required when enable_context=True"
        )
    
    # 日志记录对话类型
    conversation_type = "multi-turn" if enable_context and session_id else "single-turn"
    main_logger.info(
        f"Chat completion request {request_id}: "
        f"user={user_id}, model={request.model}, stream={request.stream}, "
        f"type={conversation_type}, session_id={session_id}"
    )
    
    # 获取原始用户消息（用于记录）
    original_messages = request.messages.copy()
    user_message = original_messages[-1].content if original_messages and original_messages[-1].role == "user" else ""
    
    # 前拦截检查（使用统一的RAG增强拦截器）
    rag_context = None  # 用于存储RAG检索的上下文
    if settings.enable_front_intercept and user_message and rag_enhanced_interceptor:
        try:
            main_logger.info(f"Request {request_id}: 执行RAG增强前拦截检查")
            
            # 使用RAG增强拦截器，它会：
            # 1. 调用safe_api进行完整前拦截（高敏词+BERT双阈值+次高敏词）
            # 2. 如果适合，进行RAG检索
            intercept_result = await rag_enhanced_interceptor.intercept_with_rag(user_message)
            
            if not intercept_result.is_safe:
                main_logger.info(f"Request {request_id}: 前拦截触发 - {intercept_result.reason}")
                if intercept_result.matched_keywords:
                    main_logger.info(f"Request {request_id}: 匹配关键词: {intercept_result.matched_keywords}")
                # 使用统一的安全响应消息
                safety_response_dict = await create_safety_response(
                    "内容安全拦截", 
                    settings.safety_response_message
                )
                
                # 记录前拦截日志
                response_time = time.time() - start_time
                log_user_request(
                    ChatCompletionRequest(
                        model=request.model,
                        messages=original_messages,
                        session_id=session_id,
                        enable_context=enable_context,
                        max_context_turns=max_context_turns,
                        **{k: v for k, v in request.model_dump().items() 
                           if k not in ['model', 'messages', 'session_id', 'enable_context', 'max_context_turns']}
                    ), 
                    user_id, 
                    request_id, 
                    api_key,
                    response_time, 
                    safety_response_dict["usage"]["total_tokens"], 
                    safety_response_dict["choices"][0]["message"]["content"], 
                    "content_filter",
                    f"前拦截触发: {intercept_result.reason}",
                    with_context=False,
                    context_turns=0
                )
                
                return safety_response_dict
            else:
                # 前拦截通过，检查是否有RAG上下文
                if hasattr(intercept_result, 'rag_context') and intercept_result.rag_context:
                    rag_context = intercept_result.rag_context
                    main_logger.info(f"Request {request_id}: 获得RAG上下文，长度: {len(rag_context)}")
                
        except Exception as e:
            main_logger.error(f"Request {request_id}: RAG增强前拦截检查出错: {e}")
            # 前拦截出错时，为了安全起见，继续执行但记录错误
    
    # 如果启用上下文且有session_id，则拼接历史对话
    context_turns = 0
    if enable_context and session_id and user_id != "anonymous":
        context_messages = conversation_manager.get_session_context(
            session_id,
            user_id, 
            request.messages, 
            max_context_turns
        )
        # 计算添加的上下文轮数
        context_turns = len(context_messages) - len(request.messages)
        request.messages = context_messages
        
        main_logger.info(
            f"Request {request_id}: Added {context_turns} context turns for session {session_id}"
        )
    
    # 如果有RAG上下文，替换用户消息为RAG增强的prompt
    if rag_context:
        try:
            from rag_prompt_template import rag_prompt_template
            
            # 创建RAG增强的消息
            rag_messages = rag_prompt_template.create_rag_messages(user_message, rag_context)
            
            # 如果有上下文对话，保留历史对话，只替换最后一条用户消息
            if enable_context and len(request.messages) > 1:
                # 保留除最后一条消息外的所有历史对话
                request.messages = request.messages[:-1] + [
                    {"role": "user", "content": rag_messages[-1]["content"]}
                ]
            else:
                # 使用完整的RAG消息（包含system prompt）
                request.messages = [
                    {"role": msg["role"], "content": msg["content"]} 
                    for msg in rag_messages
                ]
            
            main_logger.info(f"Request {request_id}: 已应用RAG增强prompt")
            
        except Exception as e:
            main_logger.error(f"Request {request_id}: RAG prompt处理失败: {e}")
            # 失败时继续使用原始消息
    
    try:
        if request.stream:
            # 流式响应
            main_logger.info(f"Starting stream response for request {request_id}")
            
            # 创建流式日志回调函数
            def stream_log_callback(response_time: float, tokens_used: int, response_content: str, finish_reason: str, error: Optional[str] = None):
                # 记录用户请求日志
                log_user_request(
                    ChatCompletionRequest(
                        model=request.model,
                        messages=original_messages,  # 使用原始消息记录
                        session_id=session_id,
                        enable_context=enable_context,
                        max_context_turns=max_context_turns,
                        **{k: v for k, v in request.model_dump().items() 
                           if k not in ['model', 'messages', 'session_id', 'enable_context', 'max_context_turns']}
                    ), 
                    user_id, 
                    request_id, 
                    api_key,  # 记录使用的API key
                    response_time, 
                    tokens_used, 
                    response_content, 
                    finish_reason, 
                    error,
                    with_context=enable_context and context_turns > 0,
                    context_turns=context_turns
                )
                
                # 如果成功且启用了多轮对话，记录对话历史
                if not error and enable_context and session_id and user_id != "anonymous" and response_content:
                    conversation_manager.add_conversation_turn(
                        session_id,
                        user_id,
                        request_id,
                        user_message,
                        response_content,
                        request.model,
                        tokens_used or 0,
                        response_time,
                        finish_reason or "unknown"
                    )
            
            # 获取原始流式响应
            original_stream_response = await vllm_client.create_chat_completion_stream(request, stream_log_callback)
            
            # 如果启用后拦截，包装流式响应
            if settings.enable_post_intercept:
                # 创建拦截包装的流式响应
                async def intercepted_stream_generator():
                    async for chunk in streaming_interceptor.intercept_stream(
                        original_stream_response.body_iterator, 
                        request_id
                    ):
                        yield chunk
                
                from fastapi.responses import StreamingResponse
                return StreamingResponse(
                    intercepted_stream_generator(),
                    media_type="text/plain",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Content-Type": "text/plain; charset=utf-8"
                    }
                )
            else:
                # 没有启用后拦截，直接返回原始响应
                return original_stream_response
        else:
            # 非流式响应
            response = await vllm_client.create_chat_completion(request)
            response_time = time.time() - start_time
            
            # 提取响应信息
            tokens_used = response.usage.total_tokens if response.usage else None
            response_content = response.choices[0].message.content if response.choices else None
            finish_reason = response.choices[0].finish_reason if response.choices else None
            
            # 后拦截检查（使用统一的safe_api客户端）
            if settings.enable_post_intercept and response_content and rag_enhanced_interceptor:
                try:
                    main_logger.info(f"Request {request_id}: 执行后拦截检查")
                    
                    # 使用RAG增强拦截器的后拦截功能（直接调用safe_api）
                    post_intercept_result = await rag_enhanced_interceptor.post_intercept(response_content)
                    
                    if not post_intercept_result.is_safe:
                        main_logger.info(f"Request {request_id}: 后拦截触发 - {post_intercept_result.reason}")
                        if post_intercept_result.score is not None:
                            main_logger.info(f"Request {request_id}: BERT置信度: {post_intercept_result.score:.4f}")
                        
                        # 创建安全响应替换原响应（使用统一的安全响应消息）
                        safety_response_dict = await create_safety_response(
                            "内容安全拦截", 
                            settings.safety_response_message
                        )
                        
                        # 记录后拦截日志（使用原始响应的token统计）
                        log_user_request(
                            ChatCompletionRequest(
                                model=request.model,
                                messages=original_messages,
                                session_id=session_id,
                                enable_context=enable_context,
                                max_context_turns=max_context_turns,
                                **{k: v for k, v in request.model_dump().items() 
                                   if k not in ['model', 'messages', 'session_id', 'enable_context', 'max_context_turns']}
                            ), 
                            user_id, 
                            request_id, 
                            api_key,
                            response_time, 
                            tokens_used, 
                            response_content,  # 记录被拦截的原始内容
                            "content_filter",
                            f"后拦截触发: {post_intercept_result.reason}",
                            with_context=enable_context and context_turns > 0,
                            context_turns=context_turns
                        )
                        
                        return safety_response_dict
                except Exception as e:
                    main_logger.error(f"Request {request_id}: 后拦截检查出错: {e}")
                    # 后拦截出错时，为了安全起见，返回安全响应
                    if settings.enable_post_intercept:  # 只有在启用后拦截时才这样做
                        safety_response_dict = await create_safety_response(
                            f"后拦截检查出错: {str(e)}"
                        )
                        return safety_response_dict
            
            # 记录用户请求
            log_user_request(
                ChatCompletionRequest(
                    model=request.model,
                    messages=original_messages,  # 使用原始消息记录
                    session_id=session_id,
                    enable_context=enable_context,
                    max_context_turns=max_context_turns,
                    **{k: v for k, v in request.model_dump().items() 
                       if k not in ['model', 'messages', 'session_id', 'enable_context', 'max_context_turns']}
                ), 
                user_id, 
                request_id, 
                api_key,  # 记录使用的API key
                response_time, 
                tokens_used, 
                response_content, 
                finish_reason,
                with_context=enable_context and context_turns > 0,
                context_turns=context_turns
            )
            
            # 如果启用了多轮对话，记录对话历史
            if enable_context and session_id and user_id != "anonymous" and response_content:
                conversation_manager.add_conversation_turn(
                    session_id,
                    user_id,
                    request_id,
                    user_message,
                    response_content,
                    request.model,
                    tokens_used or 0,
                    response_time,
                    finish_reason or "unknown"
                )
            
            main_logger.info(f"Request {request_id} completed successfully in {response_time:.3f}s")
            return response
            
    except HTTPException as e:
        response_time = time.time() - start_time
        error_msg = str(e.detail)
        
        # 记录错误
        log_user_request(
            ChatCompletionRequest(
                model=request.model,
                messages=original_messages,
                session_id=session_id,
                enable_context=enable_context,
                **{k: v for k, v in request.model_dump().items() 
                   if k not in ['model', 'messages', 'session_id', 'enable_context']}
            ), 
            user_id, 
            request_id, 
            api_key,  # 记录使用的API key
            response_time, 
            None, 
            None, 
            None, 
            error_msg,
            with_context=enable_context and context_turns > 0,
            context_turns=context_turns
        )
        main_logger.error(f"Request {request_id} failed: {error_msg}")
        
        raise e
    except Exception as e:
        response_time = time.time() - start_time
        error_msg = f"Unexpected error: {str(e)}"
        
        # 记录错误
        log_user_request(
            ChatCompletionRequest(
                model=request.model,
                messages=original_messages,
                session_id=session_id,
                enable_context=enable_context,
                **{k: v for k, v in request.model_dump().items() 
                   if k not in ['model', 'messages', 'session_id', 'enable_context']}
            ), 
            user_id, 
            request_id, 
            api_key,  # 记录使用的API key
            response_time, 
            None, 
            None, 
            None, 
            error_msg,
            with_context=enable_context and context_turns > 0,
            context_turns=context_turns
        )
        main_logger.error(f"Request {request_id} failed with unexpected error: {str(e)}")
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "http_error",
                "code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    from fastapi.responses import JSONResponse
    main_logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_error",
                "code": 500
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="vLLM Proxy API with Content Intercept Support")
    parser.add_argument("--enable-front-intercept", action="store_true", help="启用前拦截")
    parser.add_argument("--enable-post-intercept", action="store_true", help="启用后拦截")
    parser.add_argument("--front-intercept-url", type=str, help="前拦截API地址")
    parser.add_argument("--post-intercept-url", type=str, help="后拦截API地址")
    parser.add_argument("--intercept-timeout", type=float, help="拦截API超时时间（秒）")
    parser.add_argument("--host", type=str, help="服务绑定地址")
    parser.add_argument("--port", type=int, help="服务绑定端口")
    parser.add_argument("--workers", type=int, help="工作进程数")
    
    args = parser.parse_args()
    
    # 根据命令行参数覆盖配置
    config_updates = {}
    
    if args.enable_front_intercept:
        config_updates['enable_front_intercept'] = True
        config_updates['use_local_intercept'] = False  # 使用远程API模式
    if args.enable_post_intercept:
        config_updates['enable_post_intercept'] = True
        config_updates['use_local_intercept'] = False  # 使用远程API模式
    if args.front_intercept_url:
        config_updates['front_intercept_url'] = args.front_intercept_url
    if args.post_intercept_url:
        config_updates['post_intercept_url'] = args.post_intercept_url
    if args.intercept_timeout:
        config_updates['intercept_timeout'] = args.intercept_timeout
    if args.host:
        config_updates['host'] = args.host
    if args.port:
        config_updates['port'] = args.port
    if args.workers:
        config_updates['workers'] = args.workers
    
    # 应用配置更新
    settings.update_from_args(**config_updates)
    
    main_logger.info(f"Starting vLLM Proxy API server on {settings.host}:{settings.port}")
    main_logger.info(f"vLLM API base URL: {settings.vllm_api_base}")
    main_logger.info(f"Worker进程数: {settings.workers}")
    main_logger.info(f"最大连接数: {settings.max_connections}")
    main_logger.info(f"保持活跃连接数: {settings.max_keepalive_connections}")
    
    # 显示拦截配置
    if settings.enable_front_intercept:
        main_logger.info(f"前拦截已启用: {settings.front_intercept_url}")
    if settings.enable_post_intercept:
        main_logger.info(f"后拦截已启用: {settings.post_intercept_url}")
    if settings.enable_front_intercept or settings.enable_post_intercept:
        main_logger.info(f"拦截超时时间: {settings.intercept_timeout}秒")
        main_logger.info(f"拦截模式: {'本地集成' if settings.use_local_intercept else '远程API'}")
    
    uvicorn.run(
        "main:app" if settings.workers > 1 else app,
        host=settings.host,
        port=settings.port,
        workers=settings.workers if settings.workers > 1 else None,
        reload=False,
        log_level=settings.log_level.lower(),
        access_log=True
    ) 