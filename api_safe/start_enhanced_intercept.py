#!/usr/bin/env python3
"""
增强版拦截器启动脚本
一键启动带有完整拦截逻辑和RAG功能的API服务
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def setup_environment():
    """设置环境变量"""
    env_vars = {
        # 启用拦截器
        "ENABLE_FRONT_INTERCEPT": "true",
        "ENABLE_POST_INTERCEPT": "true", 
        "USE_LOCAL_INTERCEPT": "true",
        
        # 启用RAG系统
        "ENABLE_RAG": "true",
        "RAG_SERVICE_URL": "http://localhost:8000/retrieve",
        "RAG_TOP_K": "5",
        "RAG_TIMEOUT": "10.0",
        
        # BERT双阈值配置
        "BERT_FRONT_HIGH_THRESHOLD": "0.97",
        "BERT_FRONT_LOW_THRESHOLD": "0.00002", 
        "BERT_POST_THRESHOLD": "0.5",
        
        # 超时配置
        "INTERCEPT_TIMEOUT": "5.0",
        
        # 日志配置
        "LOG_LEVEL": "INFO",
        
        # 服务配置
        "HOST": "0.0.0.0",
        "PORT": "8001",
        "WORKERS": "1"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ {key}={value}")


def check_dependencies():
    """检查依赖文件"""
    print("🔍 检查依赖文件...")
    
    required_files = [
        "safe_api/data/high_sensitive_keywords.json",
        "safe_api/data/high_sensitive_keywords-2.json", 
        "safe_api/data/blacklist_1w.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
            print(f"⚠️  缺少文件: {file_path}")
        else:
            print(f"✅ 找到文件: {file_path}")
    
    # 检查模型目录
    model_dirs = [
        "safe_api/models/front_model",
        "safe_api/models/post_model"
    ]
    
    for model_dir in model_dirs:
        if not Path(model_dir).exists():
            print(f"⚠️  缺少模型目录: {model_dir}")
            missing_files.append(model_dir)
        else:
            print(f"✅ 找到模型目录: {model_dir}")
    
    if missing_files:
        print(f"\n❌ 缺少 {len(missing_files)} 个必要文件/目录")
        print("请确保以下文件存在:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    print("✅ 所有依赖文件检查通过")
    return True


def create_demo_data():
    """创建演示数据（如果文件不存在）"""
    print("📝 创建演示数据...")
    
    # 创建目录
    os.makedirs("safe_api/data", exist_ok=True)
    os.makedirs("safe_api/models", exist_ok=True)
    
    # 高敏感关键词示例
    high_sensitive_keywords = {
        "keywords": [
            "placeholder_keyword_alpha",
            "placeholder_keyword_beta",
            "placeholder_keyword_gamma"
        ]
    }
    
    # 次高敏感关键词示例
    medium_sensitive_keywords = {
        "keywords": [
            "placeholder_topic_alpha",
            "placeholder_topic_beta",
            "placeholder_topic_gamma"
        ]
    }
    
    # 1w黑名单示例（简化版）
    blacklist_1w = {
        "keywords": [
            "placeholder_category_alpha",
            "placeholder_category_beta",
            "placeholder_category_gamma"
        ]
    }
    
    # 写入文件
    import json
    
    files_to_create = [
        ("safe_api/data/high_sensitive_keywords.json", high_sensitive_keywords),
        ("safe_api/data/high_sensitive_keywords-2.json", medium_sensitive_keywords),
        ("safe_api/data/blacklist_1w.json", blacklist_1w)
    ]
    
    for file_path, data in files_to_create:
        if not Path(file_path).exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 创建演示文件: {file_path}")
        else:
            print(f"⏭️  文件已存在: {file_path}")


def start_api_server():
    """启动API服务器"""
    print("\n🚀 启动增强版拦截器API服务...")
    
    try:
        # 启动主服务
        subprocess.run([
            sys.executable, "main.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务启动失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="增强版拦截器启动脚本")
    parser.add_argument("--check-only", action="store_true", help="仅检查依赖，不启动服务")
    parser.add_argument("--create-demo-data", action="store_true", help="创建演示数据文件")
    parser.add_argument("--no-rag", action="store_true", help="禁用RAG系统")
    
    args = parser.parse_args()
    
    print("🎯 增强版拦截器启动脚本")
    print("=" * 50)
    
    # 设置环境变量
    setup_environment()
    
    # 如果禁用RAG
    if args.no_rag:
        os.environ["ENABLE_RAG"] = "false"
        print("⚠️  RAG系统已禁用")
    
    print("\n" + "=" * 50)
    
    # 创建演示数据
    if args.create_demo_data:
        create_demo_data()
        print("\n" + "=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("\n💡 提示: 使用 --create-demo-data 参数可以创建演示数据文件")
        if not args.check_only:
            print("⚠️  由于缺少依赖文件，服务可能无法正常工作")
            response = input("是否继续启动服务？(y/N): ")
            if response.lower() != 'y':
                print("❌ 启动已取消")
                return
    
    if args.check_only:
        print("✅ 依赖检查完成")
        return
    
    print("\n" + "=" * 50)
    print("📋 当前配置:")
    print(f"  前拦截: {os.environ.get('ENABLE_FRONT_INTERCEPT')}")
    print(f"  后拦截: {os.environ.get('ENABLE_POST_INTERCEPT')}")
    print(f"  RAG系统: {os.environ.get('ENABLE_RAG')}")
    print(f"  本地模式: {os.environ.get('USE_LOCAL_INTERCEPT')}")
    print(f"  服务地址: {os.environ.get('HOST')}:{os.environ.get('PORT')}")
    print("=" * 50)
    
    # 启动服务
    start_api_server()


if __name__ == "__main__":
    main()
