#!/usr/bin/env python3
"""
启动带内容拦截功能的API服务
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_dependencies():
    """检查必要的依赖"""
    print("检查依赖...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "transformers",
        "torch",
        "aiohttp"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - 缺失")
    
    if missing_packages:
        print(f"\n缺少以下依赖: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖检查通过")
    return True

def check_model_files(model_path, data_path):
    """检查模型和数据文件"""
    print("\n检查模型和数据文件...")
    
    required_paths = [
        (Path(model_path), "前拦截模型"),
        (Path(data_path) / "blacklist_1w.json", "1w黑名单"),
        (Path(data_path) / "high_sensitive_keywords.json", "高敏感词")
    ]
    
    missing_files = []
    for path, description in required_paths:
        if path.exists():
            print(f"✅ {description}: {path}")
        else:
            missing_files.append((path, description))
            print(f"❌ {description}: {path} - 文件不存在")
    
    if missing_files:
        print("\n缺少以下文件:")
        for path, description in missing_files:
            print(f"  - {description}: {path}")
        
        print("\n请确保:")
        print("1. 模型文件已正确放置")
        print("2. 数据文件已准备好")
        print("3. 路径配置正确")
        return False
    
    print("✅ 所有模型和数据文件检查通过")
    return True

def create_env_file(args):
    """创建环境配置文件"""
    env_file = Path(".env")
    
    if env_file.exists() and not args.force:
        print(f"\n配置文件 {env_file} 已存在")
        response = input("是否覆盖? (y/N): ").strip().lower()
        if response != 'y':
            print("使用现有配置文件")
            return True
    
    print(f"\n创建配置文件: {env_file}")
    
    config_content = f"""# vLLM Proxy API 配置文件 (自动生成)

# ===================
# 基础服务配置
# ===================
VLLM_API_BASE={args.vllm_url}
HOST={args.host}
PORT={args.port}

# ===================
# 安全配置
# ===================
API_KEY={args.api_key}
ENABLE_DOCS={str(args.enable_docs).lower()}
DOCS_REQUIRE_AUTH=true

# ===================
# 内容拦截配置
# ===================
# 是否启用前拦截（用户输入检查）
ENABLE_FRONT_INTERCEPT={str(args.enable_front).lower()}
# 是否启用后拦截（模型输出检查）
ENABLE_POST_INTERCEPT={str(args.enable_post).lower()}

# 是否使用本地集成模式
USE_LOCAL_INTERCEPT={str(args.use_local).lower()}

# 拦截模型路径配置（本地集成模式）
MODEL_FRONT_PATH={args.front_model_path}
MODEL_POST_PATH={args.post_model_path}
BLACKLIST_1W_PATH={args.data_path}/blacklist_1w.json
HIGH_SENSITIVE_KEYWORDS_PATH={args.data_path}/high_sensitive_keywords.json

# 拦截API地址（远程API模式）
FRONT_INTERCEPT_URL=http://localhost:8001/intercept
POST_INTERCEPT_URL=http://localhost:8002/intercept

# 拦截API超时时间（秒）
INTERCEPT_TIMEOUT={args.timeout}

# ===================
# 日志配置
# ===================
LOG_LEVEL=INFO
LOG_FILE=logs/api.log
USER_LOG_FILE=logs/user_requests.log
"""
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"✅ 配置文件已创建: {env_file}")
        return True
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def start_api_server(args):
    """启动API服务器"""
    print("\n启动API服务器...")
    
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 启动命令
    if args.workers > 1:
        cmd = [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", args.host,
            "--port", str(args.port),
            "--workers", str(args.workers),
            "--log-level", "info"
        ]
    else:
        cmd = [
            sys.executable, "main.py"
        ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        # 启动服务
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🔴 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务启动失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 意外错误: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="启动带内容拦截功能的API服务")
    
    # 基础配置
    parser.add_argument("--host", default="0.0.0.0", help="绑定主机地址")
    parser.add_argument("--port", type=int, default=8001, help="绑定端口")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    parser.add_argument("--vllm-url", default="http://localhost:8000", help="vLLM API地址")
    parser.add_argument("--api-key", default="your-secret-api-key", help="API密钥")
    
    # 拦截配置
    parser.add_argument("--enable-front", action="store_true", default=True, help="启用前拦截")
    parser.add_argument("--enable-post", action="store_true", default=True, help="启用后拦截")
    parser.add_argument("--use-local", action="store_true", default=True, help="使用本地集成模式")
    parser.add_argument("--front-model-path", default="./safe_api/models/front_model", help="前拦截模型路径")
    parser.add_argument("--post-model-path", default="./safe_api/models/post_model", help="后拦截模型路径")
    parser.add_argument("--data-path", default="./safe_api/data", help="数据文件路径")
    parser.add_argument("--timeout", type=float, default=5.0, help="拦截超时时间")
    
    # 其他选项
    parser.add_argument("--enable-docs", action="store_true", default=False, help="启用API文档")
    parser.add_argument("--force", action="store_true", help="强制覆盖现有配置文件")
    parser.add_argument("--skip-checks", action="store_true", help="跳过依赖和文件检查")
    
    args = parser.parse_args()
    
    print("🚀 启动带内容拦截功能的API服务")
    print("=" * 60)
    
    # 检查依赖
    if not args.skip_checks:
        if not check_dependencies():
            return 1
        
        # 检查模型文件（仅在使用本地模式时）
        if args.use_local:
            if not check_model_files(args.front_model_path, args.data_path):
                print("\n⚠️  模型文件检查未通过，但您可以:")
                print("1. 使用 --skip-checks 跳过检查")
                print("2. 使用远程API模式 (设置 USE_LOCAL_INTERCEPT=false)")
                print("3. 准备好模型文件后重新启动")
                return 1
    
    # 创建配置文件
    if not create_env_file(args):
        return 1
    
    # 显示配置摘要
    print(f"\n配置摘要:")
    print(f"  服务地址: {args.host}:{args.port}")
    print(f"  vLLM地址: {args.vllm_url}")
    print(f"  前拦截: {'启用' if args.enable_front else '禁用'}")
    print(f"  后拦截: {'启用' if args.enable_post else '禁用'}")
    print(f"  本地模式: {'是' if args.use_local else '否'}")
    if args.use_local:
        print(f"  前拦截模型: {args.front_model_path}")
        print(f"  后拦截模型: {args.post_model_path}")
    print(f"  工作进程: {args.workers}")
    
    print(f"\n📖 更多信息请查看: CONTENT_INTERCEPT_GUIDE.md")
    print(f"🧪 可使用测试脚本: python test_intercept.py")
    
    # 启动服务
    input("\n按Enter键启动服务...")
    return 0 if start_api_server(args) else 1

if __name__ == "__main__":
    sys.exit(main())
