import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # vLLM API配置
    vllm_api_base: str = os.getenv("VLLM_API_BASE", "http://localhost:8000")
    vllm_api_key: Optional[str] = os.getenv("VLLM_API_KEY", None)
    
    # 服务配置
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8001"))
    
    # 并发配置
    workers: int = int(os.getenv("WORKERS", "1"))  # worker进程数
    max_connections: int = int(os.getenv("MAX_CONNECTIONS", "200"))  # 最大连接数
    max_keepalive_connections: int = int(os.getenv("MAX_KEEPALIVE_CONNECTIONS", "100"))  # 保持活跃连接数
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/api.log")
    user_log_file: str = os.getenv("USER_LOG_FILE", "logs/user_requests.log")
    
    # API配置
    api_key: Optional[str] = os.getenv("API_KEY", None)  # 可选的API密钥验证（单个key，向后兼容）
    api_keys_file: str = os.getenv("API_KEYS_FILE", "api_keys.json")  # 多API key文件路径
    enable_multi_api_keys: bool = os.getenv("ENABLE_MULTI_API_KEYS", "true").lower() in ("true", "1", "yes")  # 是否启用多API key支持
    
    # 文档安全配置
    enable_docs: bool = os.getenv("ENABLE_DOCS", "true").lower() in ("true", "1", "yes")  # 是否启用API文档
    docs_require_auth: bool = os.getenv("DOCS_REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")  # 文档是否需要认证
    
    # 内容拦截配置
    enable_front_intercept: bool = os.getenv("ENABLE_FRONT_INTERCEPT", "false").lower() in ("true", "1", "yes")  # 是否启用前拦截
    enable_post_intercept: bool = os.getenv("ENABLE_POST_INTERCEPT", "false").lower() in ("true", "1", "yes")  # 是否启用后拦截
    front_intercept_url: str = os.getenv("FRONT_INTERCEPT_URL", "http://localhost:8001/intercept")  # 前拦截API地址
    post_intercept_url: str = os.getenv("POST_INTERCEPT_URL", "http://localhost:8002/intercept")  # 后拦截API地址
    
    # 拦截模型路径配置（本地集成模式）
    use_local_intercept: bool = os.getenv("USE_LOCAL_INTERCEPT", "true").lower() in ("true", "1", "yes")  # 是否使用本地集成模式
    model_front_path: str = os.getenv("MODEL_FRONT_PATH", "./safe_api/models/front_model")  # 前拦截模型路径
    model_post_path: str = os.getenv("MODEL_POST_PATH", "./safe_api/models/post_model")  # 后拦截模型路径
    blacklist_1w_path: str = os.getenv("BLACKLIST_1W_PATH", "./safe_api/data/blacklist_1w.json")  # 1w黑名单路径
    high_sensitive_keywords_path: str = os.getenv("HIGH_SENSITIVE_KEYWORDS_PATH", "./safe_api/data/high_sensitive_keywords.json")  # 高敏感词路径
    
    # 拦截超时配置
    intercept_timeout: float = float(os.getenv("INTERCEPT_TIMEOUT", "5.0"))  # 拦截API超时时间（秒）
    
    # RAG系统配置
    enable_rag: bool = os.getenv("ENABLE_RAG", "false").lower() in ("true", "1", "yes")  # 是否启用RAG系统
    rag_service_url: str = os.getenv("RAG_SERVICE_URL", "http://localhost:8000/retrieve")  # RAG检索服务地址
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))  # RAG检索返回的top-k数量
    rag_timeout: float = float(os.getenv("RAG_TIMEOUT", "10.0"))  # RAG服务超时时间（秒）
    
    # BERT双阈值配置
    bert_front_high_threshold: float = float(os.getenv("BERT_FRONT_HIGH_THRESHOLD", "0.97"))  # BERT前拦截高阈值
    bert_front_low_threshold: float = float(os.getenv("BERT_FRONT_LOW_THRESHOLD", "2e-5"))  # BERT前拦截低阈值  
    bert_post_threshold: float = float(os.getenv("BERT_POST_THRESHOLD", "0.5"))  # BERT后拦截阈值
    
    # 次高敏感词路径
    medium_sensitive_keywords_path: str = os.getenv("MEDIUM_SENSITIVE_KEYWORDS_PATH", "./safe_api/data/high_sensitive_keywords-2.json")  # 次高敏感词路径
    
    # 统一安全响应消息配置
    safety_response_message: str = os.getenv(
        "SAFETY_RESPONSE_MESSAGE", 
        "根据相关法律法规以及道德伦理规范，我无法提供关于这个问题的回答，建议换一个话题。"
    )  # 统一的安全拒绝话术
    
    class Config:
        env_file = ".env"
        protected_namespaces = ('settings_',)  # 避免模型字段冲突警告
    
    def update_from_args(self, **kwargs):
        """从命令行参数更新配置"""
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)


settings = Settings() 