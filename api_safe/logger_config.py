import logging
import os
from datetime import datetime
from pythonjsonlogger import jsonlogger
from config import settings


def setup_logging():
    """设置日志配置"""
    # 确保日志目录存在
    try:
        os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
        os.makedirs(os.path.dirname(settings.user_log_file), exist_ok=True)
    except Exception as e:
        print(f"警告: 无法创建日志目录: {e}")
        # 使用当前目录作为备用
        settings.log_file = "api.log"
        settings.user_log_file = "user_requests.log"
    
    # 主日志配置
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 用户请求日志配置
    user_logger = logging.getLogger('user_requests')
    user_logger.setLevel(logging.INFO)
    
    # JSON格式的用户日志处理器
    user_handler = logging.FileHandler(settings.user_log_file, encoding='utf-8')
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        json_ensure_ascii=False  # 确保中文字符不被转义
    )
    user_handler.setFormatter(json_formatter)
    user_logger.addHandler(user_handler)
    user_logger.propagate = False
    
    return logging.getLogger(__name__), user_logger


# 初始化日志
main_logger, user_logger = setup_logging() 