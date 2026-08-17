#!/usr/bin/env python3
"""
配置验证脚本
检查API配置、拦截器设置、依赖项等
"""

import os
import sys
import json
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigValidator:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.success = []
    
    def check_environment_variables(self):
        """检查环境变量配置"""
        logger.info("🔍 检查环境变量配置...")
        
        # 关键配置项
        key_configs = {
            'VLLM_API_BASE': 'vLLM API地址',
            'HOST': '服务主机地址',
            'PORT': '服务端口',
            'ENABLE_FRONT_INTERCEPT': '前拦截开关',
            'ENABLE_POST_INTERCEPT': '后拦截开关',
            'USE_LOCAL_INTERCEPT': '本地拦截模式',
        }
        
        for env_var, description in key_configs.items():
            value = os.getenv(env_var)
            if value is not None:
                self.success.append(f"✅ {env_var} ({description}): {value}")
            else:
                self.warnings.append(f"⚠️  {env_var} ({description}): 未设置，将使用默认值")
    
    def check_intercept_configuration(self):
        """检查拦截器配置"""
        logger.info("🔍 检查拦截器配置...")
        
        enable_front = os.getenv('ENABLE_FRONT_INTERCEPT', 'false').lower() == 'true'
        enable_post = os.getenv('ENABLE_POST_INTERCEPT', 'false').lower() == 'true'
        use_local = os.getenv('USE_LOCAL_INTERCEPT', 'true').lower() == 'true'
        
        if enable_front or enable_post:
            self.success.append(f"✅ 拦截功能已启用: 前拦截={enable_front}, 后拦截={enable_post}")
            
            if use_local:
                self.success.append("✅ 使用本地集成模式")
                
                # 检查模型路径
                model_paths = {
                    'MODEL_FRONT_PATH': os.getenv('MODEL_FRONT_PATH', './safe_api/models/front_model'),
                    'MODEL_POST_PATH': os.getenv('MODEL_POST_PATH', './safe_api/models/post_model'),
                    'BLACKLIST_1W_PATH': os.getenv('BLACKLIST_1W_PATH', './safe_api/data/blacklist_1w.json'),
                    'HIGH_SENSITIVE_KEYWORDS_PATH': os.getenv('HIGH_SENSITIVE_KEYWORDS_PATH', './safe_api/data/high_sensitive_keywords.json'),
                }
                
                for path_name, path_value in model_paths.items():
                    if os.path.exists(path_value):
                        self.success.append(f"✅ {path_name}: {path_value} (存在)")
                    else:
                        self.warnings.append(f"⚠️  {path_name}: {path_value} (不存在)")
            else:
                self.success.append("✅ 使用远程API模式")
                
                # 检查远程API地址
                front_url = os.getenv('FRONT_INTERCEPT_URL', 'http://localhost:8001/intercept')
                post_url = os.getenv('POST_INTERCEPT_URL', 'http://localhost:8002/intercept')
                
                self.success.append(f"✅ 前拦截API地址: {front_url}")
                self.success.append(f"✅ 后拦截API地址: {post_url}")
        else:
            self.warnings.append("⚠️  拦截功能未启用")
    
    def check_dependencies(self):
        """检查Python依赖项"""
        logger.info("🔍 检查Python依赖项...")
        
        required_packages = [
            'fastapi',
            'uvicorn',
            'aiohttp',
            'pydantic',
            'pydantic_settings'
        ]
        
        optional_packages = [
            ('torch', '拦截功能需要'),
            ('transformers', '拦截功能需要'),
        ]
        
        # 检查必需依赖
        for package in required_packages:
            try:
                __import__(package)
                self.success.append(f"✅ {package}: 已安装")
            except ImportError:
                self.issues.append(f"❌ {package}: 未安装 (必需)")
        
        # 检查可选依赖
        for package, purpose in optional_packages:
            try:
                __import__(package)
                self.success.append(f"✅ {package}: 已安装 ({purpose})")
            except ImportError:
                self.warnings.append(f"⚠️  {package}: 未安装 ({purpose})")
    
    def check_api_keys(self):
        """检查API密钥配置"""
        logger.info("🔍 检查API密钥配置...")
        
        enable_multi_keys = os.getenv('ENABLE_MULTI_API_KEYS', 'true').lower() == 'true'
        api_keys_file = os.getenv('API_KEYS_FILE', 'api_keys.json')
        single_api_key = os.getenv('API_KEY')
        
        if enable_multi_keys:
            if os.path.exists(api_keys_file):
                try:
                    with open(api_keys_file, 'r', encoding='utf-8') as f:
                        keys_data = json.load(f)
                    
                    if isinstance(keys_data, list) and len(keys_data) > 0:
                        self.success.append(f"✅ 多API密钥配置: {len(keys_data)} 个密钥")
                    else:
                        self.warnings.append(f"⚠️  多API密钥文件为空或格式错误")
                except Exception as e:
                    self.issues.append(f"❌ 多API密钥文件读取失败: {e}")
            else:
                self.warnings.append(f"⚠️  多API密钥文件不存在: {api_keys_file}")
        
        if single_api_key:
            self.success.append(f"✅ 单API密钥已配置")
        else:
            self.warnings.append(f"⚠️  单API密钥未配置")
        
        if not enable_multi_keys and not single_api_key:
            self.warnings.append(f"⚠️  未配置任何API密钥，API将不进行认证")
    
    def check_logging_configuration(self):
        """检查日志配置"""
        logger.info("🔍 检查日志配置...")
        
        log_file = os.getenv('LOG_FILE', 'logs/api.log')
        user_log_file = os.getenv('USER_LOG_FILE', 'logs/user_requests.log')
        
        # 检查日志目录
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                self.success.append(f"✅ 创建日志目录: {log_dir}")
            except Exception as e:
                self.issues.append(f"❌ 无法创建日志目录 {log_dir}: {e}")
        
        self.success.append(f"✅ 主日志文件: {log_file}")
        self.success.append(f"✅ 用户请求日志: {user_log_file}")
    
    def check_file_structure(self):
        """检查文件结构"""
        logger.info("🔍 检查项目文件结构...")
        
        required_files = [
            'main.py',
            'config.py',
            'models.py',
            'vllm_client.py',
            'logger_config.py',
            'content_interceptor.py',
            'streaming_interceptor.py',
        ]
        
        for file_name in required_files:
            if os.path.exists(file_name):
                self.success.append(f"✅ {file_name}: 存在")
            else:
                self.issues.append(f"❌ {file_name}: 缺失")
        
        # 检查可选文件
        optional_files = [
            'requirements.txt',
            'README.md',
            '.env',
        ]
        
        for file_name in optional_files:
            if os.path.exists(file_name):
                self.success.append(f"✅ {file_name}: 存在")
            else:
                self.warnings.append(f"⚠️  {file_name}: 不存在")
    
    def run_validation(self):
        """运行所有验证检查"""
        logger.info("🚀 开始配置验证...")
        
        # 执行所有检查
        self.check_environment_variables()
        self.check_intercept_configuration()
        self.check_dependencies()
        self.check_api_keys()
        self.check_logging_configuration()
        self.check_file_structure()
        
        # 输出结果
        logger.info("\n📊 验证结果:")
        
        if self.success:
            logger.info("\n✅ 成功项目:")
            for item in self.success:
                logger.info(f"   {item}")
        
        if self.warnings:
            logger.info("\n⚠️  警告项目:")
            for item in self.warnings:
                logger.warning(f"   {item}")
        
        if self.issues:
            logger.info("\n❌ 问题项目:")
            for item in self.issues:
                logger.error(f"   {item}")
        
        # 总结
        total_checks = len(self.success) + len(self.warnings) + len(self.issues)
        logger.info(f"\n📈 总结:")
        logger.info(f"   成功: {len(self.success)}")
        logger.info(f"   警告: {len(self.warnings)}")
        logger.info(f"   错误: {len(self.issues)}")
        
        if self.issues:
            logger.error("💥 发现严重问题，请修复后再启动服务")
            return False
        elif self.warnings:
            logger.warning("⚠️  发现一些警告，建议检查配置")
            return True
        else:
            logger.info("🎉 配置验证通过！")
            return True

def main():
    """主函数"""
    validator = ConfigValidator()
    success = validator.run_validation()
    
    if not success:
        sys.exit(1)
    else:
        logger.info("✅ 可以启动服务")

if __name__ == "__main__":
    main()
