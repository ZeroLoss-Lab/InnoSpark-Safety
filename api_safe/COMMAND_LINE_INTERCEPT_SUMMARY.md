# 命令行拦截功能集成总结

## 🎯 实现目标

✅ **保持原有启动方式不变**
✅ **通过命令行参数指定拦截API地址**
✅ **支持独立启动safe_api服务**
✅ **使用远程API模式进行拦截**

## 📋 完成的修改

### 1. 核心文件修改

#### `main.py`
- 添加命令行参数解析
- 支持拦截相关参数
- 运行时配置覆盖
- 拦截状态日志显示

#### `config.py`  
- 添加`update_from_args()`方法
- 支持运行时配置更新
- 修复Pydantic警告

#### `run.py`
- 添加拦截相关参数
- 更新帮助文档和示例
- 配置显示增强
- 环境变量映射

### 2. 新增文件

- `INTERCEPT_USAGE_EXAMPLE.md` - 详细使用指南
- `test_command_line.py` - 命令行功能测试
- `COMMAND_LINE_INTERCEPT_SUMMARY.md` - 本总结文档

## 🚀 使用方式

### 标准启动流程

#### 步骤1: 启动safe_api服务

```bash
cd safe_api

# 方法1: 使用start_services.py
python start_services.py

# 方法2: 分别启动
python front_intercept_api.py &  # 端口8001
python post_intercept_api.py &   # 端口8002
```

#### 步骤2: 启动主API（带拦截参数）

```bash
# 使用run.py（推荐，完整安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --docs-require-auth \
  --port 8003

# 或直接使用main.py（完整参数）
python main.py \
  --enable-front-intercept \
  --enable-post-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --port 8003
```

### 命令行参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--enable-front-intercept` | 启用前拦截 | 未启用 |
| `--enable-post-intercept` | 启用后拦截 | 未启用 |
| `--front-intercept-url` | 前拦截API地址 | http://localhost:8001/intercept |
| `--post-intercept-url` | 后拦截API地址 | http://localhost:8002/intercept |
| `--intercept-timeout` | 拦截超时时间（秒） | 5.0 |

### 启动示例

```bash
# 1. 仅前拦截（带安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003

# 2. 仅后拦截（带安全配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-post-intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003

# 3. 前后拦截 + 自定义地址（完整配置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --front-intercept-url http://192.168.1.100:8001/intercept \
  --post-intercept-url http://192.168.1.100:8002/intercept \
  --api-key "your-api-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --port 8003

# 4. 生产环境配置（完整安全设置）
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "your-production-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --workers 4 \
  --max-connections 500 \
  --max-keepalive-connections 200 \
  --port 8003
```

## 🔧 技术实现

### 配置覆盖机制

1. **默认配置** (config.py + 环境变量)
2. **命令行参数覆盖** (运行时)
3. **自动设置远程API模式** (use_local_intercept=false)

### 参数处理流程

```
命令行参数 → 配置更新 → 环境变量设置 → 拦截器初始化
```

### 拦截模式说明

- **本地集成模式**: `use_local_intercept=true` (直接加载模型)
- **远程API模式**: `use_local_intercept=false` (调用外部服务)

命令行模式默认使用**远程API模式**，符合您的需求。

## 📊 功能验证

### 测试方法

```bash
# 1. 测试命令行参数
python test_command_line.py

# 2. 查看帮助信息
python main.py --help
python run.py --help

# 3. 测试拦截功能
python test_intercept.py http://localhost:8003 your-api-key
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8001/health  # 前拦截
curl http://localhost:8002/health  # 后拦截  
curl http://localhost:8003/health  # 主API
```

## 🛡️ 拦截工作流程

### 前拦截流程
```
用户输入 → 前拦截API → 安全检查 → 触发/通过 → LLM处理
```

### 后拦截流程  
```
LLM输出 → 后拦截API → 安全检查 → 触发/通过 → 返回用户
```

### 安全响应
```json
{
  "choices": [{
    "message": {
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

## 📝 日志记录

启动时会显示拦截配置：

```
INFO: 前拦截已启用: http://localhost:8001/intercept
INFO: 后拦截已启用: http://localhost:8002/intercept  
INFO: 拦截超时时间: 5.0秒
INFO: 拦截模式: 远程API
```

运行时会记录拦截操作：

```
INFO: Request abc-123: 执行前拦截检查
INFO: Request abc-123: 前拦截触发 - 匹配到敏感关键词
```

## 🔗 服务架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   safe_api      │    │   main API      │    │   vLLM API      │
│                 │    │                 │    │                 │
│ front:8001      │◄───┤ :8003           │◄───┤ :8000           │
│ post :8002      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎯 优势特点

1. **保持兼容**: 原有启动方式完全不变
2. **灵活配置**: 命令行参数灵活指定拦截服务
3. **独立部署**: safe_api可独立启动和管理
4. **容错设计**: 拦截服务异常不影响主服务
5. **日志完整**: 详细的拦截日志和状态记录

## 🛠️ 故障排查

### 常见问题

1. **拦截服务连接失败**
   - 检查safe_api是否启动
   - 验证URL参数是否正确

2. **端口冲突**
   - 使用`--port`指定其他端口
   - 检查端口占用情况

3. **参数不生效**
   - 确认参数格式正确
   - 查看启动日志中的配置显示

### 调试命令

```bash
# 检查端口占用
lsof -i :8001 :8002 :8003

# 检查进程
ps aux | grep python

# 测试连通性
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## 📚 相关文档

- [INTERCEPT_USAGE_EXAMPLE.md](./INTERCEPT_USAGE_EXAMPLE.md) - 详细使用指南
- [CONTENT_INTERCEPT_GUIDE.md](./CONTENT_INTERCEPT_GUIDE.md) - 完整功能说明
- [safe_api/README.md](./safe_api/README.md) - 拦截服务文档

---

🎉 **命令行拦截功能已完成！**

现在您可以按照原有方式启动API，只需添加拦截相关的命令行参数即可实现内容安全拦截功能。
