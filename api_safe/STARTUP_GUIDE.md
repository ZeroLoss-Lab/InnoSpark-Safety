# 🚀 vLLM Proxy API 启动指南

## 概述

本指南详细介绍如何使用 `run.py` 启动 vLLM Proxy API 服务，包括所有可用的命令行参数和配置选项。

## 基本启动

### 最简单的启动方式
```bash
python run.py
```

这将使用默认配置启动服务：
- 端口：8001
- 地址：0.0.0.0
- vLLM API：http://localhost:8000
- 日志级别：INFO

## 命令行参数详解

### 🔧 服务配置参数

#### 端口和地址
```bash
# 指定端口
python run.py --port 8002

# 指定绑定地址
python run.py --host 127.0.0.1

# 组合使用
python run.py --host 127.0.0.1 --port 8002
```

#### vLLM API配置
```bash
# 指定vLLM API地址
python run.py --vllm-api http://192.168.1.100:8000

# 指定vLLM API密钥
python run.py --vllm-api-key "your-vllm-api-key"

# 组合使用
python run.py --vllm-api http://192.168.1.100:8000 --vllm-api-key "your-key"
```

### 🔐 API Key配置

#### 单个API Key（向后兼容）
```bash
# 使用单个API key
python run.py --api-key "sk-your-single-api-key"
```

#### 多API Key文件
```bash
# 使用默认API key文件
python run.py --enable-multi-api-keys

# 指定自定义API key文件
python run.py --api-keys-file /path/to/your/api_keys.json

# 禁用多API key支持
python run.py --disable-multi-api-keys

# 组合使用
python run.py --api-keys-file custom_keys.json --enable-multi-api-keys
```

### 📚 文档配置

#### 启用/禁用文档
```bash
# 启用API文档（默认）
python run.py --enable-docs

# 禁用API文档（生产环境推荐）
python run.py --disable-docs
```

#### 文档认证配置
```bash
# 文档需要API key认证（默认）
python run.py --docs-require-auth

# 文档无需认证（仅开发环境）
python run.py --docs-no-auth
```

### 📝 日志配置

#### 日志级别
```bash
# 设置日志级别
python run.py --log-level DEBUG    # 调试信息
python run.py --log-level INFO     # 一般信息（默认）
python run.py --log-level WARNING  # 警告信息
python run.py --log-level ERROR    # 错误信息
python run.py --log-level CRITICAL # 严重错误
```

#### 日志文件
```bash
# 指定API日志文件
python run.py --log-file logs/custom_api.log

# 指定用户请求日志文件
python run.py --user-log-file logs/custom_user.log

# 组合使用
python run.py --log-file logs/api.log --user-log-file logs/user.log
```

### 🔄 开发选项

#### 热重载
```bash
# 启用热重载（开发时使用）
python run.py --reload
```

## 常用启动场景

### 1. 开发环境
```bash
python run.py \
  --port 8001 \
  --log-level DEBUG \
  --docs-no-auth \
  --reload
```

### 2. 测试环境
```bash
python run.py \
  --port 8002 \
  --api-keys-file test_keys.json \
  --enable-multi-api-keys \
  --docs-require-auth \
  --log-level INFO
```

### 3. 生产环境
```bash
python run.py \
  --port 8001 \
  --disable-docs \
  --api-keys-file prod_keys.json \
  --enable-multi-api-keys \
  --log-level WARNING \
  --log-file logs/prod_api.log
```

### 4. 多实例部署
```bash
# 实例1
python run.py --port 8001 --api-keys-file instance1_keys.json

# 实例2
python run.py --port 8002 --api-keys-file instance2_keys.json

# 实例3
python run.py --port 8003 --api-keys-file instance3_keys.json
```

### 5. 自定义vLLM服务
```bash
python run.py \
  --vllm-api http://192.168.1.100:8000 \
  --vllm-api-key "your-vllm-key" \
  --port 8001 \
  --api-keys-file custom_keys.json
```

## 环境变量配置

