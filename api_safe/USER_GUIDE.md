# vLLM Proxy API 使用说明文档

## 📖 项目简介

这是一个基于FastAPI的vLLM代理API服务，提供OpenAI兼容的接口，并集成了智能内容拦截功能。支持多轮对话管理、API密钥管理和内容安全过滤。

### 🌟 主要特性

- ✅ **OpenAI兼容接口** - 完全兼容OpenAI API格式
- ✅ **多轮对话支持** - 基于Session的上下文管理
- ✅ **API密钥管理** - 支持单个和多个API密钥
- ✅ **内容安全拦截** - 前拦截和后拦截双重保护
- ✅ **高性能设计** - 支持高并发和流式响应
- ✅ **灵活配置** - 命令行参数和环境变量双重配置
- ✅ **完整日志** - 详细的请求和安全日志记录

## 🚀 快速开始

### 第一步：环境准备

1. **确保Python环境**
   ```bash
   python --version  # 需要 Python 3.8+
   ```

2. **安装基础依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **检查文件结构**
   ```bash
   ls -la  # 确认存在 main.py, run.py, api_keys.json 等文件
   ```

### 第二步：基础启动

#### 方式1：使用run.py（推荐）

```bash
# 开发环境 - 最简单的启动方式
python run.py \
  --vllm-api http://localhost:8000 \
  --docs-no-auth \
  --port 8003

# 生产环境 - 带安全配置
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "your-secret-key" \
  --disable-docs \
  --port 8003
```

#### 方式2：使用main.py

```bash
# 基础启动
python main.py --port 8003

# 查看所有参数
python main.py --help
```

### 第三步：验证服务

```bash
# 健康检查
curl http://localhost:8003/health

# 查看API文档（如果启用）
# 浏览器访问：http://localhost:8003/docs
```

## 🛡️ 内容拦截功能

### 拦截服务部署

1. **启动拦截服务**
   ```bash
   cd safe_api
   
   # 方式1：使用启动脚本
   python start_services.py
   
   # 方式2：分别启动
   python front_intercept_api.py &  # 前拦截 - 端口8001
   python post_intercept_api.py &   # 后拦截 - 端口8002
   ```

2. **验证拦截服务**
   ```bash
   curl http://localhost:8001/health  # 前拦截健康检查
   curl http://localhost:8002/health  # 后拦截健康检查
   ```

### 启动带拦截的主API

```bash
# 完整拦截配置
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003


python run.py \
  --vllm-api https://nat-notebook-inspire.sii.edu.cn/ws-6040202d-b785-4b37-98b0-c68d65dd52ce/project-b795c114-135a-40db-b3d0-19b60f25237b/user-8c70c2fa-5dd5-4f01-b07a-c8e75a057933/vscode/20027406-b151-428c-9cbe-203c50b32144/3222a1ff-e43c-424f-a65f-a97b07232df7/proxy/8001 \
  --enable-front-intercept \
  --enable-post-intercept \
  --front-intercept-url https://nat-notebook-inspire.sii.edu.cn/ws-6040202d-b785-4b37-98b0-c68d65dd52ce/project-b795c114-135a-40db-b3d0-19b60f25237b/user-8c70c2fa-5dd5-4f01-b07a-c8e75a057933/vscode/20027406-b151-428c-9cbe-203c50b32144/3222a1ff-e43c-424f-a65f-a97b07232df7/proxy/8002/intercept \
  --post-intercept-url https://nat-notebook-inspire.sii.edu.cn/ws-6040202d-b785-4b37-98b0-c68d65dd52ce/project-b795c114-135a-40db-b3d0-19b60f25237b/user-8c70c2fa-5dd5-4f01-b07a-c8e75a057933/vscode/20027406-b151-428c-9cbe-203c50b32144/3222a1ff-e43c-424f-a65f-a97b07232df7/proxy/8003/intercept \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 9001

# 仅前拦截（检查用户输入）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --api-key "your-api-key" \
  --disable-docs \
  --port 8003

# 仅后拦截（检查模型输出）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-post-intercept \
  --api-key "your-api-key" \
  --disable-docs \
  --port 8003
```

## 🔑 API使用方法

### 基础聊天接口

```bash
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下Python"}
    ]
  }'
```

### 多轮对话

```bash
# 第一轮对话
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "请解释什么是机器学习"}
    ],
    "session_id": "session-123",
    "enable_context": true,
    "max_context_turns": 5
  }'

# 第二轮对话（会自动包含上下文）
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "能举个具体例子吗？"}
    ],
    "session_id": "session-123",
    "enable_context": true
  }'
```

