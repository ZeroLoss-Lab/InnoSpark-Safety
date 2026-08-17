# 🚀 API Key 管理系统快速启动指南

## 1. 快速配置

### 步骤1: 编辑API keys文件
编辑 `api_keys.json` 文件，添加你的实际API keys：

```json
{
  "sk-your-real-key-1": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "你的主要API key",
    "enabled": true
  },
  "sk-your-real-key-2": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "你的备用API key",
    "enabled": true
  }
}
```

### 步骤2: 配置环境变量
在 `.env` 文件中添加：

```bash
# 启用多API key支持
ENABLE_MULTI_API_KEYS=true
API_KEYS_FILE=api_keys.json

# 可选：保留单个API key（向后兼容）
# API_KEY=your-single-key
```

### 步骤3: 启动服务
```bash
python run.py
```

## 2. 快速测试

### 测试API key验证
```bash
# 使用第一个key
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Authorization: Bearer sk-your-real-key-1" \
  -H "Content-Type: application/json" \
  -d '{"model": "your-model", "messages": [{"role": "user", "content": "Hello"}]}'

# 使用第二个key
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Authorization: Bearer sk-your-real-key-2" \
  -H "Content-Type: application/json" \
  -d '{"model": "your-model", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 查看API key统计
```bash
curl -X GET "http://localhost:8001/v1/admin/api-keys/stats" \
  -H "Authorization: Bearer sk-your-real-key-1"
```

## 3. 常用操作

### 添加新的API key
```bash
curl -X POST "http://localhost:8001/v1/admin/api-keys" \
  -H "Authorization: Bearer sk-your-real-key-1" \
  -H "Content-Type: application/json" \
  -d '{"key": "sk-new-key", "description": "新添加的key"}'
```

### 禁用API key
```bash
curl -X PUT "http://localhost:8001/v1/admin/api-keys/sk-your-real-key-2/disable" \
  -H "Authorization: Bearer sk-your-real-key-1"
```

### 查看所有API keys
```bash
curl -X GET "http://localhost:8001/v1/admin/api-keys" \
  -H "Authorization: Bearer sk-your-real-key-1"
```

## 4. Python客户端示例

```python
import requests

# 使用任意一个有效的API key
api_keys = [
    "sk-your-real-key-1",
    "sk-your-real-key-2"
]

for api_key in api_keys:
    try:
        response = requests.post(
            "http://localhost:8001/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "your-model",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        
        if response.status_code == 200:
            print(f"✅ API key {api_key[:8]}... 工作正常")
            break
        else:
            print(f"❌ API key {api_key[:8]}... 验证失败")
            
    except Exception as e:
        print(f"❌ API key {api_key[:8]}... 请求失败: {e}")
```

## 5. 故障排除

### 问题1: API key验证失败
**解决方案:**
1. 检查 `api_keys.json` 文件格式是否正确
2. 确认API key在文件中且 `enabled: true`
3. 检查文件权限：`chmod 600 api_keys.json`

### 问题2: 服务启动失败
**解决方案:**
1. 检查 `.env` 文件配置
2. 确认 `api_keys.json` 文件存在
3. 查看日志：`tail -f logs/api.log`

### 问题3: 缓存问题
**解决方案:**
```python
# 强制重新加载API keys
from api_key_manager import api_key_manager
api_key_manager._last_load_time = None
api_key_manager._load_api_keys()
```

## 6. 安全建议

1. **设置文件权限**
   ```bash
   chmod 600 api_keys.json
   ```

2. **定期备份**
   ```bash
   cp api_keys.json api_keys.json.backup
   ```

3. **监控使用情况**
   ```bash
   # 每天检查一次
   curl -X GET "http://localhost:8001/v1/admin/api-keys/stats" \
     -H "Authorization: Bearer your-admin-key"
   ```

## 7. 高级配置

### 自定义缓存时间
```python
# 在 api_key_manager.py 中修改
api_key_manager = APIKeyManager(cache_duration=600)  # 10分钟缓存
```

### 自定义文件路径
```bash
# 在 .env 中设置
API_KEYS_FILE=/path/to/your/api_keys.json
```

## 8. 完整测试

运行完整测试脚本：
```bash
python test_api_keys.py
```

## 9. 下一步

- 📖 阅读完整文档：`API_KEY_MANAGEMENT.md`
- 🔧 配置权限控制
- 📊 设置使用限制
- 🔄 实现自动轮换

---

**🎉 恭喜！你现在有了一个功能完整的多API key管理系统！** 