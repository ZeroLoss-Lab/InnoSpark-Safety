#!/usr/bin/env python3
"""
增强版拦截器API服务启动脚本 (Python版本)
支持完整的拦截逻辑：高敏词 -> 双阈值BERT -> 次高敏词 -> RAG系统

使用方法:
    python start_server.py                    # 默认配置启动
    python start_server.py --port 8002       # 指定端口
    python start_server.py --no-rag          # 禁用RAG
    python start_server.py --check-only      # 仅检查环境
"""

import os
import sys
import json
import time
import signal
import argparse
import subprocess
import requests
from pathlib import Path
from datetime import datetime


class Colors:
    """终端颜色定义"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class EnhancedInterceptorStarter:
    """增强版拦截器启动器"""
    
    def __init__(self):
        self.api_host = "0.0.0.0"
        self.api_port = "8001"
        self.vllm_api_base = "http://localhost:8000"
        self.rag_service_url = "http://localhost:8000/retrieve"
        self.api_key = "your_api_key_here"
        self.enable_rag = True
        self.enable_front_intercept = True
        self.enable_post_intercept = True
        self.check_only = False
        self.use_remote_intercept = False  # 是否使用远程拦截模式
        self.front_intercept_url = "http://localhost:8001/intercept"
        self.post_intercept_url = "http://localhost:8002/intercept"
        
    def print_colored(self, message, color=Colors.NC):
        """打印彩色文本"""
        print(f"{color}{message}{Colors.NC}")
    
    def print_success(self, message):
        self.print_colored(f"✅ {message}", Colors.GREEN)
    
    def print_warning(self, message):
        self.print_colored(f"⚠️  {message}", Colors.YELLOW)
    
    def print_error(self, message):
        self.print_colored(f"❌ {message}", Colors.RED)
    
    def print_info(self, message):
        self.print_colored(f"ℹ️  {message}", Colors.BLUE)
    
    def print_header(self):
        """打印标题"""
        self.print_colored("=" * 50, Colors.BLUE)
        self.print_colored("  增强版拦截器API服务启动脚本", Colors.BLUE)
        self.print_colored("=" * 50, Colors.BLUE)
    
    def check_python_environment(self):
        """检查Python环境"""
        self.print_info("检查Python环境...")
        
        # 检查Python版本
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.print_error(f"需要Python 3.8+，当前版本: {version.major}.{version.minor}")
            return False
        
        self.print_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    
    def check_dependencies(self):
        """检查依赖包"""
        self.print_info("检查Python依赖包...")
        
        required_packages = [
            "fastapi", "uvicorn", "transformers", "torch", 
            "aiohttp", "httpx", "pydantic", "pydantic_settings"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.print_warning(f"缺少以下依赖包: {', '.join(missing_packages)}")
            
            # 询问是否安装
            response = input("是否自动安装缺少的依赖包？(y/N): ")
            if response.lower() == 'y':
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", *missing_packages
                    ])
                    self.print_success("依赖包安装完成")
                except subprocess.CalledProcessError:
                    self.print_error("依赖包安装失败")
                    return False
            else:
                self.print_error("请手动安装缺少的依赖包")
                return False
        else:
            self.print_success("所有依赖包已安装")
        
        return True
    
    def check_required_files(self):
        """检查必要文件"""
        self.print_info("检查必要文件...")
        
        required_files = [
            "main.py", "config.py", "enhanced_interceptor.py",
            "rag_client.py", "rag_prompt_template.py", "logger_config.py"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            self.print_error(f"缺少以下必要文件: {', '.join(missing_files)}")
            return False
        
        self.print_success("所有必要文件存在")
        return True
    
    def create_demo_data(self):
        """创建演示数据文件"""
        self.print_info("创建演示数据文件...")
        
        # 创建目录
        directories = ["safe_api/data", "safe_api/models", "logs"]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # 高敏感关键词
        high_sensitive_keywords = {
            "keywords": [
                "placeholder_keyword_alpha",
                "placeholder_keyword_beta",
                "placeholder_keyword_gamma"
            ]
        }
        
        # 次高敏感关键词
        medium_sensitive_keywords = {
            "keywords": [
                "placeholder_topic_alpha",
                "placeholder_topic_beta",
                "placeholder_topic_gamma"
            ]
        }
        
        # 1w黑名单
        blacklist_1w = {
            "keywords": [
                "placeholder_category_alpha",
                "placeholder_category_beta",
                "placeholder_category_gamma"
            ]
        }
        
        # API密钥文件
        api_keys = {
            self.api_key: {
                "description": "默认API密钥",
                "created_at": datetime.now().isoformat(),
                "enabled": True,
                "usage_count": 0,
                "last_used": None
            }
        }
        
        # 创建文件
        files_to_create = [
            ("safe_api/data/high_sensitive_keywords.json", high_sensitive_keywords),
            ("safe_api/data/high_sensitive_keywords-2.json", medium_sensitive_keywords),
            ("safe_api/data/blacklist_1w.json", blacklist_1w),
            ("api_keys.json", api_keys)
        ]
        
        created_count = 0
        for file_path, data in files_to_create:
            if not Path(file_path).exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                created_count += 1
                self.print_success(f"创建文件: {file_path}")
        
        if created_count == 0:
            self.print_info("所有数据文件已存在")
        else:
            self.print_success(f"创建了 {created_count} 个数据文件")
    
    def setup_environment(self):
        """设置环境变量"""
        self.print_info("设置环境变量...")
        
        env_vars = {
            # 服务配置
            "VLLM_API_BASE": self.vllm_api_base,
            "HOST": self.api_host,
            "PORT": self.api_port,
            "API_KEY": self.api_key,
            "ENABLE_MULTI_API_KEYS": "true",
            
            # 拦截器配置
            "ENABLE_FRONT_INTERCEPT": str(self.enable_front_intercept).lower(),
            "ENABLE_POST_INTERCEPT": str(self.enable_post_intercept).lower(),
            "USE_LOCAL_INTERCEPT": str(not self.use_remote_intercept).lower(),
            
            # RAG系统配置
            "ENABLE_RAG": str(self.enable_rag).lower(),
            "RAG_SERVICE_URL": self.rag_service_url,
            "RAG_TOP_K": "5",
            "RAG_TIMEOUT": "10.0",
            
            # BERT双阈值配置
            "BERT_FRONT_HIGH_THRESHOLD": "0.97",
            "BERT_FRONT_LOW_THRESHOLD": "0.00002",
            "BERT_POST_THRESHOLD": "0.5",
            
            # 数据文件路径
            "HIGH_SENSITIVE_KEYWORDS_PATH": "./safe_api/data/high_sensitive_keywords.json",
            "MEDIUM_SENSITIVE_KEYWORDS_PATH": "./safe_api/data/high_sensitive_keywords-2.json",
            "BLACKLIST_1W_PATH": "./safe_api/data/blacklist_1w.json",
            
            # 超时配置
            "INTERCEPT_TIMEOUT": "5.0",
            
            # 日志配置
            "LOG_LEVEL": "INFO",
            "LOG_FILE": "logs/api.log",
            "USER_LOG_FILE": "logs/user_requests.log",
        }
        
        # 如果使用远程拦截模式，添加远程API地址
        if self.use_remote_intercept:
            env_vars.update({
                "FRONT_INTERCEPT_URL": self.front_intercept_url,
                "POST_INTERCEPT_URL": self.post_intercept_url
            })
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        self.print_success("环境变量设置完成")
    
    def check_services(self):
        """检查相关服务状态"""
        self.print_info("检查相关服务状态...")
        
        # 检查vLLM服务
        try:
            response = requests.get(f"{self.vllm_api_base}/v1/models", timeout=5)
            if response.status_code == 200:
                self.print_success(f"vLLM服务运行正常 ({self.vllm_api_base})")
            else:
                self.print_warning(f"vLLM服务响应异常: {response.status_code}")
        except requests.RequestException:
            self.print_warning(f"vLLM服务不可访问 ({self.vllm_api_base})")
            self.print_info("请确保vLLM服务已启动")
        
        # 检查RAG服务
        if self.enable_rag:
            try:
                response = requests.post(
                    self.rag_service_url,
                    json={"query": "test", "top_k": 1},
                    timeout=5
                )
                if response.status_code == 200:
                    self.print_success(f"RAG服务运行正常 ({self.rag_service_url})")
                else:
                    self.print_warning(f"RAG服务响应异常: {response.status_code}")
                    self.print_info("将禁用RAG功能")
                    self.enable_rag = False
                    os.environ["ENABLE_RAG"] = "false"
            except requests.RequestException:
                self.print_warning(f"RAG服务不可访问 ({self.rag_service_url})")
                self.print_info("将禁用RAG功能")
                self.enable_rag = False
                os.environ["ENABLE_RAG"] = "false"
    
    def print_configuration(self):
        """打印当前配置"""
        print()
        self.print_colored("📋 当前配置:", Colors.CYAN)
        print(f"  服务地址: http://{self.api_host}:{self.api_port}")
        print(f"  vLLM服务: {self.vllm_api_base}")
        print(f"  前拦截: {'启用' if self.enable_front_intercept else '禁用'}")
        print(f"  后拦截: {'启用' if self.enable_post_intercept else '禁用'}")
        print(f"  RAG系统: {'启用' if self.enable_rag else '禁用'}")
        if self.enable_rag:
            print(f"  RAG服务: {self.rag_service_url}")
        print(f"  拦截模式: {'远程API' if self.use_remote_intercept else '本地集成'}")
        if self.use_remote_intercept:
            print(f"  前拦截API: {self.front_intercept_url}")
            print(f"  后拦截API: {self.post_intercept_url}")
        print(f"  API密钥: {self.api_key[:8]}...")
        print()
    
    def start_api_server(self):
        """启动API服务"""
        self.print_info("启动增强版拦截器API服务...")
        
        # 打印配置信息
        self.print_configuration()
        
        self.print_info("使用 Ctrl+C 停止服务")
        self.print_info(f"API文档: http://{self.api_host}:{self.api_port}/docs")
        print()
        
        try:
            # 启动主服务
            subprocess.run([sys.executable, "main.py"], check=True)
        except KeyboardInterrupt:
            self.print_colored("\n⏹️  服务已停止", Colors.YELLOW)
        except subprocess.CalledProcessError as e:
            self.print_error(f"服务启动失败: {e}")
            return False
        except Exception as e:
            self.print_error(f"未知错误: {e}")
            return False
        
        return True
    
    def run_checks(self):
        """运行所有检查"""
        checks = [
            self.check_python_environment,
            self.check_dependencies, 
            self.check_required_files
        ]
        
        for check in checks:
            if not check():
                return False
        
        return True
    
    def run(self):
        """运行启动流程"""
        # 显示标题
        self.print_header()
        
        # 运行检查
        if not self.run_checks():
            self.print_error("环境检查失败，请解决问题后重试")
            return False
        
        # 创建演示数据
        self.create_demo_data()
        
        # 设置环境变量
        self.setup_environment()
        
        # 检查服务状态
        self.check_services()
        
        # 如果只是检查环境
        if self.check_only:
            self.print_success("环境检查完成，所有准备就绪！")
            return True
        
        # 启动API服务
        return self.start_api_server()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="增强版拦截器API服务启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python start_server.py                    # 默认配置启动
  python start_server.py --port 8002       # 指定端口启动
  python start_server.py --no-rag          # 禁用RAG功能
  python start_server.py --check-only      # 仅检查环境
  python start_server.py --vllm http://localhost:8000 --rag http://localhost:8000/retrieve
        """
    )
    
    parser.add_argument(
        "-p", "--port", type=str, default="8001",
        help="API服务端口 (默认: 8001)"
    )
    parser.add_argument(
        "-v", "--vllm", type=str, default="http://localhost:8000",
        help="vLLM服务地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "-r", "--rag", type=str, default="http://localhost:8000/retrieve",
        help="RAG服务地址 (默认: http://localhost:8000/retrieve)"
    )
    parser.add_argument(
        "-k", "--api-key", type=str, default="your_api_key_here",
        help="API密钥 (默认: your_api_key_here)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="服务绑定地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--no-rag", action="store_true",
        help="禁用RAG系统"
    )
    parser.add_argument(
        "--no-front", action="store_true",
        help="禁用前拦截"
    )
    parser.add_argument(
        "--no-post", action="store_true",
        help="禁用后拦截"
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="仅检查环境，不启动服务"
    )
    parser.add_argument(
        "--remote-intercept", action="store_true",
        help="使用远程拦截模式（需要先启动safe_api服务）"
    )
    parser.add_argument(
        "--front-intercept-url", type=str, default="http://localhost:8001/intercept",
        help="前拦截API地址 (默认: http://localhost:8001/intercept)"
    )
    parser.add_argument(
        "--post-intercept-url", type=str, default="http://localhost:8002/intercept",
        help="后拦截API地址 (默认: http://localhost:8002/intercept)"
    )
    
    return parser.parse_args()


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n{Colors.YELLOW}⏹️  收到停止信号，正在关闭服务...{Colors.NC}")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建启动器
    starter = EnhancedInterceptorStarter()
    
    # 设置参数
    starter.api_host = args.host
    starter.api_port = args.port
    starter.vllm_api_base = args.vllm
    starter.rag_service_url = args.rag
    starter.api_key = args.api_key
    starter.enable_rag = not args.no_rag
    starter.enable_front_intercept = not args.no_front
    starter.enable_post_intercept = not args.no_post
    starter.check_only = args.check_only
    starter.use_remote_intercept = args.remote_intercept
    starter.front_intercept_url = args.front_intercept_url
    starter.post_intercept_url = args.post_intercept_url
    
    # 运行启动流程
    success = starter.run()
    
    if success:
        starter.print_success("操作完成！")
    else:
        starter.print_error("操作失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
