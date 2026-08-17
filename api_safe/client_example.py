#!/usr/bin/env python3
"""
vLLM Proxy API 客户端示例
展示如何使用新的用户ID参数和API key鉴权
"""

import json
import requests
from typing import Optional, Dict, Any


class VLLMProxyClient:
    """vLLM Proxy API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8001", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # 如果设置了API key，添加到请求头
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def chat_completion(
        self,
        messages: list,
        model: str = "default",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        enable_context: bool = False,
        max_context_turns: int = 5,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """聊天完成接口"""
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "enable_context": enable_context,
            "max_context_turns": max_context_turns,
            **kwargs
        }
        
        # 添加用户ID（如果提供）
        if user_id:
            data["user_id"] = user_id
            
        # 添加会话ID（如果提供）
        if session_id:
            data["session_id"] = session_id
            
        # 添加最大token数（如果提供）
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计"""
        response = requests.get(
            f"{self.base_url}/v1/users/{user_id}/stats",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_session_history(self, session_id: str, max_turns: int = 10) -> Dict[str, Any]:
        """获取会话历史"""
        response = requests.get(
            f"{self.base_url}/v1/sessions/{session_id}/history",
            headers=self.headers,
            params={"max_turns": max_turns}
        )
        response.raise_for_status()
        return response.json()


def main():
    """示例用法"""
    # 创建客户端（需要设置正确的API key）
    client = VLLMProxyClient(
        base_url="http://localhost:8001",
        api_key="your-api-key-here"  # 替换为实际的API key
    )
    
    try:
        # 健康检查
        print("=== 健康检查 ===")
        health = client.health_check()
        print(f"服务状态: {health}")
        
        # 单轮对话示例
        print("\n=== 单轮对话 ===")
        response = client.chat_completion(
            messages=[
                {"role": "user", "content": "你好，请介绍一下你自己"}
            ],
            model="default",
            user_id="user123",  # 指定用户ID
            temperature=0.7,
            max_tokens=100
        )
        print(f"响应: {response['choices'][0]['message']['content']}")
        
        # 多轮对话示例
        print("\n=== 多轮对话 ===")
        session_id = "session_001"
        
        # 第一轮
        response1 = client.chat_completion(
            messages=[
                {"role": "user", "content": "我想学习Python编程"}
            ],
            model="default",
            user_id="user123",
            session_id=session_id,
            enable_context=True,
            max_context_turns=5
        )
        print(f"第一轮响应: {response1['choices'][0]['message']['content']}")
        
        # 第二轮（会自动包含上下文）
        response2 = client.chat_completion(
            messages=[
                {"role": "user", "content": "请给我一个简单的示例"}
            ],
            model="default",
            user_id="user123",
            session_id=session_id,
            enable_context=True,
            max_context_turns=5
        )
        print(f"第二轮响应: {response2['choices'][0]['message']['content']}")
        
        # 获取用户统计
        print("\n=== 用户统计 ===")
        stats = client.get_user_stats("user123")
        print(f"用户统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        # 获取会话历史
        print("\n=== 会话历史 ===")
        history = client.get_session_history(session_id)
        print(f"会话历史: {json.dumps(history, indent=2, ensure_ascii=False)}")
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
        if e.response.status_code == 401:
            print("请检查API key是否正确设置")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main() 