除了命令行参数，你也可以使用环境变量配置：

### 创建 `.env` 文件
```bash
# vLLM配置
VLLM_API_BASE=http://localhost:8000
VLLM_API_KEY=your-vllm-key

# 服务配置
HOST=0.0.0.0
PORT=8001

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/api.log
USER_LOG_FILE=logs/user_requests.log

# API Key配置
API_KEY=your-single-key
API_KEYS_FILE=api_keys.json
ENABLE_MULTI_API_KEYS=true

# 文档配置
ENABLE_DOCS=true
DOCS_REQUIRE_AUTH=true
```

### 使用环境变量启动
```bash
# 加载.env文件后启动
source .env && python run.py

# 或者直接设置环境变量
export VLLM_API_BASE=http://localhost:8000
export PORT=8002
python run.py
```

## API Key文件格式

### 简单列表格式
```json
[
  "sk-your-api-key-1",
  "sk-your-api-key-2",
  "sk-your-api-key-3"
]
```

### 详细格式（推荐）
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

## 启动示例

### 示例1：基本多API key启动
```bash
python run.py \
  --port 8001 \
  --api-keys-file api_keys.json \
  --enable-multi-api-keys \
  --log-level INFO
```

### 示例2：生产环境配置
```bash
python run.py \
  --port 8001 \
  --disable-docs \
  --api-keys-file production_keys.json \
  --enable-multi-api-keys \
  --log-level WARNING \
  --log-file logs/production.log
```

### 示例3：开发环境配置
```bash
python run.py \
  --port 8001 \
  --docs-no-auth \
  --api-keys-file dev_keys.json \
  --enable-multi-api-keys \
  --log-level DEBUG \
  --reload
```

### 示例4：自定义vLLM服务
```bash
python run.py \
  --vllm-api http://192.168.1.100:8000 \
  --vllm-api-key "your-vllm-key" \
  --port 8001 \
  --api-keys-file custom_keys.json \
  --enable-multi-api-keys \
  --docs-require-auth
```

## 启动后验证

### 1. 健康检查
```bash
curl http://localhost:8001/health
```

### 2. API文档访问
```bash
# 如果启用了文档
curl http://localhost:8001/docs

# 如果需要认证
curl -H "Authorization: Bearer your-api-key" http://localhost:8001/docs
```

### 3. API调用测试
```bash
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Authorization: Bearer sk-your-api-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 4. API Key管理
```bash
# 查看所有API keys
curl -H "Authorization: Bearer sk-your-api-key-1" \
  http://localhost:8001/v1/admin/api-keys

# 查看统计信息
curl -H "Authorization: Bearer sk-your-api-key-1" \
  http://localhost:8001/v1/admin/api-keys/stats
```

## 故障排除

### 1. 端口被占用
```bash
# 查看端口占用
lsof -i :8001

# 使用其他端口
python run.py --port 8002
```

### 2. API key文件不存在
```bash
# 创建示例API key文件
python api_key_manager.py

# 或手动创建
echo '{"sk-test-key": {"created_at": "2024-01-01T00:00:00", "last_used": null, "usage_count": 0, "description": "测试key", "enabled": true}}' > api_keys.json
```

### 3. vLLM服务不可用
```bash
# 检查vLLM服务状态
curl http://localhost:8000/v1/models

# 使用不同的vLLM地址
python run.py --vllm-api http://other-server:8000
```

### 4. 权限问题
```bash
# 设置API key文件权限
chmod 600 api_keys.json

# 设置日志目录权限
chmod 755 logs/
```

## 完整参数列表

```bash
python run.py --help
```

输出将显示所有可用的命令行参数和示例用法。

## 总结

通过这个启动指南，你可以：

1. ✅ 使用命令行参数灵活配置服务
2. ✅ 支持单个或多个API key
3. ✅ 配置文档访问权限
4. ✅ 自定义日志和端口
5. ✅ 适应不同环境需求

选择适合你需求的启动方式，开始使用 vLLM Proxy API！ 