#!/usr/bin/env python3
"""
OpenAI客户端调用转发API - 简化版本
只使用标准OpenAI参数，兼容性最好

使用方法: python openai_client_simple.py
依赖: pip install openai
"""

from openai import OpenAI


def get_response_stream(prompt, openai_api_base="http://localhost:8002/v1"):
    """
    使用OpenAI客户端调用转发API - 流式输出
    只使用标准OpenAI参数，确保兼容性
    """
    openai_api_key = "liutao123"  # 你的API Key
    client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base,
    )

    # 获取第一个模型名称（可选）
    try:
        models = client.models.list()
        model = models.data[0].id
        print(f"使用模型: {model}")
    except Exception as e:
        print(f"获取模型列表失败，使用默认模型: {e}")
        model = "qwen7b-in"

    # 构建 system prompt
    system_message = {
        "role": "system",
        "content": (
            "You are InnoSpark, created by Lab of AI Education. You are from East China Normal University(华东师范大学), "
            "and your Chinese Name is 启创. You are a helpful assistant."
        )
    }

    # 构建消息列表
    messages = [
        system_message,
        {
            "role": "user",
            "content": prompt
        }
    ]

    # 发起流式请求 - 只使用标准参数
    response_stream = client.chat.completions.create(
        messages=messages,
        model=model,
        stream=True,  # ✅ 关键参数：启用流式返回
        max_tokens=1000,  # 增加token限制
        temperature=0.7,
        # 注意：不能使用自定义参数如 session_id, enable_context 等
    )

    # 实时打印每段内容
    full_response = ""
    for chunk in response_stream:
        if chunk.choices and chunk.choices[0].delta.content:
            partial = chunk.choices[0].delta.content
            print(partial, end="", flush=True)  # 实时打印
            full_response += partial

    print()  # 换行
    return full_response


def get_response_normal(prompt, openai_api_base="http://localhost:8002/v1"):
    """
    非流式调用示例
    """
    client = OpenAI(
        api_key="liutao123",
        base_url=openai_api_base,
    )

    response = client.chat.completions.create(
        model="qwen7b-in",
        messages=[
            {
                "role": "system",
                "content": "You are InnoSpark, created by Lab of AI Education. You are from East China Normal University(华东师范大学), and your Chinese Name is 启创. You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=1000,
        temperature=0.7,
    )

    return response.choices[0].message.content


def main():
    """测试函数"""
    print("🚀 OpenAI客户端简化版测试")
    print("只使用标准OpenAI参数，确保兼容性\n")

    # 测试1：流式输出
    print("=== 测试流式输出 ===")
    prompt = "请简单介绍一下华东师范大学"
    print(f"用户: {prompt}")
    print("AI: ", end="", flush=True)
    response = get_response_stream(prompt)
    
    # 测试2：非流式输出
    print("\n=== 测试非流式输出 ===")
    prompt2 = "你来自哪里？"
    print(f"用户: {prompt2}")
    response2 = get_response_normal(prompt2)
    print(f"AI: {response2}")


if __name__ == "__main__":
    main() 