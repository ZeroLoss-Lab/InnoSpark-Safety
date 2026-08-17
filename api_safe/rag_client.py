#!/usr/bin/env python3
"""
RAG客户端 - 用于调用RAG检索服务
"""

import json
import aiohttp
from typing import Dict, Any, Optional, List
from logger_config import main_logger
from config import settings


class RAGClient:
    """RAG检索客户端"""
    
    def __init__(self):
        self.service_url = settings.rag_service_url
        self.top_k = settings.rag_top_k
        self.timeout = settings.rag_timeout
        
    async def retrieve(self, query: str) -> Optional[Dict[str, Any]]:
        """
        调用RAG检索服务
        
        Args:
            query: 用户查询问题
            
        Returns:
            检索结果的JSON数据，失败时返回None
        """
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                payload = {
                    "query": query,
                    "top_k": self.top_k
                }
                
                main_logger.info(f"调用RAG服务: {self.service_url}, query: {query[:100]}...")
                
                async with session.post(
                    self.service_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        main_logger.info(f"RAG检索成功，返回{len(result.get('results', []))}条结果")
                        return result
                    else:
                        main_logger.error(f"RAG服务调用失败: {response.status}")
                        error_text = await response.text()
                        main_logger.error(f"错误详情: {error_text}")
                        return None
                        
        except aiohttp.ClientTimeout:
            main_logger.error(f"RAG服务调用超时 (>{self.timeout}s)")
            return None
        except Exception as e:
            main_logger.error(f"RAG服务调用异常: {e}")
            return None
    
    def json_to_text(self, rag_result: Dict[str, Any]) -> str:
        """
        将RAG返回的JSON结果转换为纯文本
        
        Args:
            rag_result: RAG服务返回的JSON数据
            
        Returns:
            转换后的纯文本字符串
        """
        if not rag_result:
            return ""
            
        text_parts = []
        
        # 处理查询信息
        if 'query' in rag_result:
            text_parts.append(f"查询问题: {rag_result['query']}")
            
        # 处理检索结果
        results = rag_result.get('results', [])
        if results:
            text_parts.append(f"\n检索到{len(results)}条相关信息:")
            
            for i, result in enumerate(results, 1):
                text_parts.append(f"\n[结果{i}]")
                
                # 处理不同的字段名可能性
                content = ""
                if 'content' in result:
                    content = result['content']
                elif 'text' in result:
                    content = result['text']
                elif 'document' in result:
                    content = result['document']
                elif 'passage' in result:
                    content = result['passage']
                    
                if content:
                    text_parts.append(f"内容: {content}")
                
                # 处理来源信息
                if 'source' in result:
                    text_parts.append(f"来源: {result['source']}")
                elif 'url' in result:
                    text_parts.append(f"链接: {result['url']}")
                elif 'title' in result:
                    text_parts.append(f"标题: {result['title']}")
                    
                # 处理相似度分数
                if 'score' in result:
                    text_parts.append(f"相关度: {result['score']:.4f}")
                elif 'similarity' in result:
                    text_parts.append(f"相似度: {result['similarity']:.4f}")
        
        # 处理元数据
        if 'metadata' in rag_result:
            metadata = rag_result['metadata']
            if metadata:
                text_parts.append(f"\n检索信息:")
                for key, value in metadata.items():
                    text_parts.append(f"{key}: {value}")
        
        return "\n".join(text_parts)
    
    async def retrieve_and_format(self, query: str) -> str:
        """
        检索并格式化为文本
        
        Args:
            query: 用户查询问题
            
        Returns:
            格式化后的检索结果文本，失败时返回空字符串
        """
        rag_result = await self.retrieve(query)
        if rag_result:
            return self.json_to_text(rag_result)
        return ""


# 创建全局RAG客户端实例
rag_client = RAGClient()
