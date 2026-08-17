#!/usr/bin/env python3
"""
Safe API启动脚本 - 支持阈值配置
可以通过命令行参数或环境变量设置BERT阈值
"""

import os
import sys
import argparse
import subprocess
from start_services import ServiceManager


def setup_environment(front_high=0.97, front_low=0.00002, post_threshold=0.5):
    """设置环境变量"""
    os.environ["BERT_FRONT_HIGH_THRESHOLD"] = str(front_high)
    os.environ["BERT_FRONT_LOW_THRESHOLD"] = str(front_low)
    os.environ["BERT_POST_THRESHOLD"] = str(post_threshold)
    
    print(f"🔧 设置BERT阈值:")
    print(f"  前拦截高阈值: {front_high}")
    print(f"  前拦截低阈值: {front_low}")
    print(f"  后拦截阈值: {post_threshold}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Safe API服务启动器 - 支持阈值配置")
    
    # BERT阈值配置
    parser.add_argument(
        "--bert-front-high", type=float, default=0.97,
        help="BERT前拦截高阈值 (默认: 0.97)"
    )
    parser.add_argument(
        "--bert-front-low", type=float, default=0.00002,
        help="BERT前拦截低阈值 (默认: 0.00002)"
    )
    parser.add_argument(
        "--bert-post", type=float, default=0.5,
        help="BERT后拦截阈值 (默认: 0.5)"
    )
    
    # 模型路径配置
    parser.add_argument(
        "--model-front-path", type=str, default="./models/front_model",
        help="前拦截模型路径 (默认: ./models/front_model)"
    )
    parser.add_argument(
        "--model-post-path", type=str, default="./models/post_model",
        help="后拦截模型路径 (默认: ./models/post_model)"
    )
    
    # 关键词文件路径配置
    parser.add_argument(
        "--high-sensitive-path", type=str, default="./data/high_sensitive_keywords.json",
        help="高敏感关键词文件路径 (默认: ./data/high_sensitive_keywords.json)"
    )
    parser.add_argument(
        "--low-sensitive-path", type=str, default="./data/high_sensitive_keywords-2.json",
        help="低敏感关键词文件路径 (默认: ./data/high_sensitive_keywords-2.json)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Safe API服务启动器")
    print("=" * 50)
    
    # 设置环境变量
    setup_environment(
        front_high=args.bert_front_high,
        front_low=args.bert_front_low,
        post_threshold=args.bert_post
    )
    
    # 设置模型路径
    os.environ["MODEL_FRONT_PATH"] = args.model_front_path
    os.environ["MODEL_POST_PATH"] = args.model_post_path
    
    # 设置关键词文件路径
    os.environ["HIGH_SENSITIVE_KEYWORDS_PATH"] = args.high_sensitive_path
    os.environ["MEDIUM_SENSITIVE_KEYWORDS_PATH"] = args.low_sensitive_path
    
    print(f"📁 模型路径:")
    print(f"  前拦截模型: {args.model_front_path}")
    print(f"  后拦截模型: {args.model_post_path}")
    print(f"📄 关键词文件路径:")
    print(f"  高敏感关键词: {args.high_sensitive_path}")
    print(f"  低敏感关键词: {args.low_sensitive_path}")
    print("=" * 50)
    
    # 启动服务管理器
    manager = ServiceManager()
    
    try:
        success = manager.start_all_services()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号，正在关闭服务...")
        manager.stop_all_services()
        sys.exit(0)


if __name__ == "__main__":
    main()
