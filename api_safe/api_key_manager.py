#!/usr/bin/env python3
"""
API Key 管理器
支持从文件中读取多个API key并进行验证
"""

import os
import json
import hashlib
from typing import List, Set, Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class APIKeyManager:
    """API Key管理器"""
    
    def __init__(self, api_keys_file: str = "api_keys.json", cache_duration: int = 300):
        """
        初始化API Key管理器
        
        Args:
            api_keys_file: API key文件路径
            cache_duration: 缓存时间（秒）
        """
        self.api_keys_file = Path(api_keys_file)
        self.cache_duration = cache_duration
        self._api_keys: Set[str] = set()
        self._api_key_metadata: Dict[str, Dict] = {}
        self._last_load_time: Optional[datetime] = None
        self._load_api_keys()
    
    def _load_api_keys(self) -> None:
        """从文件加载API keys"""
        try:
            if not self.api_keys_file.exists():
                logger.warning(f"API keys file not found: {self.api_keys_file}")
                return
            
            # 检查缓存是否有效
            if (self._last_load_time and 
                datetime.now() - self._last_load_time < timedelta(seconds=self.cache_duration)):
                return
            
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 清空现有数据
            self._api_keys.clear()
            self._api_key_metadata.clear()
            
            # 处理API keys
            if isinstance(data, list):
                # 简单列表格式
                for key in data:
                    if isinstance(key, str) and key.strip():
                        self._api_keys.add(key.strip())
                        self._api_key_metadata[key.strip()] = {
                            "created_at": datetime.now().isoformat(),
                            "last_used": None,
                            "usage_count": 0
                        }
            elif isinstance(data, dict):
                # 详细格式
                for key, metadata in data.items():
                    if isinstance(key, str) and key.strip():
                        self._api_keys.add(key.strip())
                        self._api_key_metadata[key.strip()] = {
                            "created_at": metadata.get("created_at", datetime.now().isoformat()),
                            "last_used": metadata.get("last_used"),
                            "usage_count": metadata.get("usage_count", 0),
                            "description": metadata.get("description", ""),
                            "enabled": metadata.get("enabled", True)
                        }
            
            self._last_load_time = datetime.now()
            logger.info(f"Loaded {len(self._api_keys)} API keys from {self.api_keys_file}")
            
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
    
    def verify_api_key(self, api_key: str) -> bool:
        """
        验证API key
        
        Args:
            api_key: 要验证的API key
            
        Returns:
            bool: 是否有效
        """
        # 重新加载API keys（如果缓存过期）
        self._load_api_keys()
        
        if not api_key or not api_key.strip():
            return False
        
        api_key = api_key.strip()
        
        # 检查key是否存在且启用
        if api_key in self._api_keys:
            metadata = self._api_key_metadata.get(api_key, {})
            if metadata.get("enabled", True):
                # 更新使用统计
                self._update_key_usage(api_key)
                return True
        
        return False
    
    def _update_key_usage(self, api_key: str) -> None:
        """更新API key使用统计"""
        if api_key in self._api_key_metadata:
            self._api_key_metadata[api_key]["last_used"] = datetime.now().isoformat()
            self._api_key_metadata[api_key]["usage_count"] = self._api_key_metadata[api_key].get("usage_count", 0) + 1
    
    def get_key_info(self, api_key: str) -> Optional[Dict]:
        """
        获取API key信息
        
        Args:
            api_key: API key
            
        Returns:
            Dict: key信息，如果不存在返回None
        """
        self._load_api_keys()
        
        if api_key in self._api_key_metadata:
            return self._api_key_metadata[api_key].copy()
        return None
    
    def get_all_keys_info(self) -> Dict[str, Dict]:
        """
        获取所有API key信息
        
        Returns:
            Dict: 所有key的信息
        """
        self._load_api_keys()
        return self._api_key_metadata.copy()
    
    def add_api_key(self, api_key: str, description: str = "") -> bool:
        """
        添加新的API key
        
        Args:
            api_key: 新的API key
            description: key描述
            
        Returns:
            bool: 是否添加成功
        """
        if not api_key or not api_key.strip():
            return False
        
        api_key = api_key.strip()
        
        # 检查是否已存在
        if api_key in self._api_keys:
            return False
        
        # 添加到内存
        self._api_keys.add(api_key)
        self._api_key_metadata[api_key] = {
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "description": description,
            "enabled": True
        }
        
        # 保存到文件
        return self._save_api_keys()
    
    def remove_api_key(self, api_key: str) -> bool:
        """
        移除API key
        
        Args:
            api_key: 要移除的API key
            
        Returns:
            bool: 是否移除成功
        """
        if api_key in self._api_keys:
            self._api_keys.remove(api_key)
            if api_key in self._api_key_metadata:
                del self._api_key_metadata[api_key]
            return self._save_api_keys()
        return False
    
    def disable_api_key(self, api_key: str) -> bool:
        """
        禁用API key
        
        Args:
            api_key: 要禁用的API key
            
        Returns:
            bool: 是否禁用成功
        """
        if api_key in self._api_key_metadata:
            self._api_key_metadata[api_key]["enabled"] = False
            return self._save_api_keys()
        return False
    
    def enable_api_key(self, api_key: str) -> bool:
        """
        启用API key
        
        Args:
            api_key: 要启用的API key
            
        Returns:
            bool: 是否启用成功
        """
        if api_key in self._api_key_metadata:
            self._api_key_metadata[api_key]["enabled"] = True
            return self._save_api_keys()
        return False
    
    def _save_api_keys(self) -> bool:
        """保存API keys到文件"""
        try:
            # 确保目录存在
            self.api_keys_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(self._api_key_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self._api_keys)} API keys to {self.api_keys_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        获取API key统计信息
        
        Returns:
            Dict: 统计信息
        """
        self._load_api_keys()
        
        total_keys = len(self._api_keys)
        enabled_keys = sum(1 for metadata in self._api_key_metadata.values() if metadata.get("enabled", True))
        disabled_keys = total_keys - enabled_keys
        
        total_usage = sum(metadata.get("usage_count", 0) for metadata in self._api_key_metadata.values())
        
        # 最近使用的key
        recent_keys = []
        for key, metadata in self._api_key_metadata.items():
            if metadata.get("last_used"):
                recent_keys.append({
                    "key": key[:8] + "..." if len(key) > 8 else key,
                    "last_used": metadata["last_used"],
                    "usage_count": metadata.get("usage_count", 0)
                })
        
        recent_keys.sort(key=lambda x: x["last_used"], reverse=True)
        
        return {
            "total_keys": total_keys,
            "enabled_keys": enabled_keys,
            "disabled_keys": disabled_keys,
            "total_usage": total_usage,
            "recent_keys": recent_keys[:5]  # 最近5个使用的key
        }


# 全局API key管理器实例
api_key_manager = APIKeyManager()


def create_sample_api_keys_file():
    """创建示例API keys文件"""
    sample_keys = {
        "sk-sample-key-1": {
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "description": "示例API key 1",
            "enabled": True
        },
        "sk-sample-key-2": {
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "description": "示例API key 2",
            "enabled": True
        },
        "sk-sample-key-3": {
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "description": "示例API key 3",
            "enabled": True
        }
    }
    
    try:
        with open("api_keys.json", 'w', encoding='utf-8') as f:
            json.dump(sample_keys, f, indent=2, ensure_ascii=False)
        print("✅ 已创建示例API keys文件: api_keys.json")
        print("📝 请编辑此文件，添加你的实际API keys")
    except Exception as e:
        print(f"❌ 创建示例文件失败: {e}")


if __name__ == "__main__":
    # 如果文件不存在，创建示例文件
    if not Path("api_keys.json").exists():
        create_sample_api_keys_file()
    else:
        print("📁 API keys文件已存在")
    
    # 测试API key管理器
    manager = APIKeyManager()
    stats = manager.get_stats()
    print(f"\n📊 API Key统计:")
    print(f"   总key数: {stats['total_keys']}")
    print(f"   启用key数: {stats['enabled_keys']}")
    print(f"   禁用key数: {stats['disabled_keys']}")
    print(f"   总使用次数: {stats['total_usage']}") 