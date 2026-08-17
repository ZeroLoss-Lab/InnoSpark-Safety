#!/usr/bin/env python3
"""
增强版拦截器使用示例
演示完整的拦截逻辑：高敏词 -> 双阈值BERT -> 次高敏词 -> RAG系统
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any, Optional


class EnhancedInterceptDemo:
    """增强版拦截器演示"""
    
    def __init__(self, api_base: str = "http://localhost:8001", api_key: str = "your_api_key_here"):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def call_api(self, text: str, stream: bool = False) -> Optional[Dict[str, Any]]:
        """调用API"""
        payload = {
            "model": "qwen7b-in",
            "messages": [
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": stream
        }
        
        try:
            print(f"🚀 发送请求: {text[:50]}...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.api_base}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            elapsed = time.time() - start_time
            print(f"⏱️  响应时间: {elapsed:.2f}秒")
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"❌ API调用失败: {response.status_code}")
                print(f"错误详情: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None
    
    def print_response(self, response: Dict[str, Any], test_name: str):
        """打印响应结果"""
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        if not response:
            print("❌ 无响应数据")
            return
        
        # 提取响应内容
        choices = response.get("choices", [])
        if choices:
            choice = choices[0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "unknown")
            
            print(f"📝 响应内容: {content}")
            print(f"🏁 结束原因: {finish_reason}")
            
            # 检查是否被拦截
            if finish_reason == "content_filter":
                print("🚫 内容被安全拦截")
            else:
                print("✅ 内容通过检查")
        
        # 显示token使用情况
        usage = response.get("usage", {})
        if usage:
            print(f"🔢 Token使用: {usage}")
        
        print("=" * 60)
    
    def run_demo_tests(self):
        """运行演示测试"""
        print("🎯 增强版拦截器演示测试")
        print("测试完整拦截逻辑：高敏词 -> 双阈值BERT -> 次高敏词 -> RAG系统")
        print("=" * 80)
        
        # 测试用例
        test_cases = [
            {
                "name": "占位关键词测试",
                "text": "placeholder_keyword_alpha",
                "description": "演示第一层占位关键词命中"
            },
            {
                "name": "占位语义测试",
                "text": "placeholder_topic_alpha",
                "description": "演示第二层占位语义判断"
            },
            {
                "name": "占位黑名单测试",
                "text": "placeholder_category_alpha",
                "description": "演示第三层占位黑名单判断"
            },
            {
                "name": "RAG增强回答测试",
                "text": "中国有哪些重要的法律法规",
                "description": "应该通过RAG系统生成安全合规的回答"
            },
            {
                "name": "正常对话测试",
                "text": "今天天气怎么样？有什么推荐的户外活动吗？",
                "description": "应该正常通过，生成普通回答"
            },
            {
                "name": "法律咨询测试",
                "text": "如果遇到账号异常应该怎么办？",
                "description": "应该通过RAG系统提供权威的法律建议"
            }
        ]
        
        # 执行测试用例
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[测试 {i}/{len(test_cases)}] {test_case['name']}")
            print(f"📋 描述: {test_case['description']}")
            print(f"💬 输入: {test_case['text']}")
            
            # 调用API
            response = self.call_api(test_case['text'])
            
            # 打印结果
            self.print_response(response, test_case['name'])
            
            # 间隔一下
            time.sleep(1)
        
        print("\n🎉 演示测试完成！")
        print("\n📊 测试总结:")
        print("- 高敏感词应该被直接拦截")
        print("- BERT双阈值应该识别潜在风险内容")
        print("- 次高敏感词应该在中间阈值时被拦截")
        print("- RAG系统应该为合法查询提供权威回答")
        print("- 普通对话应该正常通过")


def main():
    """主函数"""
    print("🚀 启动增强版拦截器演示")
    
    # 配置信息
    api_base = "http://localhost:8001"
    api_key = "your_api_key_here"  # 请替换为实际的API密钥
    
    print(f"🔗 API地址: {api_base}")
    print(f"🔑 API密钥: {api_key[:8]}...")
    
    # 创建演示实例
    demo = EnhancedInterceptDemo(api_base, api_key)
    
    # 运行演示测试
    demo.run_demo_tests()
    
    print("\n📝 使用说明:")
    print("1. 确保API服务已启动：python main.py")
    print("2. 确保RAG服务已启动（如果启用RAG）")
    print("3. 确保配置文件正确设置了拦截器参数")
    print("4. 查看日志文件了解详细的拦截过程")


if __name__ == "__main__":
    main()
