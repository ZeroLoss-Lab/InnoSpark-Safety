#!/usr/bin/env python3
"""
调试vLLM API连接的脚本
"""

import json
import requests
import os

def test_vllm_direct():
    """直接测试vLLM API"""
    vllm_base = os.getenv("VLLM_API_BASE", "http://localhost:8000")
    
    print(f"🔍 测试vLLM API直连: {vllm_base}")
    
    # 测试模型列表
    try:
        response = requests.get(f"{vllm_base}/v1/models", timeout=10)
        print(f"✅ 模型列表请求成功: {response.status_code}")
        models_data = response.json()
        print(f"   可用模型: {[m['id'] for m in models_data.get('data', [])]}")
        
        # 获取第一个模型用于测试
        if models_data.get('data'):
            model_name = models_data['data'][0]['id']
            print(f"   使用模型: {model_name}")
            
            # 测试聊天完成
            chat_request = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "给我生成一个关于阿基米德的跨学科教案"}
                ],
                "temperature": 0.7,
                "max_tokens": 8192  # 增加到200个token以支持100字论文
            }
            
            print(f"\n🔍 测试聊天完成...")
            print(f"   请求数据: {json.dumps(chat_request, ensure_ascii=False, indent=2)}")
            
            response = requests.post(
                f"{vllm_base}/v1/chat/completions",
                json=chat_request,
                timeout=30
            )
            
            print(f"   响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 聊天完成成功")
                print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            else:
                print(f"❌ 聊天完成失败")
                print(f"   错误: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接vLLM API失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")

def test_proxy_api():
    """测试代理API"""
    proxy_port = os.getenv("PORT", "8002")
    proxy_base = f"http://localhost:{proxy_port}"
    
    print(f"\n🔍 测试代理API: {proxy_base}")
    
    try:
        # 健康检查
        response = requests.get(f"{proxy_base}/health", timeout=5)
        print(f"✅ 健康检查: {response.status_code}")
        
        # 测试聊天
        chat_request = {
            "model": "qwen7b-in",
            "messages": [
                {"role": "user", "content": "给我生成一个关于阿基米德的跨学科教案"}
            ],
            "temperature": 0.7,
            "max_tokens": 8192  # 增加到200个token以支持100字论文
        }
        
        response = requests.post(
            f"{proxy_base}/v1/chat/completions",
            json=chat_request,
            timeout=30
        )
        
        print(f"   聊天响应状态: {response.status_code}")
        if response.status_code != 200:
            print(f"   错误详情: {response.text}")
        else:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '无内容')
            print(f"✅ 代理聊天成功:")
            print(f"   完整响应: {content}")
            if 'usage' in result:
                usage = result['usage']
                print(f"   Token使用: {usage}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接代理API失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")

if __name__ == "__main__":
    print("vLLM API 调试工具")
    print("=" * 50)
    
    # 显示环境变量
    print(f"VLLM_API_BASE: {os.getenv('VLLM_API_BASE', '未设置')}")
    print(f"PORT: {os.getenv('PORT', '未设置')}")
    
    test_vllm_direct()
    test_proxy_api() 