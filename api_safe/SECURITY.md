# 安全配置指南

本文档详细说明如何配置 vLLM Proxy API 以防止 Swagger UI 敏感信息泄露漏洞和其他安全问题。

## 🚨 Swagger UI 敏感信息泄露漏洞修复

### 漏洞描述
默认情况下，FastAPI 会在 `/docs` 和 `/redoc` 端点公开 Swagger UI 文档，任何人都可以访问并查看完整的 API 接口信息，这可能导致敏感信息泄露。

### 修复方案
我们已经实施了以下安全防护措施：

1. **禁用默认文档端点**：禁用了 FastAPI 默认的不安全文档端点
2. **创建受保护的文档端点**：实现了需要认证的自定义文档端点
3. **配置化控制**：通过环境变量灵活控制文档访问策略

## 🔐 安全配置选项

### 1. 文档安全配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 启用文档 | `ENABLE_DOCS` | `true` | 是否启用 API 文档 |
| 文档认证 | `DOCS_REQUIRE_AUTH` | `true` | 文档是否需要 API Key 认证 |
| API 密钥 | `API_KEY` | 无 | 访问 API 和文档的密钥 |

### 2. 安全等级配置

#### 🔒 生产环境（推荐）
```bash
# 完全禁用文档，最高安全等级
ENABLE_DOCS=false
DOCS_REQUIRE_AUTH=true
API_KEY=your-production-secure-key
```

#### 🛡️ 测试环境
```bash
# 启用文档但需要认证
ENABLE_DOCS=true
DOCS_REQUIRE_AUTH=true
API_KEY=your-test-api-key
```

#### 🔓 开发环境（内网）
```bash
# 启用文档，无需认证（仅限内网环境）
ENABLE_DOCS=true
DOCS_REQUIRE_AUTH=false
API_KEY=
```

## 🚀 命令行参数支持

除了环境变量外，您还可以直接通过命令行参数配置安全选项：

### 基本命令行参数

| 参数 | 功能 | 示例 |
|------|------|------|
| `--api-key` | 设置API密钥 | `--api-key "your-key"` |
| `--enable-docs` | 启用API文档 | `--enable-docs` |
| `--disable-docs` | 禁用API文档 | `--disable-docs` |
| `--docs-require-auth` | 文档需要认证 | `--docs-require-auth` |
| `--docs-no-auth` | 文档无需认证 | `--docs-no-auth` |

### 完整配置示例

#### 🔒 生产环境启动
```bash
python run.py \
  --vllm-api "https://your-vllm-api.com" \
  --disable-docs \
  --api-key "your-production-key" \
  --port 8001
```

#### 🛡️ 测试环境启动
```bash
python run.py \
  --vllm-api "https://test-vllm-api.com" \
  --docs-require-auth \
  --api-key "your-test-key" \
  --port 8001
```

#### 🔓 开发环境启动
```bash
python run.py \
  --vllm-api "http://localhost:8000" \
  --docs-no-auth \
  --port 8001
```

### 优先级说明

配置优先级从高到低：
1. **命令行参数**（最高优先级）
2. **环境变量**
3. **默认值**（最低优先级）

## 📋 安全检查清单

### ✅ 部署前检查

- [ ] 确认 `ENABLE_DOCS` 在生产环境设置为 `false`
- [ ] 确认 `API_KEY` 已设置为强密码
- [ ] 确认 `DOCS_REQUIRE_AUTH` 设置为 `true`
- [ ] 测试文档端点的访问控制
- [ ] 验证 API 密钥认证正常工作

### 🧪 安全测试

#### 1. 测试文档访问控制
```bash
# 测试无认证访问（应该被拒绝）
curl -i http://localhost:8001/docs

# 测试有效认证访问
curl -i -H "Authorization: Bearer your-api-key" http://localhost:8001/docs
```

#### 2. 测试 API 密钥验证
```bash
# 测试无效 API Key（应该返回 401）
curl -i -H "Authorization: Bearer invalid-key" \
     -H "Content-Type: application/json" \
     -d '{"model":"default","messages":[{"role":"user","content":"test"}]}' \
     http://localhost:8001/v1/chat/completions

# 测试有效 API Key（应该成功）
curl -i -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"model":"default","messages":[{"role":"user","content":"test"}]}' \
     http://localhost:8001/v1/chat/completions
```

## 🔍 安全监控

### 1. 日志监控
系统会记录所有访问尝试，包括：
- 成功的 API 调用
- 失败的认证尝试
- 文档访问记录

查看安全日志：
```bash
# 查看系统日志
tail -f logs/api.log | grep -E "(401|403|docs|authentication)"

# 查看用户请求日志
tail -f logs/user_requests.log | jq '.error'
```

### 2. 异常访问检测
关注以下异常模式：
- 频繁的 401 错误（可能的密钥爆破攻击）
- 大量的文档访问请求
- 来自可疑 IP 的请求

## 🛡️ 额外安全建议

### 1. 网络安全
- 使用 HTTPS 加密传输
- 配置防火墙限制访问 IP
- 部署在内网环境，通过 VPN 访问

### 2. API 密钥管理
- 使用强随机密钥（建议 32+ 字符）
- 定期轮换 API 密钥
- 不要在代码中硬编码密钥
- 使用环境变量或密钥管理服务

### 3. 服务部署
- 使用非特权用户运行服务
- 限制服务器资源使用
- 配置日志轮转，避免磁盘满载
- 定期更新依赖包

## 🔧 故障排除

### 常见问题

#### 1. 文档访问被拒绝
**错误**：`API documentation requires authentication`

**解决方案**：
```bash
# 确认 API 密钥正确
curl -i -H "Authorization: Bearer your-actual-api-key" http://localhost:8001/docs

# 或者在开发环境关闭文档认证
export DOCS_REQUIRE_AUTH=false
```

#### 2. 文档完全无法访问
**错误**：`API documentation is disabled`

**解决方案**：
```bash
# 启用文档
export ENABLE_DOCS=true
```

#### 3. API 调用认证失败
**错误**：`Invalid API key`

**检查步骤**：
1. 确认环境变量 `API_KEY` 正确设置
2. 确认请求头格式：`Authorization: Bearer your-api-key`
3. 检查密钥中是否有多余的空格或特殊字符

## 📚 相关文档

- [API 使用指南](README.md#api-使用指南)
- [配置说明](README.md#配置选项)
- [部署指南](README.md#快速部署)

## 🚨 安全事件响应

如果发现安全问题：

1. **立即行动**：
   - 禁用文档：`ENABLE_DOCS=false`
   - 更换 API 密钥
   - 检查访问日志

2. **分析影响**：
   - 确定泄露信息范围
   - 检查异常访问记录
   - 评估潜在风险

3. **修复和预防**：
   - 应用安全补丁
   - 加强访问控制
   - 更新安全配置

---

**重要提醒**：在生产环境中，强烈建议将 `ENABLE_DOCS` 设置为 `false` 以完全禁用 API 文档，这是防止敏感信息泄露的最佳实践。 