# 安全参数配置指南

## 📋 完整安全参数列表

### API密钥认证参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--api-key` | 单个API密钥 | 无 | `--api-key "your-secret-key"` |
| `--enable-multi-api-keys` | 启用多API密钥支持 | true | `--enable-multi-api-keys` |
| `--disable-multi-api-keys` | 禁用多API密钥支持 | false | `--disable-multi-api-keys` |
| `--api-keys-file` | API密钥文件路径 | api_keys.json | `--api-keys-file "keys.json"` |

### 文档安全参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--enable-docs` | 启用API文档 | true | `--enable-docs` |
| `--disable-docs` | 禁用API文档（生产推荐） | false | `--disable-docs` |
| `--docs-require-auth` | 文档需要API密钥认证 | true | `--docs-require-auth` |
| `--docs-no-auth` | 文档无需认证（开发环境） | false | `--docs-no-auth` |

### 内容拦截参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--enable-front-intercept` | 启用前拦截 | false | `--enable-front-intercept` |
| `--enable-post-intercept` | 启用后拦截 | false | `--enable-post-intercept` |
| `--front-intercept-url` | 前拦截API地址 | http://localhost:8001/intercept | `--front-intercept-url "http://192.168.1.100:8001/intercept"` |
| `--post-intercept-url` | 后拦截API地址 | http://localhost:8002/intercept | `--post-intercept-url "http://192.168.1.100:8002/intercept"` |
| `--intercept-timeout` | 拦截超时时间（秒） | 5.0 | `--intercept-timeout 10.0` |

### 性能配置参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--workers` | Worker进程数 | 1 | `--workers 4` |
| `--max-connections` | 最大连接数 | 200 | `--max-connections 500` |
| `--max-keepalive-connections` | 保持活跃连接数 | 100 | `--max-keepalive-connections 200` |

## 🛡️ 安全级别配置

### 开发环境（低安全）

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --docs-no-auth \
  --port 8003
```

**特点：**
- 文档无需认证，便于开发调试
- 不启用API密钥验证
- 适用于本地开发环境

### 测试环境（中等安全）

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "test-api-key" \
  --docs-require-auth \
  --enable-front-intercept \
  --enable-post-intercept \
  --port 8003
```

**特点：**
- 启用API密钥验证
- 文档需要认证（可访问但需密钥）
- 启用内容拦截
- 适用于测试环境

### 生产环境（高安全）

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "prod-secret-key" \
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
- 支持多API密钥管理
- 完全禁用API文档
- 启用内容拦截
- 高性能配置
- 适用于生产环境

## 📝 配置组合示例

### 1. 最小安全配置

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "basic-key" \
  --port 8003
```

### 2. 标准安全配置

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "standard-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --docs-require-auth \
  --port 8003
```

### 3. 完整拦截配置

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "secure-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --docs-require-auth \
  --enable-front-intercept \
  --enable-post-intercept \
  --front-intercept-url http://localhost:8001/intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --intercept-timeout 5.0 \
  --port 8003
```

### 4. 高性能生产配置

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "production-key" \
  --enable-multi-api-keys \
  --api-keys-file api_keys.json \
  --disable-docs \
  --enable-front-intercept \
  --enable-post-intercept \
  --workers 8 \
  --max-connections 1000 \
  --max-keepalive-connections 500 \
  --port 8003
```

## 🔒 API密钥文件格式

### api_keys.json 示例

```json
{
  "sk-1234567890abcdef": {
    "description": "开发环境密钥",
    "enabled": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_used": null,
    "usage_count": 0
  },
  "sk-abcdef1234567890": {
    "description": "生产环境密钥", 
    "enabled": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_used": "2024-01-15T10:30:00Z",
    "usage_count": 1523
  },
  "sk-test9876543210": {
    "description": "测试密钥（已禁用）",
    "enabled": false,
    "created_at": "2024-01-01T00:00:00Z",
    "last_used": "2024-01-10T15:20:00Z",
    "usage_count": 45
  }
}
```

## 🚨 安全建议

### 密钥管理

1. **生产环境**：
   - 使用强密钥（至少32字符）
   - 定期轮换密钥
   - 禁用API文档
   - 启用多密钥管理

2. **密钥格式**：
   - 使用前缀标识：`sk-prod-`, `sk-dev-`, `sk-test-`
   - 包含随机字符串
   - 避免使用简单密码

3. **访问控制**：
   - 限制密钥访问权限
   - 记录密钥使用情况
   - 监控异常使用

### 文档安全

1. **生产环境**：完全禁用文档（`--disable-docs`）
2. **测试环境**：启用文档但需要认证（`--docs-require-auth`）
3. **开发环境**：可以无需认证（`--docs-no-auth`）

### 拦截配置

1. **前拦截**：检查用户输入，防止恶意请求
2. **后拦截**：检查模型输出，确保内容安全
3. **超时设置**：根据网络状况调整`--intercept-timeout`

## 🔍 安全检查清单

### 启动前检查

- [ ] API密钥是否设置
- [ ] 密钥文件是否存在且格式正确
- [ ] 文档安全配置是否合适
- [ ] 拦截服务是否启动
- [ ] 端口是否冲突
- [ ] 防火墙配置是否正确

### 运行时监控

- [ ] API密钥使用情况
- [ ] 异常访问记录
- [ ] 拦截触发频率
- [ ] 服务健康状态
- [ ] 性能指标监控

通过合理配置这些安全参数，可以确保API服务在不同环境下的安全性和稳定性。
