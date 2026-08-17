# 性能优化指南 🚀

## 问题诊断

如果你的转发API并发性能不如原始API，主要原因可能包括：

### 1. 连接池限制 ⚠️
**问题**：每次请求都创建新的HTTP连接，无法复用连接
**影响**：严重限制并发能力，连接建立开销大

**解决方案**：已优化为使用持久化连接池
```python
# 优化前：每次创建新客户端
async with httpx.AsyncClient() as client:
    response = await client.post(...)

# 优化后：复用连接池
client = await self._get_client()  # 复用持久化客户端
response = await client.post(...)
```

### 2. 同步IO阻塞 ⚠️
**问题**：文件保存等同步操作阻塞事件循环
**影响**：严重影响并发性能

**解决方案**：
- 异步文件操作
- 批量延迟保存
- 线程池执行IO操作

### 3. 进程和连接数限制 ⚠️
**问题**：默认单进程，连接池配置保守
**影响**：无法充分利用系统资源

## 性能配置

### 🚀 超高并发配置（600并发）
如果你的原始API能达到600并发，使用此配置：
```bash
# 使用config_600_concurrent.env
WORKERS=8                             # 多进程，充分利用CPU
MAX_CONNECTIONS=800                   # 总连接数，留缓冲
MAX_KEEPALIVE_CONNECTIONS=600         # 匹配原始API并发数
LOG_LEVEL=WARNING                     # 减少日志IO开销
```

### 🎯 匹配原始API配置（200并发）
如果你的原始API能达到200并发，使用此配置：
```bash
# 使用config_match_original.env
WORKERS=1                             # 单进程，避免多进程开销
MAX_CONNECTIONS=250                   # 总连接数，留缓冲
MAX_KEEPALIVE_CONNECTIONS=200         # 匹配原始API并发数
```

### 基础配置（适合开发环境）
```bash
# 使用config_example.env
WORKERS=1
MAX_CONNECTIONS=200
MAX_KEEPALIVE_CONNECTIONS=100
```

### 高并发配置（超越原始API）
```bash
# 使用config_production.env
WORKERS=4                          # CPU核心数
MAX_CONNECTIONS=500               # 最大连接数
MAX_KEEPALIVE_CONNECTIONS=200     # 保持活跃连接数
```

## 启动命令

### 🚀 匹配600并发原始API
```bash
# 方法1：使用配置文件（推荐）
cp config_600_concurrent.env .env
python run.py

# 方法2：命令行参数
python run.py \
  --vllm-api http://localhost:8000 \
  --port 8001 \
  --workers 8 \
  --max-connections 800 \
  --max-keepalive-connections 600
```

### 🎯 匹配200并发原始API
```bash
# 方法1：使用配置文件（推荐）
cp config_match_original.env .env
python run.py

# 方法2：命令行参数
python run.py \
  --vllm-api http://localhost:8000 \
  --port 8001 \
  --workers 1 \
  --max-connections 250 \
  --max-keepalive-connections 200
```

### 开发环境
```bash
# 单进程，适合开发调试
python run.py --vllm-api http://localhost:8000 --port 8001
```

### 高并发生产环境
```bash
# 多进程高并发
python run.py \
  --vllm-api http://localhost:8000 \
  --port 8001 \
  --workers 4 \
  --max-connections 500 \
  --max-keepalive-connections 200
```

### 使用配置文件
```bash
# 复制配置文件
cp config_production.env .env

# 启动服务
python run.py
```

## 性能测试

### 验证600并发能力
```bash
# 使用wrk测试600并发
wrk -t16 -c600 -d60s --timeout 60s \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"Hello"}]}' \
  http://localhost:8001/v1/chat/completions
```

### 验证200并发能力
```bash
# 使用wrk测试200并发
wrk -t12 -c200 -d30s --timeout 30s \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"Hello"}]}' \
  http://localhost:8001/v1/chat/completions
```

### 对比测试
```bash
# 测试原始API - 600并发
wrk -t16 -c600 -d60s http://localhost:8000/v1/chat/completions

# 测试转发API - 600并发  
wrk -t16 -c600 -d60s http://localhost:8001/v1/chat/completions

# 测试原始API - 200并发
wrk -t12 -c200 -d30s http://localhost:8000/v1/chat/completions

# 测试转发API - 200并发
wrk -t12 -c200 -d30s http://localhost:8001/v1/chat/completions
```

### 使用hey进行测试
```bash
# 安装hey
go install github.com/rakyll/hey@latest

# 测试
hey -n 1000 -c 50 -m POST \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"Hello"}]}' \
  http://localhost:8001/v1/chat/completions
```

## 性能优化清单 ✅

- [x] **连接池优化**：使用持久化httpx.AsyncClient
- [x] **异步IO**：文件操作改为异步+线程池
- [x] **批量保存**：延迟2秒批量保存，减少IO频率
- [x] **连接复用**：配置keep-alive连接
- [x] **多进程支持**：uvicorn workers配置
- [x] **连接数配置**：可调节的连接池大小

## 监控和调优

### 1. 监控指标
- 响应时间
- 并发连接数
- 错误率
- CPU和内存使用率

### 2. 调优建议
- **匹配原始API**：使用`config_match_original.env`
- **Workers数量**：单进程避免开销，多进程提升吞吐
- **连接数**：根据后端vLLM的能力调整
- **超时设置**：根据模型响应时间调整

### 3. 问题排查
```bash
# 查看当前连接数
ss -tln | grep :8001

# 监控进程
htop

# 查看日志
tail -f logs/api.log
```

## 性能对比

### 优化前
- 单进程
- 每次请求创建新连接
- 同步文件IO
- 默认连接池限制
- **预期并发**：20-50

### 优化后（匹配600并发API）
- 多进程高性能
- 连接池复用
- 异步文件IO
- 600活跃连接
- 智能超时调整
- **预期并发**：600（匹配原始API）

### 优化后（匹配200并发API）
- 单进程，避免开销
- 连接池复用
- 异步文件IO
- 200活跃连接
- **预期并发**：200（匹配原始API）

### 优化后（超越原始API）
- 多进程支持
- 连接池复用
- 异步文件IO
- 高并发连接池
- **预期并发**：200+

## 常见问题

### Q: 为什么设置了高并发配置但性能没提升？
A: 检查以下几点：
1. 后端vLLM是否支持相应并发
2. 网络带宽是否足够
3. 系统资源（CPU/内存）是否充足
4. 防火墙或负载均衡器限制

### Q: 多worker模式下数据一致性如何保证？
A: 对话历史等数据通过文件持久化，多进程间自动同步。

### Q: 如何确定最佳的worker数量？
A: 建议从CPU核心数开始，根据实际负载调整。过多worker可能导致资源竞争。

### Q: 为什么600并发使用多进程而200并发使用单进程？
A: 
- **200并发**：单进程足够处理，避免多进程开销
- **600并发**：需要多进程充分利用CPU资源，单进程可能成为瓶颈

### Q: 如何确定我需要哪种配置？
A: 根据你的原始API并发能力选择：
- 原始API ≤ 200并发：使用 `config_match_original.env`
- 原始API ≥ 600并发：使用 `config_600_concurrent.env`
- 自定义需求：调整相应参数

### Q: 为什么600并发配置的日志级别是WARNING？
A: 高并发下减少日志IO操作，避免成为性能瓶颈。生产环境可以考虑异步日志。 