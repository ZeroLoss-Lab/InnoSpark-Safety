#!/usr/bin/env python3
"""
启动脚本 - 同时启动前拦截和后拦截API服务
"""

import subprocess
import sys
import time
import signal
import os
from concurrent.futures import ThreadPoolExecutor
import threading

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_front_intercept(self):
        """启动前拦截API服务"""
        try:
            print("🚀 启动前拦截API服务 (端口 8001)...")
            
            # 传递环境变量
            env = os.environ.copy()
            
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "front_intercept_api:app", 
                "--host", "0.0.0.0", 
                "--port", "8001",
                "--reload"
            ], env=env)
            self.processes.append(("front_intercept", process))
            print("✅ 前拦截API服务启动成功")
            return process
        except Exception as e:
            print(f"❌ 前拦截API服务启动失败: {e}")
            return None
    
    def start_post_intercept(self):
        """启动后拦截API服务"""
        try:
            print("🚀 启动后拦截API服务 (端口 8002)...")
            
            # 传递环境变量
            env = os.environ.copy()
            
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "post_intercept_api:app", 
                "--host", "0.0.0.0", 
                "--port", "8002",
                "--reload"
            ], env=env)
            self.processes.append(("post_intercept", process))
            print("✅ 后拦截API服务启动成功")
            return process
        except Exception as e:
            print(f"❌ 后拦截API服务启动失败: {e}")
            return None
    
    def monitor_process(self, name, process):
        """监控进程状态"""
        while self.running:
            if process.poll() is not None:
                print(f"⚠️  {name} 服务意外退出，退出码: {process.returncode}")
                break
            time.sleep(1)
    
    def start_all_services(self):
        """启动所有服务"""
        print("🔄 启动安全拦截API系统...")
        print("=" * 50)
        
        # 启动服务
        front_process = self.start_front_intercept()
        time.sleep(2)  # 等待一下再启动下一个
        post_process = self.start_post_intercept()
        
        if not front_process and not post_process:
            print("❌ 所有服务启动失败")
            return False
        
        print("\n" + "=" * 50)
        print("✅ 服务启动完成!")
        print("\n📋 服务信息:")
        print("  前拦截API: http://localhost:8001")
        print("  后拦截API: http://localhost:8002")
        print("\n📖 API文档:")
        print("  前拦截API文档: http://localhost:8001/docs")
        print("  后拦截API文档: http://localhost:8002/docs")
        print("\n💡 测试命令:")
        print("  python start_with_thresholds.py")
        print("\n⚠️  按 Ctrl+C 停止所有服务")
        print("=" * 50)
        
        # 启动监控线程
        with ThreadPoolExecutor(max_workers=2) as executor:
            if front_process:
                executor.submit(self.monitor_process, "前拦截API", front_process)
            if post_process:
                executor.submit(self.monitor_process, "后拦截API", post_process)
            
            try:
                # 主线程等待
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 收到停止信号，正在关闭服务...")
                self.stop_all_services()
        
        return True
    
    def stop_all_services(self):
        """停止所有服务"""
        self.running = False
        
        for name, process in self.processes:
            try:
                print(f"🛑 停止 {name} 服务...")
                process.terminate()
                
                # 等待进程优雅退出
                try:
                    process.wait(timeout=5)
                    print(f"✅ {name} 服务已停止")
                except subprocess.TimeoutExpired:
                    print(f"⚠️  {name} 服务未响应，强制终止...")
                    process.kill()
                    process.wait()
                    print(f"✅ {name} 服务已强制停止")
                    
            except Exception as e:
                print(f"❌ 停止 {name} 服务时出错: {e}")
        
        print("🏁 所有服务已停止")

def check_requirements():
    """检查依赖是否安装"""
    required_packages = [
        'fastapi', 'uvicorn', 'transformers', 'torch', 'aiohttp'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少必要的Python包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 请运行以下命令安装依赖:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_files():
    """检查必要文件是否存在"""
    required_files = [
        'front_intercept_api.py',
        'post_intercept_api.py',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必要的文件:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def main():
    """主函数"""
    print("🔍 安全拦截API系统启动器")
    print("=" * 50)
    
    # 检查依赖
    if not check_requirements():
        sys.exit(1)
    
    # 检查文件
    if not check_files():
        sys.exit(1)
    
    print("✅ 环境检查通过\n")
    
    # 启动服务管理器
    manager = ServiceManager()
    
    # 设置信号处理
    def signal_handler(signum, frame):
        print(f"\n收到信号 {signum}，正在关闭服务...")
        manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动所有服务
    success = manager.start_all_services()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