### 流式响应

```bash
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "请写一首关于春天的诗"}
    ],
    "stream": true
  }'
```

## ⚙️ 配置参数详解

### 服务配置

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--vllm-api` | vLLM服务地址 | http://localhost:8000 | `--vllm-api http://192.168.1.100:8000` |
| `--host` | 服务绑定地址 | 0.0.0.0 | `--host 127.0.0.1` |
| `--port` | 服务端口 | 8001 | `--port 8003` |
| `--workers` | 工作进程数 | 1 | `--workers 4` |

### 安全配置

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--api-key` | 单个API密钥 | 无 | `--api-key "sk-123456"` |
| `--enable-multi-api-keys` | 启用多密钥支持 | true | `--enable-multi-api-keys` |
| `--api-keys-file` | 密钥文件路径 | api_keys.json | `--api-keys-file keys.json` |
| `--disable-docs` | 禁用API文档 | false | `--disable-docs` |
| `--docs-require-auth` | 文档需要认证 | true | `--docs-require-auth` |

### 拦截配置

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--enable-front-intercept` | 启用前拦截 | false | `--enable-front-intercept` |
| `--enable-post-intercept` | 启用后拦截 | false | `--enable-post-intercept` |
| `--front-intercept-url` | 前拦截服务地址 | http://localhost:8001/intercept | `--front-intercept-url http://192.168.1.10:8001/intercept` |
| `--post-intercept-url` | 后拦截服务地址 | http://localhost:8002/intercept | `--post-intercept-url http://192.168.1.10:8002/intercept` |

### 性能配置

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--max-connections` | 最大连接数 | 200 | `--max-connections 500` |
| `--max-keepalive-connections` | 保持活跃连接数 | 100 | `--max-keepalive-connections 200` |
| `--intercept-timeout` | 拦截超时时间 | 5.0 | `--intercept-timeout 10.0` |

## 🏗️ 部署场景

### 开发环境

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --docs-no-auth \
  --port 8003
```

**特点：**
- 文档无需认证，便于调试
- 无API密钥验证
- 适合本地开发

### 测试环境

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "test-api-key" \
  --enable-multi-api-keys \
  --docs-require-auth \
  --enable-front-intercept \
  --enable-post-intercept \
  --port 8003
```

**特点：**
- 启用API密钥验证
- 文档需要认证
- 启用内容拦截
- 适合内部测试

### 生产环境

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "production-secret-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --enable-front-intercept \
  --enable-post-intercept \
  --workers 4 \
  --max-connections 500 \
  --max-keepalive-connections 200 \
  --port 8003
```

**特点：**
- 强制API密钥验证
- 完全禁用API文档
- 启用内容拦截
- 高性能配置
- 适合生产部署

## 🔒 API密钥管理

### 单个密钥模式

```bash
python run.py \
  --api-key "your-secret-key" \
  --port 8003
```

### 多密钥模式

1. **编辑密钥文件** (`api_keys.json`)
   ```json
   {
     "sk-dev-key-123": {
       "description": "开发环境密钥",
       "enabled": true,
       "created_at": "2024-01-01T00:00:00Z"
     },
     "sk-prod-key-456": {
       "description": "生产环境密钥",
       "enabled": true,
       "created_at": "2024-01-01T00:00:00Z"
     }
   }
   ```

2. **启动服务**
   ```bash
   python run.py \
     --enable-multi-api-keys \
     --api-keys-file api_keys.json \
     --port 8003
   ```

### 密钥管理API

```bash
# 获取所有密钥信息
curl -H "Authorization: Bearer your-admin-key" \
  http://localhost:8003/v1/admin/api-keys

# 添加新密钥
curl -X POST \
  -H "Authorization: Bearer your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"key": "sk-new-key-789", "description": "新密钥"}' \
  http://localhost:8003/v1/admin/api-keys

# 禁用密钥
curl -X PUT \
  -H "Authorization: Bearer your-admin-key" \
  http://localhost:8003/v1/admin/api-keys/sk-old-key-123/disable
```

## 📊 监控和日志

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8003/health

# 拦截服务健康检查
curl http://localhost:8001/health  # 前拦截
curl http://localhost:8002/health  # 后拦截
```

### 用户统计

```bash
# 用户统计信息
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8003/v1/users/user123/stats

