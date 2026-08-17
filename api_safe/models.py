from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="模型名称")
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="随机性参数")
    top_p: Optional[float] = Field(1.0, ge=0, le=1, description="核采样参数")
    max_tokens: Optional[int] = Field(None, ge=1, description="最大生成token数")
    stream: Optional[bool] = Field(False, description="是否流式输出")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止词")
    presence_penalty: Optional[float] = Field(0, ge=-2, le=2, description="存在惩罚")
    frequency_penalty: Optional[float] = Field(0, ge=-2, le=2, description="频率惩罚")
    logit_bias: Optional[Dict[str, float]] = Field(None, description="logit偏置")
    user: Optional[str] = Field(None, description="用户ID（向后兼容）")
    
    # 新增字段：用户身份标识
    user_id: Optional[str] = Field(None, description="用户ID，用于区分不同用户的日志记录")
    
    # 新增字段：会话管理
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话上下文管理")
    enable_context: Optional[bool] = Field(False, description="是否启用上下文拼接，默认为False（单轮对话）")
    max_context_turns: Optional[int] = Field(5, ge=1, le=20, description="最大上下文轮数，仅在enable_context=True时生效")


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class ChatCompletionStreamChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]


class ErrorResponse(BaseModel):
    error: Dict[str, Any]
    
    
class UserRequestLog(BaseModel):
    """用户请求日志模型"""
    timestamp: str
    user_id: Optional[str]
    session_id: Optional[str]  # 新增：会话ID
    request_id: str
    model: str
    messages: List[Dict[str, Any]]  # 改为Dict以支持clean_messages
    parameters: Dict[str, Any]
    api_key: Optional[str] = None  # 新增：使用的API key
    response_time: Optional[float] = None
    tokens_used: Optional[int] = None
    response_content: Optional[str] = None  # 新增：模型输出内容
    finish_reason: Optional[str] = None     # 新增：完成原因
    error: Optional[str] = None


# 拦截相关模型
class InterceptRequest(BaseModel):
    """拦截请求模型"""
    text: str = Field(..., description="要检查的文本内容")


class InterceptResponse(BaseModel):
    """拦截响应模型"""
    is_safe: bool = Field(..., description="是否安全")
    reason: str = Field(..., description="拦截原因")
    matched_keywords: Optional[List[str]] = Field(None, description="匹配到的关键词")
    score: Optional[float] = Field(None, description="置信度分数")
    safety_response: Optional[str] = Field(None, description="安全响应内容")
    bert_results: Optional[Dict[str, Any]] = Field(None, description="BERT检测结果详情")


class FrontInterceptResponse(InterceptResponse):
    """前拦截响应模型"""
    pass


class PostInterceptResponse(InterceptResponse):
    """后拦截响应模型"""
    pass


class SafetyFilterInfo(BaseModel):
    """安全过滤器信息"""
    triggered: bool = Field(..., description="是否触发")
    reason: str = Field(..., description="触发原因")
    filter_type: str = Field(..., description="过滤器类型: front_intercept 或 post_intercept")
    matched_keywords: Optional[List[str]] = Field(None, description="匹配到的关键词")
    confidence_score: Optional[float] = Field(None, description="置信度分数")


class SafetyChatCompletionResponse(ChatCompletionResponse):
    """带安全过滤器信息的聊天完成响应"""
    safety_filter: Optional[SafetyFilterInfo] = Field(None, description="安全过滤器信息") 