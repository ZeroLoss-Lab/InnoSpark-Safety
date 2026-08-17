# API Key 管理系统

## 概述

这个API key管理系统允许你维护多个API key，所有在指定文件中的API key都可以访问你的API服务。

## 功能特性

- ✅ **多API key支持**: 支持在文件中维护多个API key
- ✅ **向后兼容**: 仍然支持单个API key配置
- ✅ **实时验证**: 支持实时验证API key
- ✅ **使用统计**: 记录每个key的使用次数和最后使用时间
- ✅ **启用/禁用**: 可以临时禁用某个key而不删除
- ✅ **管理API**: 提供REST API来管理API keys
- ✅ **缓存机制**: 支持缓存以提高性能

## 配置

### 环境变量

在 `.env` 文件中添加以下配置：

```bash
# 单个API key（向后兼容）
API_KEY=your-single-api-key

# 多API key配置
ENABLE_MULTI_API_KEYS=true
API_KEYS_FILE=api_keys.json
```

### API Keys文件格式

支持两种格式：

#### 1. 简单列表格式
```json
[
  "sk-your-api-key-1",
  "sk-your-api-key-2",
  "sk-your-api-key-3"
]
```

#### 2. 详细格式（推荐）
```json
{
  "sk-your-api-key-1": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "主要API key",
    "enabled": true
  },
  "sk-your-api-key-2": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "备用API key",
    "enabled": true
  }
}
```

## 使用方法

### 1. 客户端调用

使用任何在 `api_keys.json` 文件中的API key：

```bash
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Authorization: Bearer sk-your-api-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 2. Python客户端示例

```python
import requests

api_key = "sk-your-api-key-1"  # 使用文件中的任意key
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8001/v1/chat/completions",
    headers=headers,
    json={
        "model": "your-model",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)

print(response.json())
```

## 管理API

### 1. 查看所有API keys

```bash
curl -X GET "http://localhost:8001/v1/admin/api-keys" \
  -H "Authorization: Bearer sk-your-api-key-1"
```

### 2. 查看API key统计

```bash
curl -X GET "http://localhost:8001/v1/admin/api-keys/stats" \
  -H "Authorization: Bearer sk-your-api-key-1"
```

### 3. 添加新的API key

```bash
curl -X POST "http://localhost:8001/v1/admin/api-keys" \
  -H "Authorization: Bearer sk-your-api-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-new-api-key",
    "description": "新添加的API key"
  }'
```

### 4. 禁用API key

```bash
curl -X PUT "http://localhost:8001/v1/admin/api-keys/sk-your-api-key-2/disable" \
  -H "Authorization: Bearer sk-your-api-key-1"
```

### 5. 启用API key

```bash
curl -X PUT "http://localhost:8001/v1/admin/api-keys/sk-your-api-key-2/enable" \
  -H "Authorization: Bearer sk-your-api-key-1"
```

### 6. 删除API key

```bash
curl -X DELETE "http://localhost:8001/v1/admin/api-keys/sk-your-api-key-3" \
  -H "Authorization: Bearer sk-your-api-key-1"
```

## 管理工具

### 命令行工具

运行以下命令来管理API keys：

```bash
# 创建示例API keys文件
python api_key_manager.py

# 查看统计信息
python -c "
from api_key_manager import api_key_manager
stats = api_key_manager.get_stats()
print(f'总key数: {stats[\"total_keys\"]}')
print(f'启用key数: {stats[\"enabled_keys\"]}')
print(f'总使用次数: {stats[\"total_usage\"]}')
"
```

### 直接编辑文件

你也可以直接编辑 `api_keys.json` 文件：

```bash
# 添加新的API key
echo '{
  "sk-new-key": {
    "created_at": "'$(date -u +%Y-%m-%dT%H:%M:%S)'",
    "last_used": null,
    "usage_count": 0,
    "description": "手动添加的key",
    "enabled": true
  }
}' >> api_keys.json
```

## 安全建议

1. **文件权限**: 确保 `api_keys.json` 文件只有必要的用户可读
   ```bash
   chmod 600 api_keys.json
   ```

2. **定期轮换**: 定期更换API keys
   ```bash
   # 禁用旧key
   curl -X PUT "http://localhost:8001/v1/admin/api-keys/old-key/disable" \
     -H "Authorization: Bearer admin-key"
   
   # 添加新key
   curl -X POST "http://localhost:8001/v1/admin/api-keys" \
     -H "Authorization: Bearer admin-key" \
     -d '{"key": "new-key", "description": "轮换后的key"}'
   ```

3. **监控使用**: 定期检查API key使用统计
   ```bash
   curl -X GET "http://localhost:8001/v1/admin/api-keys/stats" \
     -H "Authorization: Bearer admin-key"
   ```

4. **备份**: 定期备份API keys文件
   ```bash
   cp api_keys.json api_keys.json.backup
   ```

## 故障排除

### 1. API key验证失败

检查以下几点：
- API key是否在 `api_keys.json` 文件中
- API key是否被禁用（`enabled: false`）
- 文件格式是否正确（JSON格式）
- 文件权限是否正确

### 2. 文件加载失败

```bash
# 检查文件是否存在
ls -la api_keys.json

# 检查JSON格式
python -m json.tool api_keys.json

# 查看日志
tail -f logs/api.log
```

### 3. 缓存问题

如果修改了API keys文件但验证仍然使用旧数据，可能是缓存问题：

```python
# 强制重新加载
from api_key_manager import api_key_manager
api_key_manager._last_load_time = None
api_key_manager._load_api_keys()
```

## 性能优化

1. **缓存时间**: 默认缓存5分钟，可以通过修改 `cache_duration` 参数调整
2. **文件监控**: 可以添加文件监控来自动重新加载
3. **数据库存储**: 对于大量API keys，可以考虑使用数据库存储

## 扩展功能

### 1. 添加权限控制

可以为不同的API key设置不同的权限：

```json
{
  "sk-admin-key": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "管理员key",
    "enabled": true,
    "permissions": ["read", "write", "admin"]
  },
  "sk-user-key": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "普通用户key",
    "enabled": true,
    "permissions": ["read", "write"]
  }
}
```

### 2. 添加过期时间

```json
{
  "sk-temp-key": {
    "created_at": "2024-01-01T00:00:00",
    "expires_at": "2024-12-31T23:59:59",
    "last_used": null,
    "usage_count": 0,
    "description": "临时key",
    "enabled": true
  }
}
```

### 3. 添加使用限制

```json
{
  "sk-limited-key": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "限制使用次数的key",
    "enabled": true,
    "max_usage": 1000,
    "daily_limit": 100
  }
}
```

## 总结

这个API key管理系统提供了灵活、安全、易用的多API key支持，既保持了向后兼容性，又提供了强大的管理功能。你可以根据实际需求进行配置和扩展。 