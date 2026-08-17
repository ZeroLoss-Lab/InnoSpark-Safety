#!/usr/bin/env python3
"""
增强版API服务启动脚本
支持：
- 可控制前拦截/后拦截/RAG开关
- 多API密钥支持
- 文档访问控制
- 完整的服务管理
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
from concurrent.futures import ThreadPoolExecutor
import threading


class EnhancedAPIStarter:
    """增强版API启动器"""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
        # 默认配置
        self.api_host = "0.0.0.0"
        self.api_port = "8003"
        self.front_intercept_port = "8001"
        self.post_intercept_port = "8002"
        self.vllm_api_base = "http://localhost:8000"
        self.rag_service_url = "http://localhost:8000/retrieve"
        
        # 功能开关
        self.enable_front_intercept = True
        self.enable_post_intercept = True
        self.enable_rag = True
        self.enable_docs = False  # 默认禁用文档
        
        # API密钥配置
        self.api_keys_file = "api_keys.json"
        self.single_api_key = None
        
        # 路径配置
        self.safe_api_dir = Path("safe_api")
        
    def print_colored(self, message, color_code="0"):
        """打印彩色文本"""
        print(f"\033[{color_code}m{message}\033[0m")
    
    def print_success(self, message):
        self.print_colored(f"✅ {message}", "32")
    
    def print_warning(self, message):
        self.print_colored(f"⚠️  {message}", "33")
    
    def print_error(self, message):
        self.print_colored(f"❌ {message}", "31")
    
    def print_info(self, message):
        self.print_colored(f"ℹ️  {message}", "34")
    
    def print_header(self):
        """打印标题"""
        self.print_colored("=" * 60, "36")
        self.print_colored("  增强版API服务启动器", "36")
        self.print_colored("=" * 60, "36")
    
    def create_api_keys_file(self):
        """创建API密钥文件"""
        if not Path(self.api_keys_file).exists():
            # 创建默认的API密钥文件，使用与现有格式一致的结构
            default_keys = {
                "sk-your-api-key-1": {
                    "created_at": "2024-01-01T00:00:00",
                    "last_used": None,
                    "usage_count": 0,
                    "description": "主要API key",
                    "enabled": True
                },
                "sk-your-api-key-2": {
                    "created_at": "2024-01-01T00:00:00",
                    "last_used": None,
                    "usage_count": 0,
                    "description": "备用API key",
                    "enabled": True
                },
                "sk-your-api-key-3": {
                    "created_at": "2024-01-01T00:00:00",
                    "last_used": None,
                    "usage_count": 0,
                    "description": "测试API key",
                    "enabled": True
                }
            }
            
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(default_keys, f, ensure_ascii=False, indent=2)
            
            self.print_success(f"创建默认API密钥文件: {self.api_keys_file}")
        else:
            self.print_info(f"使用现有API密钥文件: {self.api_keys_file}")
    
    def validate_api_keys_file(self):
        """验证API密钥文件"""
        try:
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            
            if not isinstance(keys_data, dict):
                self.print_error("API密钥文件格式错误：应为JSON对象")
                return False
            
            enabled_keys = [k for k, v in keys_data.items() if v.get('enabled', True)]
            if not enabled_keys:
                self.print_error("没有可用的API密钥")
                return False
            
            self.print_success(f"API密钥文件验证通过，共 {len(enabled_keys)} 个可用密钥")
            return True
            
        except Exception as e:
            self.print_error(f"API密钥文件验证失败: {e}")
            return False
    
    def create_demo_data(self):
        """创建演示数据"""
        self.print_info("创建演示数据...")
        
        # 创建目录
        data_dir = self.safe_api_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # 创建文件
        files_to_create = [
            (data_dir / "high_sensitive_keywords.json", high_sensitive_keywords),
            (data_dir / "high_sensitive_keywords-2.json", medium_sensitive_keywords),
            (data_dir / "blacklist_1w.json", blacklist_1w)
        ]
        
        created_count = 0
        for file_path, data in files_to_create:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                created_count += 1
        
        if created_count > 0:
            self.print_success(f"创建了 {created_count} 个数据文件")
    
    def start_front_intercept_service(self):
        """启动前拦截服务"""
        if not self.enable_front_intercept:
            self.print_info("前拦截已禁用，跳过启动")
            return True
            
        self.print_info(f"启动前拦截BERT API服务 (端口 {self.front_intercept_port})...")
        
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "safe_api.front_intercept_api:app",
                "--host", "0.0.0.0",
                "--port", self.front_intercept_port
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(("前拦截API", process))
            
            # 等待服务启动
            if self.wait_for_service(f"http://localhost:{self.front_intercept_port}/health", "前拦截API", 20):
                self.print_success(f"前拦截API服务启动成功 (端口 {self.front_intercept_port})")
                return True
            else:
                self.print_error("前拦截API服务启动超时")
                return False
                
        except Exception as e:
            self.print_error(f"前拦截API服务启动失败: {e}")
            return False
    
    def start_post_intercept_service(self):
        """启动后拦截服务"""
        if not self.enable_post_intercept:
            self.print_info("后拦截已禁用，跳过启动")
            return True
            
        self.print_info(f"启动后拦截BERT API服务 (端口 {self.post_intercept_port})...")
        
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "safe_api.post_intercept_api:app",
                "--host", "0.0.0.0",
                "--port", self.post_intercept_port
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(("后拦截API", process))
            
            # 等待服务启动
            if self.wait_for_service(f"http://localhost:{self.post_intercept_port}/health", "后拦截API", 20):
                self.print_success(f"后拦截API服务启动成功 (端口 {self.post_intercept_port})")
                return True
            else:
                self.print_error("后拦截API服务启动超时")
                return False
                
        except Exception as e:
            self.print_error(f"后拦截API服务启动失败: {e}")
            return False
    
    def start_main_api_service(self):
        """启动主API服务"""
        self.print_info(f"启动主API服务 (端口 {self.api_port})...")
        
        # 设置环境变量
        env_vars = {
            # 服务配置
            "VLLM_API_BASE": self.vllm_api_base,
            "HOST": self.api_host,
            "PORT": self.api_port,
            
            # API密钥配置
            "ENABLE_MULTI_API_KEYS": "true",
            "API_KEYS_FILE": self.api_keys_file,
            
            # 文档配置
            "ENABLE_DOCS": str(self.enable_docs).lower(),
            "DOCS_REQUIRE_AUTH": "true",  # 即使启用文档也需要认证
            
            # 拦截器配置
            "ENABLE_FRONT_INTERCEPT": str(self.enable_front_intercept).lower(),
            "ENABLE_POST_INTERCEPT": str(self.enable_post_intercept).lower(),
            "USE_LOCAL_INTERCEPT": "false",  # 使用远程拦截模式
            
            # 远程拦截API地址
            "FRONT_INTERCEPT_URL": f"http://localhost:{self.front_intercept_port}/intercept",
            "POST_INTERCEPT_URL": f"http://localhost:{self.post_intercept_port}/intercept",
            
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
            "INTERCEPT_TIMEOUT": "10.0",
            
            # 日志配置
            "LOG_LEVEL": "INFO",
            "LOG_FILE": "logs/api.log",
            "USER_LOG_FILE": "logs/user_requests.log"
        }
        
        # 如果指定了单个API密钥，也设置它（向后兼容）
        if self.single_api_key:
            env_vars["API_KEY"] = self.single_api_key
        
        # 应用环境变量
        env = os.environ.copy()
        env.update(env_vars)
        
        try:
            # 创建logs目录
            Path("logs").mkdir(exist_ok=True)
            
            process = subprocess.Popen([
                sys.executable, "main.py"
            ], env=env)
            
            self.processes.append(("主API服务", process))
            
            # 等待服务启动
            if self.wait_for_service(f"http://localhost:{self.api_port}/health", "主API服务", 15):
                self.print_success(f"主API服务启动成功 (端口 {self.api_port})")
                return True
            else:
                self.print_error("主API服务启动超时")
                return False
                
        except Exception as e:
            self.print_error(f"主API服务启动失败: {e}")
            return False
    
    def wait_for_service(self, url, service_name, max_wait=30):
        """等待服务启动"""
        self.print_info(f"等待 {service_name} 启动...")
        
        for i in range(max_wait):
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                self.print_info(f"等待 {service_name} 启动... ({i}/{max_wait})")
        
        return False
    
    def check_external_services(self):
        """检查外部服务状态"""
        self.print_info("检查外部服务状态...")
        
        services_to_check = []
        
        # 检查vLLM服务
        services_to_check.append(("vLLM服务", self.vllm_api_base + "/v1/models", "GET"))
        
        # 如果启用RAG，检查RAG服务
        if self.enable_rag:
            services_to_check.append(("RAG服务", self.rag_service_url, "POST"))
        
        for service_name, url, method in services_to_check:
            try:
                if method == "POST":
                    response = requests.post(url, json={"query": "test", "top_k": 1}, timeout=5)
                else:
                    response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    self.print_success(f"{service_name} 运行正常")
                else:
                    self.print_warning(f"{service_name} 响应异常: {response.status_code}")
            except requests.RequestException:
                self.print_warning(f"{service_name} 不可访问 ({url})")
                if service_name == "RAG服务":
                    self.print_info("RAG服务不可用，将禁用RAG功能")
                    self.enable_rag = False
    
    def print_service_info(self):
        """打印服务信息"""
        print()
        self.print_colored("🎉 服务启动完成！", "32")
        print()
        self.print_colored("📋 服务信息:", "36")
        
        if self.enable_front_intercept:
            print(f"  前拦截API:  http://localhost:{self.front_intercept_port}")
        if self.enable_post_intercept:
            print(f"  后拦截API:  http://localhost:{self.post_intercept_port}")
        print(f"  主API服务:  http://localhost:{self.api_port}")
        
        print()
        self.print_colored("📖 API文档:", "36")
        if self.enable_docs:
            print(f"  主API文档:  http://localhost:{self.api_port}/docs (需要认证)")
        else:
            print("  API文档已禁用")
        
        if self.enable_front_intercept:
            print(f"  前拦截文档: http://localhost:{self.front_intercept_port}/docs")
        if self.enable_post_intercept:
            print(f"  后拦截文档: http://localhost:{self.post_intercept_port}/docs")
        
        print()
        self.print_colored("🔧 功能状态:", "36")
        print(f"  前拦截: {'✅ 启用' if self.enable_front_intercept else '❌ 禁用'}")
        print(f"  后拦截: {'✅ 启用' if self.enable_post_intercept else '❌ 禁用'}")
        print(f"  RAG系统: {'✅ 启用' if self.enable_rag else '❌ 禁用'}")
        print(f"  API文档: {'✅ 启用' if self.enable_docs else '❌ 禁用'}")
        
        print()
        self.print_colored("🔑 API密钥:", "36")
        print(f"  密钥文件: {self.api_keys_file}")
        
        # 显示可用的API密钥
        try:
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            enabled_keys = [k for k, v in keys_data.items() if v.get('enabled', True)]
            print(f"  可用密钥: {len(enabled_keys)} 个")
            for key in enabled_keys[:3]:  # 只显示前3个
                print(f"    - {key[:12]}...")
            if len(enabled_keys) > 3:
                print(f"    - ... 还有 {len(enabled_keys) - 3} 个")
        except:
            pass
        
        print()
        self.print_colored("💡 测试命令:", "36")
        if enabled_keys:
            test_key = enabled_keys[0]
            print(f"  curl -X POST 'http://localhost:{self.api_port}/v1/chat/completions' \\")
            print(f"    -H 'Authorization: Bearer {test_key}' \\")
            print(f"    -H 'Content-Type: application/json' \\")
            print(f"    -d '{{\"model\":\"qwen7b-in\",\"messages\":[{{\"role\":\"user\",\"content\":\"你好\"}}]}}'")
        
        print()
        self.print_colored("⚠️  按 Ctrl+C 停止所有服务", "33")
        self.print_colored("=" * 60, "36")
    
    def monitor_processes(self):
        """监控进程"""
        def monitor_single_process(name, process):
            while self.running:
                if process.poll() is not None:
                    self.print_warning(f"{name} 意外退出，退出码: {process.returncode}")
                    break
                time.sleep(1)
        
        with ThreadPoolExecutor(max_workers=len(self.processes)) as executor:
            for name, process in self.processes:
                executor.submit(monitor_single_process, name, process)
            
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.print_info("收到停止信号...")
                self.stop_all_services()
    
    def stop_all_services(self):
        """停止所有服务"""
        self.running = False
        self.print_info("正在停止所有服务...")
        
        for name, process in reversed(self.processes):
            try:
                self.print_info(f"停止 {name}...")
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                    self.print_success(f"{name} 已停止")
                except subprocess.TimeoutExpired:
                    self.print_warning(f"{name} 未响应，强制终止...")
                    process.kill()
                    process.wait()
                    self.print_success(f"{name} 已强制停止")
                    
            except Exception as e:
                self.print_error(f"停止 {name} 时出错: {e}")
        
        self.print_success("所有服务已停止")
    
    def start_all_services(self):
        """启动所有服务"""
        self.print_header()
        
        # 创建/验证API密钥文件
        self.create_api_keys_file()
        if not self.validate_api_keys_file():
            return False
        
        # 创建演示数据
        self.create_demo_data()
        
        # 检查外部服务状态
        self.check_external_services()
        
        print()
        self.print_info("开始启动服务...")
        
        # 按顺序启动服务
        services = []
        
        if self.enable_front_intercept:
            services.append(("前拦截BERT API", self.start_front_intercept_service))
        
        if self.enable_post_intercept:
            services.append(("后拦截BERT API", self.start_post_intercept_service))
        
        services.append(("主API服务", self.start_main_api_service))
        
        for service_name, start_func in services:
            if not start_func():
                self.print_error(f"{service_name} 启动失败，停止启动流程")
                self.stop_all_services()
                return False
            time.sleep(2)  # 等待服务稳定
        
        # 打印服务信息
        self.print_service_info()
        
        # 监控进程
        self.monitor_processes()
        
        return True


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="增强版API服务启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python start_enhanced_api.py                              # 默认启动所有功能
  python start_enhanced_api.py --no-front --no-post        # 仅启动主API，禁用拦截
  python start_enhanced_api.py --no-rag                     # 禁用RAG功能
  python start_enhanced_api.py --enable-docs               # 启用API文档
  python start_enhanced_api.py --api-keys custom_keys.json # 使用自定义API密钥文件
  python start_enhanced_api.py --port 9000 --single-key sk-test-123  # 自定义端口和单个密钥
        """
    )
    
    # 服务配置
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="服务绑定地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=str, default="8003",
        help="主API服务端口 (默认: 8003)"
    )
    parser.add_argument(
        "--vllm", type=str, default="http://localhost:8000",
        help="vLLM服务地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--rag", type=str, default="http://localhost:8000/retrieve",
        help="RAG服务地址 (默认: http://localhost:8000/retrieve)"
    )
    
    # 功能开关
    parser.add_argument(
        "--no-front", action="store_true",
        help="禁用前拦截功能"
    )
    parser.add_argument(
        "--no-post", action="store_true",
        help="禁用后拦截功能"
    )
    parser.add_argument(
        "--no-rag", action="store_true",
        help="禁用RAG功能"
    )
    parser.add_argument(
        "--enable-docs", action="store_true",
        help="启用API文档访问（默认禁用）"
    )
    
    # API密钥配置
    parser.add_argument(
        "--api-keys", type=str, default="api_keys.json",
        help="API密钥JSON文件路径 (默认: api_keys.json)"
    )
    parser.add_argument(
        "--single-key", type=str,
        help="使用单个API密钥（向后兼容）"
    )
    
    # 端口配置
    parser.add_argument(
        "--front-port", type=str, default="8001",
        help="前拦截服务端口 (默认: 8001)"
    )
    parser.add_argument(
        "--post-port", type=str, default="8002",
        help="后拦截服务端口 (默认: 8002)"
    )
    
    return parser.parse_args()


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在关闭服务...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建启动器
    starter = EnhancedAPIStarter()
    
    # 设置参数
    starter.api_host = args.host
    starter.api_port = args.port
    starter.front_intercept_port = args.front_port
    starter.post_intercept_port = args.post_port
    starter.vllm_api_base = args.vllm
    starter.rag_service_url = args.rag
    
    # 功能开关
    starter.enable_front_intercept = not args.no_front
    starter.enable_post_intercept = not args.no_post
    starter.enable_rag = not args.no_rag
    starter.enable_docs = args.enable_docs
    
    # API密钥配置
    starter.api_keys_file = args.api_keys
    starter.single_api_key = args.single_key
    
    # 启动所有服务
    success = starter.start_all_services()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
