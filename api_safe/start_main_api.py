#!/usr/bin/env python3
"""
主API服务启动脚本
连接到独立运行的safe_api和RAG服务
支持完全的功能控制和阈值配置
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


class MainAPIStarter:
    """主API服务启动器"""
    
    def __init__(self):
        self.process = None
        self.running = True
        
        # 默认配置
        self.api_host = "0.0.0.0"
        self.api_port = "8003"
        self.vllm_api_base = "http://localhost:8000"
        
        # 外部服务地址
        self.front_intercept_url = "http://localhost:8001/intercept"
        self.post_intercept_url = "http://localhost:8002/intercept"
        self.rag_service_url = "http://localhost:8000/retrieve"
        
        # 功能开关
        self.enable_front_intercept = True
        self.enable_post_intercept = True
        self.enable_rag = True
        self.enable_docs = False  # 默认禁用文档
        
        # BERT阈值配置
        self.bert_front_high_threshold = 0.97
        self.bert_front_low_threshold = 0.00002
        self.bert_post_threshold = 0.5
        
        # RAG配置
        self.rag_top_k = 5
        self.rag_timeout = 10.0
        
        # API密钥配置
        self.api_keys_file = "api_keys.json"
        self.single_api_key = None
        
        # 超时配置
        self.intercept_timeout = 10.0
        
        # 关键词文件路径配置
        self.high_sensitive_path = "./safe_api/data/high_sensitive_keywords.json"
        self.low_sensitive_path = "./safe_api/data/high_sensitive_keywords-2.json"
        
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
        self.print_colored("  主API服务启动器", "36")
        self.print_colored("=" * 60, "36")
    
    def validate_api_keys_file(self):
        """验证API密钥文件"""
        if not Path(self.api_keys_file).exists():
            self.print_error(f"API密钥文件不存在: {self.api_keys_file}")
            return False
            
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
    
    def check_external_services(self):
        """检查外部服务状态"""
        self.print_info("检查外部服务状态...")
        
        services_to_check = []
        
        # 检查vLLM服务
        services_to_check.append(("vLLM服务", self.vllm_api_base + "/v1/models", "GET"))
        
        # 检查前拦截服务
        if self.enable_front_intercept:
            services_to_check.append(("前拦截服务", self.front_intercept_url.replace('/intercept', '/health'), "GET"))
        
        # 检查后拦截服务
        if self.enable_post_intercept:
            services_to_check.append(("后拦截服务", self.post_intercept_url.replace('/intercept', '/health'), "GET"))
        
        # 检查RAG服务
        if self.enable_rag:
            services_to_check.append(("RAG服务", self.rag_service_url, "POST"))
        
        all_services_ok = True
        
        for service_name, url, method in services_to_check:
            try:
                if method == "POST":
                    response = requests.post(url, json={"query": "test", "top_k": 1}, timeout=5)
                else:
                    response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    self.print_success(f"{service_name} 运行正常 ({url})")
                else:
                    self.print_warning(f"{service_name} 响应异常: {response.status_code}")
                    if service_name == "RAG服务":
                        self.print_info("RAG服务异常，将禁用RAG功能")
                        self.enable_rag = False
                    elif "拦截" in service_name:
                        self.print_warning(f"{service_name}异常，但将继续启动")
            except requests.RequestException:
                self.print_warning(f"{service_name} 不可访问 ({url})")
                if service_name == "vLLM服务":
                    self.print_error("vLLM服务不可访问，无法启动主API服务")
                    all_services_ok = False
                elif service_name == "RAG服务":
                    self.print_info("RAG服务不可访问，将禁用RAG功能")
                    self.enable_rag = False
                elif "拦截" in service_name:
                    self.print_warning(f"{service_name}不可访问，但将继续启动")
        
        return all_services_ok
    
    def setup_environment(self):
        """设置环境变量"""
        self.print_info("设置环境变量...")
        
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
            
            # 拦截器配置 - 使用远程模式
            "ENABLE_FRONT_INTERCEPT": str(self.enable_front_intercept).lower(),
            "ENABLE_POST_INTERCEPT": str(self.enable_post_intercept).lower(),
            "USE_LOCAL_INTERCEPT": "false",  # 强制使用远程模式
            
            # 远程拦截API地址
            "FRONT_INTERCEPT_URL": self.front_intercept_url,
            "POST_INTERCEPT_URL": self.post_intercept_url,
            "INTERCEPT_TIMEOUT": str(self.intercept_timeout),
            
            # RAG系统配置
            "ENABLE_RAG": str(self.enable_rag).lower(),
            "RAG_SERVICE_URL": self.rag_service_url,
            "RAG_TOP_K": str(self.rag_top_k),
            "RAG_TIMEOUT": str(self.rag_timeout),
            
            # BERT阈值配置（传递给增强版拦截器，如果使用）
            "BERT_FRONT_HIGH_THRESHOLD": str(self.bert_front_high_threshold),
            "BERT_FRONT_LOW_THRESHOLD": str(self.bert_front_low_threshold),
            "BERT_POST_THRESHOLD": str(self.bert_post_threshold),
            
            # 关键词数据文件路径
            "HIGH_SENSITIVE_KEYWORDS_PATH": self.high_sensitive_path,
            "MEDIUM_SENSITIVE_KEYWORDS_PATH": self.low_sensitive_path,
            
            # 日志配置
            "LOG_LEVEL": "INFO",
            "LOG_FILE": "logs/api.log",
            "USER_LOG_FILE": "logs/user_requests.log"
        }
        
        # 如果指定了单个API密钥，也设置它（向后兼容）
        if self.single_api_key:
            env_vars["API_KEY"] = self.single_api_key
        
        # 应用环境变量
        for key, value in env_vars.items():
            os.environ[key] = value
        
        self.print_success("环境变量设置完成")
    
    def start_main_api_service(self):
        """启动主API服务"""
        self.print_info(f"启动主API服务 (端口 {self.api_port})...")
        
        try:
            # 创建logs目录
            Path("logs").mkdir(exist_ok=True)
            
            self.process = subprocess.Popen([
                sys.executable, "main.py"
            ])
            
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
    
    def print_service_info(self):
        """打印服务信息"""
        print()
        self.print_colored("🎉 主API服务启动完成！", "32")
        print()
        self.print_colored("📋 服务信息:", "36")
        print(f"  主API服务:  http://localhost:{self.api_port}")
        print(f"  vLLM服务:   {self.vllm_api_base}")
        
        print()
        self.print_colored("🔗 外部服务连接:", "36")
        if self.enable_front_intercept:
            print(f"  前拦截API:  {self.front_intercept_url}")
        if self.enable_post_intercept:
            print(f"  后拦截API:  {self.post_intercept_url}")
        if self.enable_rag:
            print(f"  RAG服务:    {self.rag_service_url}")
        
        print()
        self.print_colored("🔧 功能配置:", "36")
        print(f"  前拦截:     {'✅ 启用' if self.enable_front_intercept else '❌ 禁用'}")
        print(f"  后拦截:     {'✅ 启用' if self.enable_post_intercept else '❌ 禁用'}")
        print(f"  RAG系统:    {'✅ 启用' if self.enable_rag else '❌ 禁用'}")
        print(f"  API文档:    {'✅ 启用' if self.enable_docs else '❌ 禁用'}")
        
        print()
        self.print_colored("⚙️  BERT阈值配置:", "36")
        if self.enable_front_intercept:
            print(f"  前拦截高阈值: {self.bert_front_high_threshold}")
            print(f"  前拦截低阈值: {self.bert_front_low_threshold}")
        if self.enable_post_intercept:
            print(f"  后拦截阈值:   {self.bert_post_threshold}")
        
        print()
        self.print_colored("🔑 API密钥:", "36")
        print(f"  密钥文件: {self.api_keys_file}")
        
        # 显示可用的API密钥
        try:
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            enabled_keys = [k for k, v in keys_data.items() if v.get('enabled', True)]
            print(f"  可用密钥: {len(enabled_keys)} 个")
            for key in enabled_keys[:2]:  # 只显示前2个
                print(f"    - {key[:15]}...")
            if len(enabled_keys) > 2:
                print(f"    - ... 还有 {len(enabled_keys) - 2} 个")
        except:
            pass
        
        print()
        self.print_colored("📖 API文档:", "36")
        if self.enable_docs:
            print(f"  主API文档:  http://localhost:{self.api_port}/docs (需要认证)")
        else:
            print("  API文档已禁用")
        
        print()
        self.print_colored("💡 测试命令:", "36")
        if 'enabled_keys' in locals() and enabled_keys:
            test_key = enabled_keys[0]
            print(f"  curl -X POST 'http://localhost:{self.api_port}/v1/chat/completions' \\")
            print(f"    -H 'Authorization: Bearer {test_key}' \\")
            print(f"    -H 'Content-Type: application/json' \\")
            print(f"    -d '{{\"model\":\"qwen7b-in\",\"messages\":[{{\"role\":\"user\",\"content\":\"你好\"}}]}}'")
        
        print()
        self.print_colored("⚠️  按 Ctrl+C 停止服务", "33")
        self.print_colored("=" * 60, "36")
    
    def monitor_process(self):
        """监控进程"""
        try:
            while self.running:
                if self.process and self.process.poll() is not None:
                    self.print_warning(f"主API服务意外退出，退出码: {self.process.returncode}")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            self.print_info("收到停止信号...")
            self.stop_service()
    
    def stop_service(self):
        """停止服务"""
        self.running = False
        
        if self.process:
            try:
                self.print_info("正在停止主API服务...")
                self.process.terminate()
                
                try:
                    self.process.wait(timeout=5)
                    self.print_success("主API服务已停止")
                except subprocess.TimeoutExpired:
                    self.print_warning("主API服务未响应，强制终止...")
                    self.process.kill()
                    self.process.wait()
                    self.print_success("主API服务已强制停止")
                    
            except Exception as e:
                self.print_error(f"停止主API服务时出错: {e}")
    
    def start(self):
        """启动主API服务"""
        self.print_header()
        
        # 验证API密钥文件
        if not self.validate_api_keys_file():
            return False
        
        # 检查外部服务状态
        if not self.check_external_services():
            return False
        
        # 设置环境变量
        self.setup_environment()
        
        # 启动主API服务
        if not self.start_main_api_service():
            return False
        
        # 打印服务信息
        self.print_service_info()
        
        # 监控进程
        self.monitor_process()
        
        return True


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="主API服务启动器 - 连接到独立的safe_api和RAG服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python start_main_api.py                                    # 默认配置启动
  python start_main_api.py --no-front --no-post              # 禁用拦截功能
  python start_main_api.py --no-rag                           # 禁用RAG功能
  python start_main_api.py --enable-docs                      # 启用API文档
  python start_main_api.py --front-url http://192.168.1.100:8001/intercept  # 自定义前拦截地址
  python start_main_api.py --bert-front-high 0.95 --bert-post 0.6  # 自定义BERT阈值
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
    
    # 外部服务地址
    parser.add_argument(
        "--front-url", type=str, default="http://localhost:8001/intercept",
        help="前拦截API地址 (默认: http://localhost:8001/intercept)"
    )
    parser.add_argument(
        "--post-url", type=str, default="http://localhost:8002/intercept",
        help="后拦截API地址 (默认: http://localhost:8002/intercept)"
    )
    parser.add_argument(
        "--rag-url", type=str, default="http://localhost:8000/retrieve",
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
    
    # RAG配置
    parser.add_argument(
        "--rag-top-k", type=int, default=5,
        help="RAG检索top-k数量 (默认: 5)"
    )
    parser.add_argument(
        "--rag-timeout", type=float, default=10.0,
        help="RAG服务超时时间 (默认: 10.0秒)"
    )
    
    # 关键词文件路径配置
    parser.add_argument(
        "--high-sensitive-path", type=str,
        default="./safe_api/data/high_sensitive_keywords.json", 
        help="高敏感关键词文件路径 (默认: ./safe_api/data/high_sensitive_keywords.json)"
    )
    parser.add_argument(
        "--low-sensitive-path", type=str,
        default="./safe_api/data/high_sensitive_keywords-2.json",
        help="低敏感关键词文件路径 (默认: ./safe_api/data/high_sensitive_keywords-2.json)"
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
    
    # 超时配置
    parser.add_argument(
        "--intercept-timeout", type=float, default=10.0,
        help="拦截服务超时时间 (默认: 10.0秒)"
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
    starter = MainAPIStarter()
    
    # 设置基本参数
    starter.api_host = args.host
    starter.api_port = args.port
    starter.vllm_api_base = args.vllm
    
    # 设置外部服务地址
    starter.front_intercept_url = args.front_url
    starter.post_intercept_url = args.post_url
    starter.rag_service_url = args.rag_url
    
    # 功能开关
    starter.enable_front_intercept = not args.no_front
    starter.enable_post_intercept = not args.no_post
    starter.enable_rag = not args.no_rag
    starter.enable_docs = args.enable_docs
    
    # BERT阈值配置
    starter.bert_front_high_threshold = args.bert_front_high
    starter.bert_front_low_threshold = args.bert_front_low
    starter.bert_post_threshold = args.bert_post
    
    # RAG配置
    starter.rag_top_k = args.rag_top_k
    starter.rag_timeout = args.rag_timeout
    
    # 关键词文件路径配置
    starter.high_sensitive_path = args.high_sensitive_path
    starter.low_sensitive_path = args.low_sensitive_path
    
    # API密钥配置
    starter.api_keys_file = args.api_keys
    starter.single_api_key = args.single_key
    
    # 超时配置
    starter.intercept_timeout = args.intercept_timeout
    
    # 启动服务
    success = starter.start()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
