# 🚀 快速启动参考

## 最常用启动命令

### 1. 基本启动（多API key）
```bash
python run.py --api-keys-file api_keys.json --enable-multi-api-keys
```

### 2. 生产环境启动
```bash
python run.py \
  --port 8001 \
  --disable-docs \
  --api-keys-file api_keys.json \
  --enable-multi-api-keys \
  --log-level WARNING
```

### 3. 开发环境启动
```bash
python run.py \
  --port 8001 \
  --docs-no-auth \
  --api-keys-file api_keys.json \
  --enable-multi-api-keys \
  --log-level DEBUG \
  --reload
```

### 4. 自定义端口和vLLM地址
```bash
python run.py \
  --port 8002 \
  --vllm-api http://192.168.1.100:8000 \
  --api-keys-file api_keys.json \
  --enable-multi-api-keys
```

### 5. 单个API key启动（向后兼容）
```bash
python run.py --api-key "sk-your-single-api-key"
```

## 参数速查表

| 参数 | 说明 | 示例 |
|------|------|------|
| `--port` | 服务端口 | `--port 8002` |
| `--host` | 绑定地址 | `--host 127.0.0.1` |
| `--api-keys-file` | API key文件 | `--api-keys-file keys.json` |
| `--enable-multi-api-keys` | 启用多API key | `--enable-multi-api-keys` |
| `--disable-docs` | 禁用文档 | `--disable-docs` |
| `--docs-no-auth` | 文档无需认证 | `--docs-no-auth` |
| `--log-level` | 日志级别 | `--log-level DEBUG` |
| `--vllm-api` | vLLM地址 | `--vllm-api http://server:8000` |
| `--reload` | 热重载 | `--reload` |

## 环境配置

### 开发环境
```bash
# 启用文档，无需认证，调试日志
python run.py --docs-no-auth --log-level DEBUG --reload
```

### 测试环境
```bash
# 启用文档，需要认证，信息日志
python run.py --docs-require-auth --log-level INFO
```

### 生产环境
```bash
# 禁用文档，警告日志
python run.py --disable-docs --log-level WARNING
```

## 验证启动

```bash
# 健康检查
curl http://localhost:8001/health

# API调用测试
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Authorization: Bearer sk-your-api-key-1" \
  -H "Content-Type: application/json" \
  -d '{"model": "your-model", "messages": [{"role": "user", "content": "Hello"}]}'
```

## 常用组合

### 快速开发
```bash
python run.py --docs-no-auth --reload
```

### 安全生产
```bash
python run.py --disable-docs --api-keys-file prod_keys.json
```

### 多实例
```bash
# 实例1
python run.py --port 8001 --api-keys-file keys1.json

# 实例2  
python run.py --port 8002 --api-keys-file keys2.json
```

---

**💡 提示**: 使用 `python run.py --help` 查看完整参数列表 