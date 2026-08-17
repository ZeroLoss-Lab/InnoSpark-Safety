#!/usr/bin/env python3
"""
RAG增强拦截器 - 专门处理RAG系统逻辑
与safe_api配合，实现完整的拦截+RAG流程
"""

from typing import Optional
from dataclasses import dataclass

from config import settings
from logger_config import main_logger
from rag_client import rag_client
from safe_api_client import safe_api_client, InterceptResult


@dataclass
class RAGInterceptResult(InterceptResult):
    """扩展的拦截结果，包含RAG信息"""
    pass


class RAGEnhancedInterceptor:
    """RAG增强拦截器"""
    
    def __init__(self):
        # 注意：安全响应消息由主API统一管理，这里不需要存储
        pass
    
    async def intercept_with_rag(self, text: str) -> RAGInterceptResult:
        """
        执行完整的RAG增强拦截逻辑
        
        流程：
        1. 调用safe_api进行前拦截（包含高敏词+BERT双阈值+次高敏词检查）
        2. 如果前拦截通过且启用RAG，则进行RAG检索
        3. 返回结果供主API使用
        """
        main_logger.info("开始执行RAG增强拦截检查")
        
        # 步骤1: 调用safe_api进行完整的前拦截检查
        # 这包括了您设计的所有逻辑：高敏词 -> BERT双阈值 -> 次高敏词
        front_result = await safe_api_client.front_intercept(text)
        
        if not front_result.is_safe:
            # 前拦截触发，直接返回拦截结果
            main_logger.info(f"前拦截触发: {front_result.reason}")
            return RAGInterceptResult(
                is_safe=False,
                reason=front_result.reason,
                matched_keywords=front_result.matched_keywords,
                safety_response=None  # 由主API统一处理安全响应消息
            )
        
        # 步骤2: 前拦截通过，检查是否需要RAG增强
        # 根据前拦截的reason判断是否应该使用RAG
        should_use_rag = (
            settings.enable_rag and 
            front_result.is_safe and
            (
                "BERT双阈值判断未确定" in front_result.reason or
                "BERT双阈值判断为直接通过" in front_result.reason or
                "前拦截通过" in front_result.reason
            )
        )
        
        if should_use_rag:
            # 步骤3: 使用RAG系统
            main_logger.info("前拦截通过，启动RAG系统")
            try:
                # 调用RAG检索
                rag_context = await rag_client.retrieve_and_format(text)
                
                if rag_context:
                    main_logger.info("RAG检索成功，返回RAG增强结果")
                    return RAGInterceptResult(
                        is_safe=True,
                        reason="通过RAG系统处理",
                        rag_context=rag_context,
                        rag_used=True
                    )
                else:
                    main_logger.warning("RAG检索失败，默认通过")
                    return RAGInterceptResult(
                        is_safe=True,
                        reason="RAG检索失败，默认通过"
                    )
                    
            except Exception as e:
                main_logger.error(f"RAG系统调用失败: {e}")
                return RAGInterceptResult(
                    is_safe=True,
                    reason=f"RAG系统调用失败，默认通过: {str(e)}"
                )
        else:
            # 未启用RAG或不需要RAG，直接返回前拦截结果
            main_logger.info("前拦截通过，未启用RAG系统")
            return RAGInterceptResult(
                is_safe=True,
                reason=front_result.reason
            )
    
    async def post_intercept(self, text: str) -> InterceptResult:
        """
        执行后拦截检查
        直接调用safe_api的后拦截服务
        """
        return await safe_api_client.post_intercept(text)


# 创建全局RAG增强拦截器实例
rag_enhanced_interceptor = RAGEnhancedInterceptor()
