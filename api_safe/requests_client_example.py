#!/usr/bin/env python3
"""
使用requests库调用转发API - 完整功能版本
支持所有自定义参数：session_id, enable_context, max_context_turns

使用方法: python requests_client_example.py
依赖: pip install requests
"""

import requests
import json
import uuid


def get_response_stream_with_session(prompt, api_base="http://localhost:8002", session_id=None, enable_context=False):
    """
    使用requests调用转发API - 支持流式输出和多轮对话
    
    Args:
        prompt: 用户输入
        api_base: API基础URL
        session_id: 会话ID（多轮对话需要）
        enable_context: 是否启用多轮上下文
    """
    url = f"{api_base}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer liutao123"  # 你的API Key
    }
    
    # 构建请求数据
    data = {
        "model": "qwen7b-in",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are InnoSpark, created by Lab of AI Education. You are from East China Normal University(华东师范大学), "
                    "and your Chinese Name is 启创. You are a helpful assistant."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": True,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    # 添加自定义参数
    if session_id:
        data["session_id"] = session_id
    if enable_context:
        data["enable_context"] = True
        data["max_context_turns"] = 10
    
    print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        # 发送流式请求
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        print("AI: ", end="", flush=True)
        full_response = ""
        
        # 处理流式响应
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]  # 移除 'data: ' 前缀
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        if 'choices' in chunk_data and chunk_data['choices']:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                print(content, end="", flush=True)
                                full_response += content
                    except json.JSONDecodeError:
                        continue
        
        print()  # 换行
        return full_response
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None


def get_response_normal_with_session(prompt, api_base="http://localhost:8002", session_id=None, enable_context=False):
    """
    使用requests调用转发API - 非流式输出，支持多轮对话
    """
    url = f"{api_base}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer liutao123"
    }
    
    data = {
        "model": "qwen7b-in",
        "messages": [
            {
                "role": "system",
                "content": "You are InnoSpark, created by Lab of AI Education. You are from East China Normal University(华东师范大学), and your Chinese Name is 启创. You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    # 添加自定义参数
    if session_id:
        data["session_id"] = session_id
    if enable_context:
        data["enable_context"] = True
        data["max_context_turns"] = 10
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None


class MultiTurnChat:
    """多轮对话会话管理类"""
    
    def __init__(self, api_base="http://localhost:8002"):
        self.api_base = api_base
        self.session_id = str(uuid.uuid4())
        print(f"创建会话: {self.session_id}")
    
    def send_message(self, message, stream=True):
        """发送消息"""
        print(f"\n用户: {message}")
        
        if stream:
            return get_response_stream_with_session(
                message, 
                self.api_base, 
                self.session_id, 
                enable_context=True
            )
        else:
            response = get_response_normal_with_session(
                message, 
                self.api_base, 
                self.session_id, 
                enable_context=True
            )
            print(f"AI: {response}")
            return response


def test_single_turn():
    """测试单轮对话"""
    print("=== 测试单轮对话 ===")
    
    # 流式输出
    print("\n1. 流式输出测试：")
    get_response_stream_with_session("你好，请介绍一下你自己")
    
    # 非流式输出
    print("\n2. 非流式输出测试：")
    response = get_response_normal_with_session("你来自哪里？")
    print(f"AI: {response}")


def test_multi_turn():
    """测试多轮对话"""
    print("\n=== 测试多轮对话 ===")
    
    chat = MultiTurnChat()
    
    # 第一轮
    chat.send_message("我叫张三，请记住我的名字", stream=True)
    
    # 第二轮
    chat.send_message("我的名字是什么？", stream=True)
    
    # 第三轮
    chat.send_message("请用我的名字跟我打招呼", stream=True)


def interactive_mode():
    """交互模式"""
    print("\n=== 交互模式 ===")
    print("输入 'quit' 退出")
    print("输入 'new' 创建新会话")
    print("输入 'single' 切换单轮模式")
    print("输入 'multi' 切换多轮模式")
    print()
    
    chat = None
    multi_turn_mode = False
    
    while True:
        try:
            user_input = input("用户: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'new':
                chat = MultiTurnChat()
                multi_turn_mode = True
                print("✅ 创建新的多轮对话会话")
                continue
            elif user_input.lower() == 'single':
                multi_turn_mode = False
                print("✅ 切换到单轮模式")
                continue
            elif user_input.lower() == 'multi':
                if not chat:
                    chat = MultiTurnChat()
                multi_turn_mode = True
                print("✅ 切换到多轮模式")
                continue
            elif not user_input:
                continue
            
            # 发送消息
            if multi_turn_mode and chat:
                chat.send_message(user_input, stream=True)
            else:
                get_response_stream_with_session(user_input)
                
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n错误: {e}")
    
    print("👋 再见！")


def main():
    """主函数"""
    print("🚀 requests库调用转发API示例")
    print("支持所有自定义参数：session_id, enable_context等")
    print("=" * 60)
    
    while True:
        print("\n请选择测试模式：")
        print("1. 单轮对话测试")
        print("2. 多轮对话测试")
        print("3. 交互模式")
        print("4. 退出")
        
        choice = input("\n请输入选择 (1-4): ").strip()
        
        if choice == "1":
            test_single_turn()
        elif choice == "2":
            test_multi_turn()
        elif choice == "3":
            interactive_mode()
        elif choice == "4":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    main() 