# API文档安全参数对比

## 📋 文档安全参数说明

| 参数 | 效果 | 适用场景 | 安全级别 |
|------|------|----------|----------|
| 默认（无参数） | 文档需要认证 | 标准环境 | 🟡 中等 |
| `--docs-no-auth` | 文档无需认证 | 开发环境 | 🟢 低 |
| `--docs-require-auth` | 文档需要API密钥 | 受控环境 | 🟡 中等 |
| `--disable-docs` | **完全禁用文档** | **生产环境** | 🔴 **高** |

## 🔒 安全级别详解

### 🟢 开发环境（低安全）
```bash
python run.py --docs-no-auth --port 8003
```
- ✅ 文档可直接访问：http://localhost:8003/docs
- ✅ 无需任何认证
- ⚠️ 仅适用于本地开发

### 🟡 测试环境（中等安全）
```bash
python run.py --docs-require-auth --api-key "test-key" --port 8003
```
- ✅ 文档可访问：http://localhost:8003/docs
- 🔑 需要在请求头中提供API密钥：`Authorization: Bearer test-key`
- ✅ 适用于内部测试

### 🔴 生产环境（高安全）
```bash
python run.py --disable-docs --api-key "prod-key" --port 8003
```
- ❌ 文档完全不可访问
- ❌ http://localhost:8003/docs 返回404
- ❌ http://localhost:8003/redoc 返回404
- ❌ http://localhost:8003/openapi.json 返回404
- ✅ **推荐用于生产环境**

## 🚀 推荐配置

### 开发环境
```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --docs-no-auth \
  --port 8003
```

### 内部测试
```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --api-key "test-api-key" \
  --docs-require-auth \
  --enable-front-intercept \
  --enable-post-intercept \
  --port 8003
```

### 生产部署
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
  --port 8003
```

## 🔍 验证方法

### 检查文档是否可访问

```bash
# 1. 检查Swagger UI
curl -I http://localhost:8003/docs

# 2. 检查ReDoc
curl -I http://localhost:8003/redoc

# 3. 检查OpenAPI schema
curl -I http://localhost:8003/openapi.json
```

### 预期结果

| 配置 | /docs | /redoc | /openapi.json |
|------|-------|--------|---------------|
| `--docs-no-auth` | 200 OK | 200 OK | 200 OK |
| `--docs-require-auth` | 401 Unauthorized* | 401 Unauthorized* | 401 Unauthorized* |
| `--disable-docs` | 404 Not Found | 404 Not Found | 404 Not Found |

*需要提供正确的API密钥才能访问

## ⚠️ 安全提醒

### 生产环境必须禁用文档

1. **信息泄露风险**：API文档暴露了所有接口结构
2. **攻击面扩大**：增加了潜在的攻击入口
3. **合规要求**：生产环境通常要求关闭调试功能

### 正确的生产配置

```bash
# ✅ 推荐：完全禁用文档
--disable-docs

# ❌ 不推荐：仅要求认证（仍有风险）
--docs-require-auth
```

### 文档访问测试

使用curl测试文档访问权限：

```bash
# 测试无认证访问
curl http://localhost:8003/docs

# 测试带认证访问
curl -H "Authorization: Bearer your-api-key" http://localhost:8003/docs
```

通过合理配置文档安全参数，可以在不同环境下平衡开发便利性和安全性。
