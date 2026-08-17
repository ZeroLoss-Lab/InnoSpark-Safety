# 拦截功能使用示例

## 快速启动指南

### 步骤1: 启动safe_api拦截服务

在`safe_api`目录下启动前后拦截服务：

```bash
cd safe_api

# 启动前拦截服务（端口8001）
python front_intercept_api.py &

# 启动后拦截服务（端口8002）  
python post_intercept_api.py &

# 或者使用提供的启动脚本
python start_services.py
```

验证服务启动：
```bash
# 检查前拦截服务
curl http://localhost:8001/health

# 检查后拦截服务
curl http://localhost:8002/health
```

### 步骤2: 启动带拦截功能的主API

#### 方法1: 使用run.py脚本（推荐）

```bash
# 启用前后拦截（完整安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003

# 仅启用前拦截（带安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --disable-docs \
  --port 8003

# 仅启用后拦截（带安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-post-intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --disable-docs \
  --port 8003
```

#### 方法2: 直接使用main.py

```bash
# 启用前后拦截
python main.py \
  --enable-front-intercept \
  --enable-post-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --port 8003

# 仅启用前拦截
python main.py \
  --enable-front-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --port 8003
```

### 步骤3: 测试拦截功能

使用测试脚本验证：

```bash
# 修改测试脚本中的API地址和密钥
python test_intercept.py http://localhost:8003 your-api-key
```

或手动测试：

```bash
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "test-model",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

## 完整启动示例

### 场景1: 本地开发环境

```bash
# 终端1: 启动vLLM服务
# 按照vLLM官方文档启动

# 终端2: 启动拦截服务  
cd safe_api
python start_services.py

# 终端3: 启动主API（开发环境配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "dev-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --docs-no-auth \
  --port 8003
```

### 场景2: 生产环境

```bash
# 终端1: 启动拦截服务（后台运行）
cd safe_api
nohup python front_intercept_api.py > logs/front_intercept.log 2>&1 &
nohup python post_intercept_api.py > logs/post_intercept.log 2>&1 &

# 终端2: 启动主API（生产配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "your-production-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --workers 4 \
  --max-connections 500 \
  --max-keepalive-connections 200 \
  --port 8003
```

### 场景3: 仅前拦截（检查用户输入）

```bash
# 仅启动前拦截服务
cd safe_api
python front_intercept_api.py &

# 启动主API（仅前拦截，带安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003
```

### 场景4: 仅后拦截（检查模型输出）

```bash
# 仅启动后拦截服务
cd safe_api  
python post_intercept_api.py &

# 启动主API（仅后拦截，带安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-post-intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003
```

## 参数说明

### 拦截相关参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--enable-front-intercept` | 启用前拦截 | 未启用 |
| `--enable-post-intercept` | 启用后拦截 | 未启用 |
| `--front-intercept-url` | 前拦截API地址 | http://localhost:8001/intercept |
| `--post-intercept-url` | 后拦截API地址 | http://localhost:8002/intercept |
| `--intercept-timeout` | 拦截API超时时间（秒） | 5.0 |

### 常用服务参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--vllm-api` | vLLM API地址 | http://localhost:8000 |
| `--port` | 服务端口 | 8001 |
| `--api-key` | API密钥 | 无 |
| `--workers` | 工作进程数 | 1 |

## 端口规划建议

- **vLLM服务**: 8000
- **前拦截服务**: 8001  
- **后拦截服务**: 8002
- **主API服务**: 8003

这样可以避免端口冲突，便于管理。

## 日志和监控

启动后可以通过以下方式查看日志：

```bash
# 查看主API日志
tail -f logs/api.log

# 查看用户请求日志
tail -f logs/user_requests.log

# 查看拦截服务日志（如果使用nohup启动）
tail -f safe_api/logs/front_intercept.log
tail -f safe_api/logs/post_intercept.log
```

检查服务状态：

```bash
# 检查主API健康
curl http://localhost:8003/health

# 检查前拦截服务
curl http://localhost:8001/health

# 检查后拦截服务  
curl http://localhost:8002/health
```

## 故障排查

### 常见问题

1. **拦截服务连接失败**
   ```
   ERROR: 前拦截API调用出错: Connection refused
   ```
   - 检查拦截服务是否启动
   - 验证拦截服务URL是否正确
   - 检查防火墙设置

2. **拦截服务超时**
   ```
   ERROR: 前拦截API调用出错: Timeout
   ```
   - 增加`--intercept-timeout`参数值
   - 检查拦截服务性能
   - 查看拦截服务日志

3. **端口已被占用**
   ```
   ERROR: Address already in use
   ```
   - 使用`--port`参数指定其他端口
   - 或停止占用端口的其他服务

### 检查命令

```bash
# 检查端口占用
lsof -i :8001  # 前拦截
lsof -i :8002  # 后拦截  
lsof -i :8003  # 主API

# 检查进程
ps aux | grep python

# 检查网络连通性
telnet localhost 8001
telnet localhost 8002
```

## 性能建议

1. **生产环境**：使用多worker进程
   ```bash
   --workers 4
   ```

2. **高并发场景**：调整连接池配置
   ```bash
   --max-connections 500 --max-keepalive-connections 200
   ```

3. **网络优化**：将拦截服务部署在同一机器或同一网段

4. **监控告警**：设置拦截服务的健康检查和告警机制

这样，您就可以根据需要灵活启动带拦截功能的API服务了！
