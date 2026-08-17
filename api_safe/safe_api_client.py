#!/usr/bin/env python3
"""
Safe API客户端 - 统一调用safe_api的拦截服务
避免在主API中重复实现拦截逻辑
"""

import aiohttp
import json
from typing import List, Optional
from dataclasses import dataclass

from config import settings
from logger_config import main_logger


@dataclass
class InterceptResult:
    """拦截结果"""
    is_safe: bool
    reason: str = ""
    matched_keywords: List[str] = None
    score: Optional[float] = None
    safety_response: Optional[str] = None
    rag_context: Optional[str] = None  # RAG检索的上下文
    rag_used: bool = False  # 是否使用了RAG


class SafeAPIClient:
    """Safe API统一客户端"""
    
    def __init__(self):
        self.front_intercept_url = settings.front_intercept_url
        self.post_intercept_url = settings.post_intercept_url
        self.timeout = settings.intercept_timeout
        # 注意：安全响应消息由主API统一管理，这里不需要存储
    
    async def front_intercept(self, text: str) -> InterceptResult:
        """
        调用前拦截API
        实现您设计的完整逻辑：
        1. 高敏关键词检查
        2. BERT双阈值判断  
        3. 次高敏关键词检查
        """
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.post(
                    self.front_intercept_url,
                    json={"text": text},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return InterceptResult(
                            is_safe=result.get("is_safe", True),
                            reason=result.get("reason", ""),
                            matched_keywords=result.get("matched_keywords", []),
                            safety_response=None  # Safe API不返回具体消息，由主API处理
                        )
                    else:
                        main_logger.error(f"前拦截API调用失败: {response.status}")
                        error_text = await response.text()
                        main_logger.error(f"错误详情: {error_text}")
                        return InterceptResult(
                            is_safe=False, 
                            reason=f"前拦截API调用失败: {response.status}",
                            safety_response=None  # 主API会处理安全响应消息
                        )
        except aiohttp.ClientTimeout:
            main_logger.error(f"前拦截API调用超时 (>{self.timeout}s)")
            return InterceptResult(
                is_safe=False, 
                reason=f"前拦截API调用超时",
                safety_response=None  # 主API会处理安全响应消息
            )
        except Exception as e:
            main_logger.error(f"前拦截API调用异常: {e}")
            return InterceptResult(
                is_safe=False, 
                reason=f"前拦截API调用异常: {str(e)}",
                safety_response=None  # 主API会处理安全响应消息
            )
    
    async def post_intercept(self, text: str) -> InterceptResult:
        """
        调用后拦截API
        实现BERT后拦截判断
        """
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.post(
                    self.post_intercept_url,
                    json={"text": text},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return InterceptResult(
                            is_safe=result.get("is_safe", True),
                            reason=result.get("reason", ""),
                            score=result.get("score"),
                            safety_response=None  # Safe API不返回具体消息，由主API处理
                        )
                    else:
                        main_logger.error(f"后拦截API调用失败: {response.status}")
                        error_text = await response.text()
                        main_logger.error(f"错误详情: {error_text}")
                        return InterceptResult(
                            is_safe=False, 
                            reason=f"后拦截API调用失败: {response.status}",
                            safety_response=None  # 主API会处理安全响应消息
                        )
        except aiohttp.ClientTimeout:
            main_logger.error(f"后拦截API调用超时 (>{self.timeout}s)")
            return InterceptResult(
                is_safe=False, 
                reason=f"后拦截API调用超时",
                safety_response=None  # 主API会处理安全响应消息
            )
        except Exception as e:
            main_logger.error(f"后拦截API调用异常: {e}")
            return InterceptResult(
                is_safe=False, 
                reason=f"后拦截API调用异常: {str(e)}",
                safety_response=None  # 主API会处理安全响应消息
            )


# 创建全局客户端实例
safe_api_client = SafeAPIClient()
