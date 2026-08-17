# 增强版API服务启动脚本使用说明

## 🚀 快速开始

### 默认启动（推荐）
```bash
python start_enhanced_api.py
```
- ✅ 启动前拦截BERT API (8001端口)
- ✅ 启动后拦截BERT API (8002端口)
- ✅ 启动主API服务 (8003端口)
- ✅ 启用RAG功能
- ❌ 禁用API文档访问
- 🔑 支持多API密钥

## 🎛️ 功能控制

### 控制拦截功能
```bash
# 禁用前拦截
python start_enhanced_api.py --no-front

# 禁用后拦截  
python start_enhanced_api.py --no-post

# 禁用所有拦截
python start_enhanced_api.py --no-front --no-post
```

### 控制RAG功能
```bash
# 禁用RAG
python start_enhanced_api.py --no-rag

# 自定义RAG服务地址
python start_enhanced_api.py --rag http://localhost:9000/retrieve
```

### 控制API文档
```bash
# 启用API文档（默认禁用）
python start_enhanced_api.py --enable-docs
```

## 🔑 API密钥管理

### 使用多API密钥文件
```bash
# 使用默认密钥文件 (api_keys.json)
python start_enhanced_api.py

# 使用自定义密钥文件
python start_enhanced_api.py --api-keys my_keys.json
```

### API密钥文件格式
```json
{
  "sk-your-api-key-1": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": "2025-07-21T11:00:49.733149",
    "usage_count": 2,
    "description": "主要API key",
    "enabled": true
  },
  "sk-your-api-key-2": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": "2025-07-21T11:00:49.733158",
    "usage_count": 2,
    "description": "备用API key",
    "enabled": true
  },
  "sk-your-api-key-3": {
    "created_at": "2024-01-01T00:00:00",
    "last_used": null,
    "usage_count": 0,
    "description": "测试API key",
    "enabled": false
  }
}
```

### 使用单个API密钥（向后兼容）
```bash
python start_enhanced_api.py --single-key sk-your-secret-key
```

## 🔧 高级配置

### 自定义端口
```bash
# 自定义主API端口
python start_enhanced_api.py --port 9000

# 自定义拦截服务端口
python start_enhanced_api.py --front-port 9001 --post-port 9002
```

### 自定义服务地址
```bash
# 自定义vLLM服务地址
python start_enhanced_api.py --vllm http://192.168.1.100:8000

# 自定义绑定地址
python start_enhanced_api.py --host 127.0.0.1
```

## 📋 完整参数列表

```bash
python start_enhanced_api.py [选项]

服务配置:
  --host HOST                 服务绑定地址 (默认: 0.0.0.0)
  --port PORT                 主API服务端口 (默认: 8003)
  --vllm URL                  vLLM服务地址 (默认: http://localhost:8000)
  --rag URL                   RAG服务地址 (默认: http://localhost:8000/retrieve)

功能开关:
  --no-front                  禁用前拦截功能
  --no-post                   禁用后拦截功能
  --no-rag                    禁用RAG功能
  --enable-docs               启用API文档访问（默认禁用）

API密钥配置:
  --api-keys FILE             API密钥JSON文件路径 (默认: api_keys.json)
  --single-key KEY            使用单个API密钥（向后兼容）

端口配置:
  --front-port PORT           前拦截服务端口 (默认: 8001)
  --post-port PORT            后拦截服务端口 (默认: 8002)
```

## 🎯 使用场景示例

### 场景1：开发测试环境
```bash
# 启用所有功能，包括文档
python start_enhanced_api.py --enable-docs --single-key dev-test-key
```

### 场景2：生产环境
```bash
# 禁用文档，使用多密钥，自定义端口
python start_enhanced_api.py --port 80 --api-keys production_keys.json
```

### 场景3：仅语言模型服务
```bash
# 禁用所有拦截和RAG功能
python start_enhanced_api.py --no-front --no-post --no-rag
```

### 场景4：仅前拦截
```bash
# 只启用前拦截，禁用后拦截和RAG
python start_enhanced_api.py --no-post --no-rag
```

### 场景5：RAG增强模式
```bash
# 启用RAG但禁用拦截
python start_enhanced_api.py --no-front --no-post
```

## 🔍 服务验证

### 检查服务状态
```bash
# 检查主API服务
curl http://localhost:8003/health

# 检查前拦截服务（如果启用）
curl http://localhost:8001/health

# 检查后拦截服务（如果启用）  
curl http://localhost:8002/health
```

### 测试API调用
```bash
curl -X POST 'http://localhost:8003/v1/chat/completions' \
  -H 'Authorization: Bearer sk-your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen7b-in",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

### 测试拦截功能
```bash
# 测试前拦截（应该被拦截）
curl -X POST 'http://localhost:8003/v1/chat/completions' \
  -H 'Authorization: Bearer sk-your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen7b-in",
    "messages": [
      {"role": "user", "content": "placeholder_request_alpha"}
    ]
  }'
```

### 测试RAG功能
```bash
# 测试RAG增强回答
curl -X POST 'http://localhost:8003/v1/chat/completions' \
  -H 'Authorization: Bearer sk-your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen7b-in",
    "messages": [
      {"role": "user", "content": "中国有哪些重要的法律法规"}
    ]
  }'
```

## 📊 服务架构

```
用户请求 → 主API服务(8003)
              ↓
        [前拦截API(8001)] → vLLM(8000) → [后拦截API(8002)]
              ↓                              ↓
        [RAG服务(8000/retrieve)]      返回结果给用户
```

## 🔐 安全特性

1. **多API密钥支持**: 支持多个用户使用不同的API密钥
2. **密钥状态管理**: 可以启用/禁用特定密钥
3. **使用统计**: 记录每个密钥的使用次数和最后使用时间
4. **文档访问控制**: 默认禁用API文档，需要显式启用
5. **认证保护**: 即使启用文档也需要API密钥认证

## 🚨 注意事项

1. **端口冲突**: 确保配置的端口没有被其他服务占用
2. **依赖服务**: 确保vLLM服务和RAG服务（如果启用）正常运行
3. **模型文件**: 确保BERT模型文件存在于safe_api目录下
4. **权限管理**: 妥善保管API密钥文件
5. **日志监控**: 定期检查logs目录下的日志文件

## 🛠️ 故障排除

### 服务启动失败
1. 检查端口是否被占用：`netstat -an | grep 8003`
2. 检查依赖是否安装：`pip install -r requirements.txt`
3. 查看启动日志：观察控制台输出

### API密钥问题
1. 检查密钥文件格式是否正确
2. 确认密钥的enabled字段为true
3. 验证请求头中的Authorization格式

### 拦截功能异常
1. 确认safe_api目录下的模型文件存在
2. 检查前后拦截服务是否正常启动
3. 验证数据文件（关键词库）是否存在

### RAG功能异常
1. 检查RAG服务是否可访问
2. 验证RAG_SERVICE_URL配置是否正确
3. 测试RAG服务的独立调用

---

如有其他问题，请查看日志文件或联系技术支持。
