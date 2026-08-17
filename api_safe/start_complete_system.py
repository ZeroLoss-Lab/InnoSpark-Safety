#!/usr/bin/env python3
"""
完整系统启动脚本
启动顺序：
1. 前拦截BERT API服务 (端口8001)
2. 后拦截BERT API服务 (端口8002) 
3. 主API服务 (端口8003) - 使用远程拦截模式 + RAG功能
"""

import os
import sys
import time
import signal
import subprocess
import requests
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading


class CompleteSystemStarter:
    """完整系统启动器"""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
        # 服务配置
        self.front_intercept_port = "8001"
        self.post_intercept_port = "8002"
        self.main_api_port = "8003"
        self.vllm_api_base = "http://localhost:8000"
        self.rag_service_url = "http://localhost:8000/retrieve"
        self.api_key = "your_api_key_here"
        
        # 路径配置
        self.safe_api_dir = Path("safe_api")
        self.current_dir = Path(".")
        
    def print_colored(self, message, color_code="0"):
        """打印彩色文本"""
        print(f"\033[{color_code}m{message}\033[0m")
    
    def print_success(self, message):
        self.print_colored(f"✅ {message}", "32")  # 绿色
    
    def print_warning(self, message):
        self.print_colored(f"⚠️  {message}", "33")  # 黄色
    
    def print_error(self, message):
        self.print_colored(f"❌ {message}", "31")  # 红色
    
    def print_info(self, message):
        self.print_colored(f"ℹ️  {message}", "34")  # 蓝色
    
    def print_header(self):
        """打印标题"""
        self.print_colored("=" * 60, "36")
        self.print_colored("  增强版拦截器完整系统启动器", "36")
        self.print_colored("=" * 60, "36")
    
    def check_dependencies(self):
        """检查依赖"""
        self.print_info("检查依赖...")
        
        # 检查safe_api目录
        if not self.safe_api_dir.exists():
            self.print_error("safe_api目录不存在")
            return False
        
        # 检查必要文件
        required_files = [
            "safe_api/front_intercept_api.py",
            "safe_api/post_intercept_api.py", 
            "main.py",
            "enhanced_interceptor.py",
            "rag_client.py"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            self.print_error(f"缺少必要文件: {', '.join(missing_files)}")
            return False
        
        self.print_success("依赖检查通过")
        return True
    
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
        
        # API密钥文件
        api_keys = {
            self.api_key: {
                "description": "默认API密钥",
                "created_at": "2024-01-01T00:00:00",
                "enabled": True,
                "usage_count": 0,
                "last_used": None
            }
        }
        
        # 创建文件
        files_to_create = [
            (data_dir / "high_sensitive_keywords.json", high_sensitive_keywords),
            (data_dir / "high_sensitive_keywords-2.json", medium_sensitive_keywords),
            (data_dir / "blacklist_1w.json", blacklist_1w),
            (self.current_dir / "api_keys.json", api_keys)
        ]
        
        created_count = 0
        for file_path, data in files_to_create:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                created_count += 1
        
        if created_count > 0:
            self.print_success(f"创建了 {created_count} 个数据文件")
        else:
            self.print_info("数据文件已存在")
    
    def start_front_intercept_service(self):
        """启动前拦截服务"""
        self.print_info(f"启动前拦截BERT API服务 (端口 {self.front_intercept_port})...")
        
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "safe_api.front_intercept_api:app",
                "--host", "0.0.0.0",
                "--port", self.front_intercept_port,
                "--reload"
            ])
            
            self.processes.append(("前拦截API", process))
            
            # 等待服务启动
            self.wait_for_service(f"http://localhost:{self.front_intercept_port}/health", "前拦截API")
            self.print_success(f"前拦截API服务启动成功 (端口 {self.front_intercept_port})")
            return True
            
        except Exception as e:
            self.print_error(f"前拦截API服务启动失败: {e}")
            return False
    
    def start_post_intercept_service(self):
        """启动后拦截服务"""
        self.print_info(f"启动后拦截BERT API服务 (端口 {self.post_intercept_port})...")
        
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "safe_api.post_intercept_api:app",
                "--host", "0.0.0.0", 
                "--port", self.post_intercept_port,
                "--reload"
            ])
            
            self.processes.append(("后拦截API", process))
            
            # 等待服务启动
            self.wait_for_service(f"http://localhost:{self.post_intercept_port}/health", "后拦截API")
            self.print_success(f"后拦截API服务启动成功 (端口 {self.post_intercept_port})")
            return True
            
        except Exception as e:
            self.print_error(f"后拦截API服务启动失败: {e}")
            return False
    
    def start_main_api_service(self):
        """启动主API服务"""
        self.print_info(f"启动主API服务 (端口 {self.main_api_port})...")
        
        # 设置环境变量 - 使用远程拦截模式
        env_vars = {
            # 服务配置
            "VLLM_API_BASE": self.vllm_api_base,
            "HOST": "0.0.0.0",
            "PORT": self.main_api_port,
            "API_KEY": self.api_key,
            "ENABLE_MULTI_API_KEYS": "true",
            
            # 拦截器配置 - 使用远程模式
            "ENABLE_FRONT_INTERCEPT": "true",
            "ENABLE_POST_INTERCEPT": "true",
            "USE_LOCAL_INTERCEPT": "false",  # 使用远程拦截模式
            
            # 远程拦截API地址
            "FRONT_INTERCEPT_URL": f"http://localhost:{self.front_intercept_port}/intercept",
            "POST_INTERCEPT_URL": f"http://localhost:{self.post_intercept_port}/intercept",
            
            # RAG系统配置
            "ENABLE_RAG": "true",
            "RAG_SERVICE_URL": self.rag_service_url,
            "RAG_TOP_K": "5",
            "RAG_TIMEOUT": "10.0",
            
            # BERT双阈值配置（用于增强版拦截器，如果启用本地模式）
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
        
        # 应用环境变量
        env = os.environ.copy()
        env.update(env_vars)
        
        try:
            process = subprocess.Popen([
                sys.executable, "main.py"
            ], env=env)
            
            self.processes.append(("主API服务", process))
            
            # 等待服务启动
            self.wait_for_service(f"http://localhost:{self.main_api_port}/health", "主API服务")
            self.print_success(f"主API服务启动成功 (端口 {self.main_api_port})")
            return True
            
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
        
        self.print_warning(f"{service_name} 启动超时")
        return False
    
    def check_services_status(self):
        """检查服务状态"""
        self.print_info("检查相关服务状态...")
        
        services_to_check = [
            ("vLLM服务", self.vllm_api_base + "/v1/models"),
            ("RAG服务", self.rag_service_url)
        ]
        
        for service_name, url in services_to_check:
            try:
                if "retrieve" in url:
                    # RAG服务需要POST请求
                    response = requests.post(url, json={"query": "test", "top_k": 1}, timeout=5)
                else:
                    response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    self.print_success(f"{service_name} 运行正常")
                else:
                    self.print_warning(f"{service_name} 响应异常: {response.status_code}")
            except requests.RequestException:
                self.print_warning(f"{service_name} 不可访问 ({url})")
    
    def print_service_info(self):
        """打印服务信息"""
        print()
        self.print_colored("🎉 所有服务启动完成！", "32")
        print()
        self.print_colored("📋 服务信息:", "36")
        print(f"  前拦截API:  http://localhost:{self.front_intercept_port}")
        print(f"  后拦截API:  http://localhost:{self.post_intercept_port}")
        print(f"  主API服务:  http://localhost:{self.main_api_port}")
        print()
        self.print_colored("📖 API文档:", "36")
        print(f"  前拦截文档: http://localhost:{self.front_intercept_port}/docs")
        print(f"  后拦截文档: http://localhost:{self.post_intercept_port}/docs")
        print(f"  主API文档:  http://localhost:{self.main_api_port}/docs")
        print()
        self.print_colored("🔑 API密钥:", "36")
        print(f"  {self.api_key}")
        print()
        self.print_colored("💡 测试命令:", "36")
        print(f"  curl -X POST 'http://localhost:{self.main_api_port}/v1/chat/completions' \\")
        print(f"    -H 'Authorization: Bearer {self.api_key}' \\")
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
        
        for name, process in reversed(self.processes):  # 反向停止
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
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 创建演示数据
        self.create_demo_data()
        
        # 检查外部服务状态
        self.check_services_status()
        
        print()
        self.print_info("开始启动服务...")
        
        # 按顺序启动服务
        services = [
            ("前拦截BERT API", self.start_front_intercept_service),
            ("后拦截BERT API", self.start_post_intercept_service),
            ("主API服务", self.start_main_api_service)
        ]
        
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


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在关闭服务...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建启动器
    starter = CompleteSystemStarter()
    
    # 启动所有服务
    success = starter.start_all_services()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