# 会话历史
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8003/v1/sessions/session123/history
```

### 日志文件

- **主API日志**: `logs/api.log`
- **用户请求日志**: `logs/user_requests.log`
- **前拦截日志**: `safe_api/logs/front_intercept.log`
- **后拦截日志**: `safe_api/logs/post_intercept.log`

```bash
# 查看实时日志
tail -f logs/api.log
tail -f logs/user_requests.log

# 查看拦截日志
tail -f safe_api/logs/front_intercept.log
tail -f safe_api/logs/post_intercept.log
```

## 🔧 故障排查

### 常见问题

1. **服务无法启动**
   ```bash
   # 检查端口占用
   lsof -i :8003
   
   # 检查vLLM服务
   curl http://localhost:8000/health
   ```

2. **拦截功能不工作**
   ```bash
   # 检查拦截服务状态
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   
   # 检查拦截配置
   python run.py --help | grep intercept
   ```

3. **API密钥验证失败**
   ```bash
   # 检查密钥文件
   cat api_keys.json
   
   # 测试密钥
   curl -H "Authorization: Bearer your-key" \
     http://localhost:8003/health
   ```

4. **依赖问题**
   ```bash
   # 安装完整依赖
   pip install -r requirements.txt
   
   # 安装拦截功能依赖
   pip install torch transformers aiohttp
   ```

### 错误代码

| 错误码 | 说明 | 解决方法 |
|--------|------|----------|
| 401 | API密钥无效 | 检查Authorization头 |
| 404 | 接口不存在 | 检查URL路径 |
| 500 | 内部服务器错误 | 查看日志文件 |
| 502 | vLLM服务不可用 | 检查vLLM服务状态 |

### 调试模式

```bash
# 启用详细日志
python run.py \
  --log-level DEBUG \
  --vllm-api http://localhost:8000 \
  --port 8003

# 开发模式（热重载）
python run.py \
  --reload \
  --docs-no-auth \
  --port 8003
```

## 🧪 测试验证

### 功能测试

```bash
# 运行完整测试
python test_command_line.py

# 测试拦截功能
python test_intercept.py http://localhost:8003 your-api-key

# 查看演示
./demo_usage.sh
```

### 性能测试

```bash
# 简单压力测试
for i in {1..10}; do
  curl -X POST http://localhost:8003/v1/chat/completions \
    -H "Authorization: Bearer your-key" \
    -H "Content-Type: application/json" \
    -d '{"model":"test","messages":[{"role":"user","content":"test"}]}' &
done
wait
```

## 📚 API接口文档

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/v1/chat/completions` | POST | 聊天完成（兼容OpenAI） |
| `/v1/models` | GET | 获取模型列表 |
| `/v1/users/{user_id}/stats` | GET | 用户统计 |
| `/v1/sessions/{session_id}/history` | GET | 会话历史 |

### 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/v1/admin/api-keys` | GET | 获取密钥列表 |
| `/v1/admin/api-keys` | POST | 添加新密钥 |
| `/v1/admin/api-keys/{key}/disable` | PUT | 禁用密钥 |
| `/v1/admin/api-keys/{key}/enable` | PUT | 启用密钥 |

### 响应格式

#### 成功响应
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-3.5-turbo",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "你好！我是AI助手，很高兴为您服务。"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

#### 拦截响应
```json
{
  "id": "chatcmpl-456",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "safety-filter",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "根据相关法律法规，我无法提供关于这个问题的回答，建议换一个话题。"
    },
    "finish_reason": "content_filter"
  }],
  "safety_filter": {
    "triggered": true,
    "reason": "前拦截触发: 匹配到敏感关键词"
  }
}
```

## 📞 技术支持

### 文档资源

- `INTERCEPT_USAGE_EXAMPLE.md` - 拦截功能详细使用指南
- `SECURITY_PARAMETERS_GUIDE.md` - 安全参数配置指南
- `COMMAND_LINE_INTERCEPT_SUMMARY.md` - 命令行集成总结
- `DOCS_SECURITY_COMPARISON.md` - 文档安全参数对比
- `FINAL_TEST_REPORT.md` - 功能测试报告

### 快速帮助

```bash
# 查看帮助信息
python run.py --help
python main.py --help

# 运行演示
./demo_usage.sh

# 运行测试
python test_command_line.py
```

---

🎉 **恭喜！您已经掌握了vLLM Proxy API的使用方法！**

如有任何问题，请查看相关文档或检查日志文件获取详细错误信息。
