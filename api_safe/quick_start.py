#!/usr/bin/env python3
"""
快速启动脚本 - 一键启动增强版拦截器
最简单的启动方式，自动处理所有配置
"""

import os
import sys

def main():
    """快速启动主函数"""
    print("🚀 增强版拦截器 - 快速启动")
    print("=" * 40)
    
    # 设置关键环境变量
    env_config = {
        # 启用拦截器
        "ENABLE_FRONT_INTERCEPT": "true",
        "ENABLE_POST_INTERCEPT": "true", 
        "USE_LOCAL_INTERCEPT": "true",
        
        # 启用RAG系统
        "ENABLE_RAG": "true",
        "RAG_SERVICE_URL": "http://localhost:8000/retrieve",
        
        # 基本配置
        "HOST": "0.0.0.0",
        "PORT": "8001",
        "API_KEY": "your_api_key_here",
        "LOG_LEVEL": "INFO",
        
        # 双阈值配置
        "BERT_FRONT_HIGH_THRESHOLD": "0.97",
        "BERT_FRONT_LOW_THRESHOLD": "0.00002",
        "BERT_POST_THRESHOLD": "0.5"
    }
    
    # 应用环境变量
    for key, value in env_config.items():
        os.environ[key] = value
    
    print("✅ 环境配置完成")
    print("📍 服务地址: http://localhost:8001")
    print("📖 API文档: http://localhost:8001/docs")
    print("🔑 API密钥: your_api_key_here")
    print("⚠️  使用 Ctrl+C 停止服务")
    print("=" * 40)
    
    try:
        # 启动服务
        os.system("python main.py")
    except KeyboardInterrupt:
        print("\n⏹️  服务已停止")

if __name__ == "__main__":
    main()
