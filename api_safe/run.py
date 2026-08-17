#!/usr/bin/env python3
"""
vLLM Proxy API 启动脚本
支持命令行参数配置
"""

import os
import sys
import argparse
import subprocess


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import httpx
        import pydantic
        print("✓ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False


def create_logs_directory():
    """创建日志目录"""
    os.makedirs("logs", exist_ok=True)
    print("✓ 日志目录已创建")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="vLLM Proxy API 服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本启动
  python run.py --vllm-api http://localhost:8000 --port 8002
  
  # 启用API密钥认证
  python run.py --vllm-api http://localhost:8000 --api-key "your-api-key"
  
  # 启用前后拦截（需要先启动safe_api服务）
  python run.py --vllm-api http://localhost:8000 \\
    --enable-front-intercept \\
    --enable-post-intercept \\
    --front-intercept-url http://localhost:8001/intercept \\
    --post-intercept-url http://localhost:8002/intercept \\
    --api-key "your-api-key" \\
    --enable-multi-api-keys \\
    --api-keys-file api_keys.json \\
    --disable-docs \\
    --port 8003
  
  # 仅启用前拦截（带安全配置）
  python run.py --vllm-api http://localhost:8000 \\
    --enable-front-intercept \\
    --front-intercept-url http://localhost:8001/intercept \\
    --api-key "your-api-key" \\
    --enable-multi-api-keys \\
    --disable-docs \\
    --port 8003
  
  # 生产环境（完整安全配置）
  python run.py --vllm-api http://localhost:8000 \\
    --enable-front-intercept \\
    --enable-post-intercept \\
    --api-key "prod-api-key" \\
    --enable-multi-api-keys \\
    --api-keys-file api_keys.json \\
    --disable-docs \\
    --workers 4 \\
    --max-connections 500 \\
    --port 8003
  
  # 开发环境（文档无需认证）
  python run.py --vllm-api http://localhost:8000 --docs-no-auth
  
  # 测试环境（文档需要认证）
  python run.py --vllm-api http://localhost:8000 --docs-require-auth --api-key "test-key"
  
  python run.py --help
        """
    )
    
    # vLLM API配置
    parser.add_argument(
        "--vllm-api", "--vllm-api-base",
        dest="vllm_api_base",
        default=os.getenv("VLLM_API_BASE", "http://localhost:8000"),
        help="vLLM API地址 (默认: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--vllm-api-key",
        dest="vllm_api_key",
        default=os.getenv("VLLM_API_KEY"),
        help="vLLM API密钥 (可选)"
    )
    
    # 服务配置
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="服务绑定地址 (默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.getenv("PORT", "8001")),
        help="服务端口 (默认: 8001)"
    )
    
    # 并发配置
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("WORKERS", "1")),
        help="Worker进程数量 (默认: 1, 生产环境建议设置为CPU核心数)"
    )
    
    parser.add_argument(
        "--max-connections",
        type=int,
        default=int(os.getenv("MAX_CONNECTIONS", "200")),
        help="最大连接数 (默认: 200)"
    )
    
    parser.add_argument(
        "--max-keepalive-connections",
        type=int,
        default=int(os.getenv("MAX_KEEPALIVE_CONNECTIONS", "100")),
        help="保持活跃连接数 (默认: 100)"
    )
    
    # 日志配置
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="日志级别 (默认: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        default=os.getenv("LOG_FILE", "logs/api.log"),
        help="API日志文件路径 (默认: logs/api.log)"
    )
    
    parser.add_argument(
        "--user-log-file",
        default=os.getenv("USER_LOG_FILE", "logs/user_requests.log"),
        help="用户请求日志文件路径 (默认: logs/user_requests.log)"
    )
    
    # API安全配置
    parser.add_argument(
        "--api-key",
        default=os.getenv("API_KEY"),
        help="API密钥验证 (可选，单个key，向后兼容)"
    )
    
    parser.add_argument(
        "--api-keys-file",
        default=os.getenv("API_KEYS_FILE", "api_keys.json"),
        help="多API key文件路径 (默认: api_keys.json)"
    )
    
    parser.add_argument(
        "--enable-multi-api-keys",
        action="store_true",
        default=None,  # 使用None让环境变量优先
        help="启用多API key支持 (默认: true)"
    )
    
    parser.add_argument(
        "--disable-multi-api-keys",
        action="store_true",
        default=False,
        help="禁用多API key支持"
    )
    
    # 文档安全配置
    parser.add_argument(
        "--enable-docs",
        action="store_true",
        default=None,  # 使用None让环境变量优先
        help="启用API文档 (默认: true)"
    )
    
    parser.add_argument(
        "--disable-docs",
        action="store_true",
        default=False,
        help="禁用API文档 (生产环境推荐)"
    )
    
    parser.add_argument(
        "--docs-require-auth",
        action="store_true", 
        default=None,  # 使用None让环境变量优先
        help="文档需要API Key认证 (默认: true)"
    )
    
    parser.add_argument(
        "--docs-no-auth",
        action="store_true",
        default=False,
        help="文档无需认证 (仅开发环境推荐)"
    )
    
    # 内容拦截配置
    parser.add_argument(
        "--enable-front-intercept",
        action="store_true",
        help="启用前拦截 (用户输入检查)"
    )
    
    parser.add_argument(
        "--enable-post-intercept", 
        action="store_true",
        help="启用后拦截 (模型输出检查)"
    )
    
    parser.add_argument(
        "--front-intercept-url",
        default=os.getenv("FRONT_INTERCEPT_URL", "http://localhost:8001/intercept"),
        help="前拦截API地址 (默认: http://localhost:8001/intercept)"
    )
    
    parser.add_argument(
        "--post-intercept-url",
        default=os.getenv("POST_INTERCEPT_URL", "http://localhost:8002/intercept"),
        help="后拦截API地址 (默认: http://localhost:8002/intercept)"
    )
    
    parser.add_argument(
        "--intercept-timeout",
        type=float,
        default=float(os.getenv("INTERCEPT_TIMEOUT", "5.0")),
        help="拦截API超时时间/秒 (默认: 5.0)"
    )

    # 开发选项
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载 (仅开发时使用)"
    )
    
    return parser.parse_args()


def apply_config(args):
    """将命令行参数应用到环境变量"""
    # 处理文档配置逻辑
    enable_docs = None
    docs_require_auth = None
    
    # 处理文档启用/禁用
    if args.disable_docs:
        enable_docs = "false"
    elif args.enable_docs:
        enable_docs = "true"
    # 如果都没设置，保持None让环境变量优先
    
    # 处理文档认证
    if args.docs_no_auth:
        docs_require_auth = "false"
    elif args.docs_require_auth:
        docs_require_auth = "true"
    # 如果都没设置，保持None让环境变量优先
    
    # 处理多API key配置
    enable_multi_api_keys = None
    if args.disable_multi_api_keys:
        enable_multi_api_keys = "false"
    elif args.enable_multi_api_keys:
        enable_multi_api_keys = "true"
    # 如果都没设置，保持None让环境变量优先
    
    # 将命令行参数映射到环境变量
    config_mapping = {
        "VLLM_API_BASE": args.vllm_api_base,
        "VLLM_API_KEY": args.vllm_api_key,
        "HOST": args.host,
        "PORT": str(args.port),
        "WORKERS": str(args.workers),
        "MAX_CONNECTIONS": str(args.max_connections),
        "MAX_KEEPALIVE_CONNECTIONS": str(args.max_keepalive_connections),
        "LOG_LEVEL": args.log_level,
        "LOG_FILE": args.log_file,
        "USER_LOG_FILE": args.user_log_file,
        "API_KEY": args.api_key,
        "API_KEYS_FILE": args.api_keys_file,
        "ENABLE_MULTI_API_KEYS": enable_multi_api_keys,
        "ENABLE_DOCS": enable_docs,
        "DOCS_REQUIRE_AUTH": docs_require_auth,
        # 拦截配置
        "ENABLE_FRONT_INTERCEPT": "true" if args.enable_front_intercept else None,
        "ENABLE_POST_INTERCEPT": "true" if args.enable_post_intercept else None,
        "FRONT_INTERCEPT_URL": args.front_intercept_url,
        "POST_INTERCEPT_URL": args.post_intercept_url,
        "INTERCEPT_TIMEOUT": str(args.intercept_timeout),
        "USE_LOCAL_INTERCEPT": "false",  # 命令行模式默认使用远程API
    }
    
    # 设置环境变量（只设置非None的值）
    for key, value in config_mapping.items():
        if value is not None:
            os.environ[key] = value
    
    return config_mapping


def main():
    """主函数"""
    print("vLLM Proxy API 启动器")
    print("=" * 50)
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 创建日志目录
    create_logs_directory()
    
    # 应用配置
    config = apply_config(args)
    
    # 显示当前配置
    print("\n当前配置:")
    print(f"  vLLM API地址: {config['VLLM_API_BASE']}")
    print(f"  服务地址: {config['HOST']}:{config['PORT']}")
    print(f"  Worker进程数: {config['WORKERS']}")
    print(f"  最大连接数: {config['MAX_CONNECTIONS']}")
    print(f"  保持活跃连接数: {config['MAX_KEEPALIVE_CONNECTIONS']}")
    print(f"  日志级别: {config['LOG_LEVEL']}")
    print(f"  API日志: {config['LOG_FILE']}")
    print(f"  用户日志: {config['USER_LOG_FILE']}")
    if config.get('VLLM_API_KEY'):
        print(f"  vLLM API密钥: ****{config['VLLM_API_KEY'][-4:]}")
    if config.get('API_KEY'):
        print(f"  API密钥验证: 已启用 (单个key)")
    
    # 显示多API key配置
    enable_multi_api_keys = os.getenv("ENABLE_MULTI_API_KEYS", "true").lower() in ("true", "1", "yes")
    api_keys_file = config.get('API_KEYS_FILE', 'api_keys.json')
    
    if enable_multi_api_keys:
        print(f"  多API key支持: 已启用")
        print(f"  API key文件: {api_keys_file}")
        # 检查文件是否存在
        if os.path.exists(api_keys_file):
            try:
                import json
                with open(api_keys_file, 'r') as f:
                    keys_data = json.load(f)
                if isinstance(keys_data, dict):
                    key_count = len(keys_data)
                elif isinstance(keys_data, list):
                    key_count = len(keys_data)
                else:
                    key_count = 0
                print(f"  已加载API keys: {key_count} 个")
            except Exception as e:
                print(f"  警告: 无法读取API key文件: {e}")
        else:
            print(f"  警告: API key文件不存在: {api_keys_file}")
    else:
        print(f"  多API key支持: 已禁用")
    
    # 显示安全配置
    enable_docs = os.getenv("ENABLE_DOCS", "true").lower() in ("true", "1", "yes")
    docs_require_auth = os.getenv("DOCS_REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")
    
    print(f"  API文档: {'已启用' if enable_docs else '已禁用'}")
    if enable_docs:
        print(f"  文档认证: {'需要' if docs_require_auth else '无需'}API Key")
    
    # 显示拦截配置
    enable_front_intercept = os.getenv("ENABLE_FRONT_INTERCEPT", "false").lower() in ("true", "1", "yes")
    enable_post_intercept = os.getenv("ENABLE_POST_INTERCEPT", "false").lower() in ("true", "1", "yes")
    
    if enable_front_intercept or enable_post_intercept:
        print(f"\n拦截配置:")
        if enable_front_intercept:
            print(f"  前拦截: 已启用 - {config.get('FRONT_INTERCEPT_URL')}")
        if enable_post_intercept:
            print(f"  后拦截: 已启用 - {config.get('POST_INTERCEPT_URL')}")
        print(f"  超时时间: {config.get('INTERCEPT_TIMEOUT')}秒")
        print(f"  拦截模式: 远程API模式")
    else:
        print(f"\n拦截配置: 未启用")
    
    print(f"\n服务地址:")
    print(f"  API文档: http://{config['HOST']}:{config['PORT']}/docs")
    print(f"  健康检查: http://{config['HOST']}:{config['PORT']}/health")
    print(f"  OpenAI兼容接口: http://{config['HOST']}:{config['PORT']}/v1/chat/completions")
    
    print(f"\n启动服务...")
    
    # 启动服务
    try:
        from main import app
        import uvicorn
        
        # 确定是否使用多进程
        workers = int(config["WORKERS"])
        if workers > 1 and args.reload:
            print("警告: reload模式下不支持多worker，将使用单worker")
            workers = 1
        
        uvicorn.run(
            "main:app" if workers > 1 else app,  # 多worker时需要使用字符串路径
            host=config["HOST"],
            port=int(config["PORT"]),
            workers=workers if workers > 1 else None,
            log_level=config["LOG_LEVEL"].lower(),
            reload=args.reload,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n✓ 服务已停止")
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 