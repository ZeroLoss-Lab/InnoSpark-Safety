#!/usr/bin/env python3
"""
转发主API与拦截系统集成状态报告
生成详细的集成检查报告
"""

import os
import sys
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationReporter:
    def __init__(self):
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "status": "unknown",
                "total_checks": 0,
                "passed_checks": 0,
                "warnings": 0,
                "errors": 0
            },
            "sections": {}
        }
    
    def check_core_files(self):
        """检查核心文件"""
        section = {
            "name": "核心文件检查",
            "status": "pass",
            "items": []
        }
        
        core_files = {
            "main.py": "主API服务",
            "config.py": "配置管理",
            "models.py": "数据模型",
            "vllm_client.py": "vLLM客户端",
            "content_interceptor.py": "内容拦截器",
            "streaming_interceptor.py": "流式拦截器",
            "logger_config.py": "日志配置",
            "api_key_manager.py": "API密钥管理",
            "conversation_manager.py": "对话管理"
        }
        
        for file_name, description in core_files.items():
            if os.path.exists(file_name):
                section["items"].append({
                    "name": f"{file_name} ({description})",
                    "status": "pass",
                    "message": "文件存在"
                })
            else:
                section["items"].append({
                    "name": f"{file_name} ({description})",
                    "status": "error",
                    "message": "文件缺失"
                })
                section["status"] = "error"
        
        self.report["sections"]["core_files"] = section
    
    def check_intercept_files(self):
        """检查拦截相关文件"""
        section = {
            "name": "拦截系统文件",
            "status": "pass",
            "items": []
        }
        
        intercept_files = {
            "safe_api/front_intercept_api.py": "前拦截API",
            "safe_api/post_intercept_api.py": "后拦截API",
            "safe_api/data/blacklist_1w.json": "黑名单数据",
            "safe_api/data/high_sensitive_keywords.json": "高敏感词数据"
        }
        
        for file_path, description in intercept_files.items():
            if os.path.exists(file_path):
                section["items"].append({
                    "name": f"{description}",
                    "status": "pass",
                    "message": f"文件存在: {file_path}"
                })
            else:
                section["items"].append({
                    "name": f"{description}",
                    "status": "warning",
                    "message": f"文件缺失: {file_path}"
                })
                if section["status"] == "pass":
                    section["status"] = "warning"
        
        self.report["sections"]["intercept_files"] = section
    
    def check_configuration(self):
        """检查配置"""
        section = {
            "name": "配置检查",
            "status": "pass",
            "items": []
        }
        
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from config import settings
            
            # 基础配置
            section["items"].append({
                "name": "vLLM API Base",
                "status": "pass",
                "message": f"{settings.vllm_api_base}"
            })
            
            section["items"].append({
                "name": "服务地址",
                "status": "pass",
                "message": f"{settings.host}:{settings.port}"
            })
            
            # 拦截配置
            front_status = "启用" if settings.enable_front_intercept else "禁用"
            post_status = "启用" if settings.enable_post_intercept else "禁用"
            local_mode = "本地集成" if settings.use_local_intercept else "远程API"
            
            section["items"].append({
                "name": "前拦截",
                "status": "pass" if settings.enable_front_intercept else "warning",
                "message": front_status
            })
            
            section["items"].append({
                "name": "后拦截",
                "status": "pass" if settings.enable_post_intercept else "warning",
                "message": post_status
            })
            
            section["items"].append({
                "name": "拦截模式",
                "status": "pass",
                "message": local_mode
            })
            
            # 数据文件路径
            if os.path.exists(settings.blacklist_1w_path):
                section["items"].append({
                    "name": "黑名单数据",
                    "status": "pass",
                    "message": f"存在: {settings.blacklist_1w_path}"
                })
            else:
                section["items"].append({
                    "name": "黑名单数据",
                    "status": "warning",
                    "message": f"缺失: {settings.blacklist_1w_path}"
                })
            
            if os.path.exists(settings.high_sensitive_keywords_path):
                section["items"].append({
                    "name": "高敏感词数据",
                    "status": "pass", 
                    "message": f"存在: {settings.high_sensitive_keywords_path}"
                })
            else:
                section["items"].append({
                    "name": "高敏感词数据",
                    "status": "warning",
                    "message": f"缺失: {settings.high_sensitive_keywords_path}"
                })
            
        except Exception as e:
            section["items"].append({
                "name": "配置加载",
                "status": "error",
                "message": f"配置加载失败: {e}"
            })
            section["status"] = "error"
        
        self.report["sections"]["configuration"] = section
    
    def check_dependencies(self):
        """检查依赖"""
        section = {
            "name": "依赖检查",
            "status": "pass",
            "items": []
        }
        
        # 必需依赖
        required_deps = [
            "fastapi",
            "uvicorn", 
            "aiohttp",
            "pydantic",
            "pydantic_settings"
        ]
        
        # 拦截功能依赖
        intercept_deps = [
            "torch",
            "transformers"
        ]
        
        for dep in required_deps:
            try:
                __import__(dep)
                section["items"].append({
                    "name": f"{dep} (必需)",
                    "status": "pass",
                    "message": "已安装"
                })
            except ImportError:
                section["items"].append({
                    "name": f"{dep} (必需)",
                    "status": "error",
                    "message": "未安装"
                })
                section["status"] = "error"
        
        for dep in intercept_deps:
            try:
                __import__(dep)
                section["items"].append({
                    "name": f"{dep} (拦截功能)",
                    "status": "pass",
                    "message": "已安装"
                })
            except ImportError:
                section["items"].append({
                    "name": f"{dep} (拦截功能)",
                    "status": "warning",
                    "message": "未安装 - 拦截功能不可用"
                })
                if section["status"] == "pass":
                    section["status"] = "warning"
        
        self.report["sections"]["dependencies"] = section
    
    def check_api_integration(self):
        """检查API集成"""
        section = {
            "name": "API集成检查",
            "status": "pass",
            "items": []
        }
        
        try:
            # 检查主API中的拦截器导入
            with open("main.py", "r", encoding="utf-8") as f:
                main_content = f.read()
            
            # 检查关键集成点
            integration_points = [
                ("拦截器导入", "from content_interceptor import"),
                ("前拦截调用", "front_interceptor.intercept"),
                ("后拦截调用", "post_interceptor.intercept"),
                ("流式拦截", "streaming_interceptor.intercept_stream"),
                ("安全响应创建", "create_safety_response"),
                ("拦截器初始化", "await front_interceptor.initialize"),
            ]
            
            for name, pattern in integration_points:
                if pattern in main_content:
                    section["items"].append({
                        "name": name,
                        "status": "pass",
                        "message": "已集成"
                    })
                else:
                    section["items"].append({
                        "name": name,
                        "status": "warning",
                        "message": "未找到集成代码"
                    })
                    if section["status"] == "pass":
                        section["status"] = "warning"
            
            # 检查拦截响应简化
            if "intercept_result.reason" in main_content:
                section["items"].append({
                    "name": "详细日志记录",
                    "status": "pass",
                    "message": "支持详细拦截信息记录"
                })
            else:
                section["items"].append({
                    "name": "详细日志记录",
                    "status": "warning",
                    "message": "可能缺少详细拦截信息"
                })
            
        except Exception as e:
            section["items"].append({
                "name": "API集成检查",
                "status": "error",
                "message": f"检查失败: {e}"
            })
            section["status"] = "error"
        
        self.report["sections"]["api_integration"] = section
    
    def check_data_integrity(self):
        """检查数据完整性"""
        section = {
            "name": "数据完整性",
            "status": "pass",
            "items": []
        }
        
        # 检查黑名单数据
        blacklist_path = "./safe_api/data/blacklist_1w.json"
        if os.path.exists(blacklist_path):
            try:
                with open(blacklist_path, 'r', encoding='utf-8') as f:
                    blacklist_data = json.load(f)
                
                if isinstance(blacklist_data, list) and len(blacklist_data) > 0:
                    section["items"].append({
                        "name": "黑名单数据",
                        "status": "pass",
                        "message": f"有效数据，{len(blacklist_data)} 个类别"
                    })
                else:
                    section["items"].append({
                        "name": "黑名单数据",
                        "status": "warning",
                        "message": "数据为空或格式错误"
                    })
            except Exception as e:
                section["items"].append({
                    "name": "黑名单数据",
                    "status": "error",
                    "message": f"数据读取失败: {e}"
                })
                section["status"] = "error"
        
        # 检查高敏感词数据
        high_sensitive_path = "./safe_api/data/high_sensitive_keywords.json"
        if os.path.exists(high_sensitive_path):
            try:
                with open(high_sensitive_path, 'r', encoding='utf-8') as f:
                    keywords_data = json.load(f)
                
                if isinstance(keywords_data, list) and len(keywords_data) > 0:
                    section["items"].append({
                        "name": "高敏感词数据",
                        "status": "pass",
                        "message": f"有效数据，{len(keywords_data)} 个关键词"
                    })
                else:
                    section["items"].append({
                        "name": "高敏感词数据",
                        "status": "warning",
                        "message": "数据为空或格式错误"
                    })
            except Exception as e:
                section["items"].append({
                    "name": "高敏感词数据",
                    "status": "error",
                    "message": f"数据读取失败: {e}"
                })
                section["status"] = "error"
        
        self.report["sections"]["data_integrity"] = section
    
    def calculate_summary(self):
        """计算总结"""
        total_checks = 0
        passed_checks = 0
        warnings = 0
        errors = 0
        
        for section_name, section in self.report["sections"].items():
            for item in section["items"]:
                total_checks += 1
                if item["status"] == "pass":
                    passed_checks += 1
                elif item["status"] == "warning":
                    warnings += 1
                elif item["status"] == "error":
                    errors += 1
        
        # 确定整体状态
        if errors > 0:
            overall_status = "error"
        elif warnings > 0:
            overall_status = "warning"
        else:
            overall_status = "pass"
        
        self.report["summary"] = {
            "status": overall_status,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "warnings": warnings,
            "errors": errors
        }
    
    def generate_report(self):
        """生成完整报告"""
        logger.info("🚀 生成转发主API与拦截系统集成报告...")
        
        # 执行所有检查
        self.check_core_files()
        self.check_intercept_files()
        self.check_configuration()
        self.check_dependencies()
        self.check_api_integration()
        self.check_data_integrity()
        
        # 计算总结
        self.calculate_summary()
        
        return self.report
    
    def print_report(self, report):
        """打印报告"""
        print("="*80)
        print("🔍 转发主API与拦截系统集成报告")
        print("="*80)
        print(f"生成时间: {report['timestamp']}")
        print()
        
        # 总结
        summary = report['summary']
        status_emoji = {
            "pass": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        print(f"📊 总结: {status_emoji[summary['status']]} {summary['status'].upper()}")
        print(f"   总检查项: {summary['total_checks']}")
        print(f"   通过: {summary['passed_checks']}")
        print(f"   警告: {summary['warnings']}")
        print(f"   错误: {summary['errors']}")
        print()
        
        # 各部分详情
        for section_name, section in report['sections'].items():
            section_emoji = status_emoji[section['status']]
            print(f"{section_emoji} {section['name']}")
            
            for item in section['items']:
                item_emoji = status_emoji[item['status']]
                print(f"   {item_emoji} {item['name']}: {item['message']}")
            print()
        
        # 建议
        print("💡 建议:")
        if summary['errors'] > 0:
            print("   - 修复所有错误项后再启动服务")
        if summary['warnings'] > 0:
            print("   - 检查警告项，考虑是否需要处理")
        if summary['status'] == 'pass':
            print("   - 系统集成状态良好，可以正常使用")
        
        print("="*80)

def main():
    """主函数"""
    reporter = IntegrationReporter()
    report = reporter.generate_report()
    reporter.print_report(report)
    
    # 保存报告到文件
    report_file = f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 报告已保存到: {report_file}")
    
    # 根据状态返回退出码
    if report['summary']['status'] == 'error':
        return 1
    else:
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
