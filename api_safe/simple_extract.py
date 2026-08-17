#!/usr/bin/env python3
"""
简单的对话提取脚本
根据给定的API keys提取用户提问和模型回答，保存为JSON

使用方法：
python simple_extract.py sk-your-api-key-1 sk-your-api-key-2 sk-your-api-key-3
"""

import json
import sys
from pathlib import Path


def extract_conversations(api_keys, log_file="logs/user_requests.log"):
    """提取指定API keys的对话记录"""
    
    # 检查日志文件是否存在
    if not Path(log_file).exists():
        print(f"错误: 日志文件 {log_file} 不存在")
        return {}
    
    # 读取日志文件
    result = {}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    api_key = entry.get('api_key')
                    
                    # 只处理指定的API keys
                    if api_key not in api_keys:
                        continue
                    
                    # 初始化API key的记录
                    if api_key not in result:
                        result[api_key] = []
                    
                    # 提取用户提问
                    user_question = ""
                    messages = entry.get('messages', [])
                    for msg in messages:
                        if msg.get('role') == 'user':
                            user_question = msg.get('content', '')
                            break
                    
                    # 提取模型回答
                    model_answer = entry.get('response_content', '') or ""
                    
                    # 添加到结果
                    conversation = {
                        "user_question": user_question,
                        "model_answer": model_answer
                    }
                    
                    result[api_key].append(conversation)
                    
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"读取日志文件失败: {e}")
        return {}
    
    return result


def main():
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python simple_extract.py <api_key1> [api_key2] [api_key3] ...")
        print("示例: python simple_extract.py sk-your-api-key-1 sk-your-api-key-2")
        sys.exit(1)
    
    # 获取API keys
    api_keys = sys.argv[1:]
    print(f"提取以下API keys的对话记录: {api_keys}")
    
    # 提取对话记录
    conversations = extract_conversations(api_keys)
    
    if not conversations:
        print("没有找到任何对话记录")
        return
    
    # 保存到JSON文件
    output_file = "conversations_simple.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 对话记录已保存到: {output_file}")
        
        # 显示统计信息
        for api_key, records in conversations.items():
            print(f"📋 {api_key}: {len(records)} 条对话记录")
            
    except Exception as e:
        print(f"保存文件失败: {e}")


if __name__ == "__main__":
    main() 