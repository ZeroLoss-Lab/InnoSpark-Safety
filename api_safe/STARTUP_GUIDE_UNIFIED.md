# 统一架构启动指南

## 📋 概述

新的统一架构将拦截逻辑和配置分离：
- **Safe API**: 负责具体的拦截逻辑和BERT阈值配置
- **主API**: 负责决定是否启用前后拦截以及RAG系统

## 🏗️ 架构图

```
用户请求 → 主API (决策层) → Safe API (执行层)
                ↓              ↓
        启用/禁用拦截功能    BERT阈值配置
        启用/禁用RAG        关键词库配置
```

---

## 🚀 启动步骤

### 第一步：启动 Safe API 服务

Safe API 负责具体的拦截逻辑执行，需要配置 BERT 阈值。

#### 1.1 前拦截 API 服务

```bash
# 启动前拦截服务 (端口 8001)
cd /Users/ssy/work/api

# 设置BERT前拦截阈值
export BERT_FRONT_HIGH_THRESHOLD=0.97    # 高阈值：>=此值直接拦截
export BERT_FRONT_LOW_THRESHOLD=0.00002  # 低阈值：<=此值直接通过
export MODEL_FRONT_PATH="./safe_api/models/front_model"
export HIGH_SENSITIVE_KEYWORDS_PATH="./safe_api/data/high_sensitive_keywords.json"
export BLACKLIST_1W_PATH="./safe_api/data/blacklist_1w.json"

# 启动前拦截服务
python safe_api/front_intercept_api.py
```

#### 1.2 后拦截 API 服务

```bash
# 新开终端，启动后拦截服务 (端口 8002)
cd /Users/ssy/work/api

# 设置BERT后拦截阈值
export BERT_POST_THRESHOLD=0.5           # 后拦截阈值
export MODEL_POST_PATH="./safe_api/models/post_model"

# 启动后拦截服务
python safe_api/post_intercept_api.py
```

### 第二步：启动主 API 服务

主API 负责决定是否启用各种功能，不需要配置具体的拦截阈值。

```bash
# 新开终端，启动主API服务
cd /Users/ssy/work/api

# 设置主API功能开关
export ENABLE_FRONT_INTERCEPT=true       # 是否启用前拦截
export ENABLE_POST_INTERCEPT=true        # 是否启用后拦截
export ENABLE_RAG=true                   # 是否启用RAG系统

# 设置Safe API服务地址
export FRONT_INTERCEPT_URL="http://localhost:8001/intercept"
export POST_INTERCEPT_URL="http://localhost:8002/intercept"
export USE_LOCAL_INTERCEPT=false         # 使用远程Safe API模式

# 设置RAG系统配置
export RAG_SERVICE_URL="http://localhost:8000/retrieve"
export RAG_TOP_K=5
export RAG_TIMEOUT=10.0

# 设置vLLM配置
export VLLM_API_BASE="http://localhost:8000"

# 启动主API服务
python main.py
```

---

## 🔧 配置文件方式

### Safe API 配置文件 (safe_api_config.env)

```bash
# Safe API 拦截逻辑配置
# 用于配置具体的拦截参数和阈值

# === BERT 阈值配置 ===
BERT_FRONT_HIGH_THRESHOLD=0.97
BERT_FRONT_LOW_THRESHOLD=0.00002
BERT_POST_THRESHOLD=0.5

# === 模型路径配置 ===
MODEL_FRONT_PATH=./safe_api/models/front_model
MODEL_POST_PATH=./safe_api/models/post_model

# === 关键词库配置 ===
HIGH_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords.json
BLACKLIST_1W_PATH=./safe_api/data/blacklist_1w.json

# === 服务配置 ===
# 前拦截服务端口
FRONT_API_PORT=8001
# 后拦截服务端口  
POST_API_PORT=8002
```

### 主 API 配置文件 (main_api_config.env)

```bash
# 主API 功能开关配置
# 用于决定是否启用各种功能

# === 功能开关 ===
ENABLE_FRONT_INTERCEPT=true
ENABLE_POST_INTERCEPT=true
ENABLE_RAG=true

# === Safe API 服务地址 ===
USE_LOCAL_INTERCEPT=false
FRONT_INTERCEPT_URL=http://localhost:8001/intercept
POST_INTERCEPT_URL=http://localhost:8002/intercept
INTERCEPT_TIMEOUT=5.0

# === RAG 系统配置 ===
RAG_SERVICE_URL=http://localhost:8000/retrieve
RAG_TOP_K=5
RAG_TIMEOUT=10.0

# === vLLM 配置 ===
VLLM_API_BASE=http://localhost:8000

# === 主API 服务配置 ===
HOST=0.0.0.0
PORT=8080
LOG_LEVEL=INFO

# === API 密钥配置 ===
ENABLE_MULTI_API_KEYS=true
API_KEYS_FILE=api_keys.json
```

### 使用配置文件启动

```bash
# 启动 Safe API (前拦截)
env $(cat safe_api_config.env | grep -v '^#' | xargs) python safe_api/front_intercept_api.py

# 启动 Safe API (后拦截)  
env $(cat safe_api_config.env | grep -v '^#' | xargs) python safe_api/post_intercept_api.py

# 启动主API
env $(cat main_api_config.env | grep -v '^#' | xargs) python main.py
```

---

## 🎛️ 命令行参数方式

### Safe API 命令行启动

```bash
# 前拦截服务
python safe_api/front_intercept_api.py \
  --bert-front-high 0.97 \
  --bert-front-low 0.00002 \
  --model-path ./safe_api/models/front_model \
  --keywords-path ./safe_api/data/high_sensitive_keywords.json \
  --blacklist-path ./safe_api/data/blacklist_1w.json \
  --port 8001

# 后拦截服务
python safe_api/post_intercept_api.py \
  --bert-post-threshold 0.5 \
  --model-path ./safe_api/models/post_model \
  --port 8002
```

### 主 API 命令行启动

```bash
python main.py \
  --enable-front-intercept \
  --enable-post-intercept \
  --enable-rag \
  --front-intercept-url http://localhost:8001/intercept \
  --post-intercept-url http://localhost:8002/intercept \
  --rag-service-url http://localhost:8000/retrieve \
  --vllm-api-base http://localhost:8000 \
  --port 8080
```

---

## 🧪 测试验证

### 1. 验证 Safe API 服务

```bash
# 测试前拦截
curl -X POST "http://localhost:8001/intercept" \
  -H "Content-Type: application/json" \
  -d '{"text": "placeholder_request_alpha"}'

# 测试后拦截
curl -X POST "http://localhost:8002/intercept" \
  -H "Content-Type: application/json" \
  -d '{"text": "这是一个测试回答"}'
```

### 2. 验证主 API 服务

```bash
# 测试完整流程
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "user", "content": "你好，今天天气怎么样？"}
    ]
  }'
```

---

## 🔄 不同场景的启动组合

### 场景1：完整功能 (前拦截 + 后拦截 + RAG)

```bash
# Safe API
BERT_FRONT_HIGH_THRESHOLD=0.97 BERT_FRONT_LOW_THRESHOLD=0.00002 python safe_api/front_intercept_api.py &
BERT_POST_THRESHOLD=0.5 python safe_api/post_intercept_api.py &

# 主API  
ENABLE_FRONT_INTERCEPT=true ENABLE_POST_INTERCEPT=true ENABLE_RAG=true python main.py
```

### 场景2：仅前拦截 + RAG

```bash
# Safe API
BERT_FRONT_HIGH_THRESHOLD=0.97 BERT_FRONT_LOW_THRESHOLD=0.00002 python safe_api/front_intercept_api.py &

# 主API
ENABLE_FRONT_INTERCEPT=true ENABLE_POST_INTERCEPT=false ENABLE_RAG=true python main.py
```

### 场景3：仅基础拦截（无RAG）

```bash
# Safe API
BERT_FRONT_HIGH_THRESHOLD=0.97 BERT_FRONT_LOW_THRESHOLD=0.00002 python safe_api/front_intercept_api.py &
BERT_POST_THRESHOLD=0.5 python safe_api/post_intercept_api.py &

# 主API
ENABLE_FRONT_INTERCEPT=true ENABLE_POST_INTERCEPT=true ENABLE_RAG=false python main.py
```

---

## 📊 配置参数说明

### Safe API 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BERT_FRONT_HIGH_THRESHOLD` | 0.97 | BERT前拦截高阈值，>=此值直接拦截 |
| `BERT_FRONT_LOW_THRESHOLD` | 0.00002 | BERT前拦截低阈值，<=此值直接通过 |  
| `BERT_POST_THRESHOLD` | 0.5 | BERT后拦截阈值 |
| `MODEL_FRONT_PATH` | ./safe_api/models/front_model | 前拦截模型路径 |
| `MODEL_POST_PATH` | ./safe_api/models/post_model | 后拦截模型路径 |

### 主 API 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_FRONT_INTERCEPT` | true | 是否启用前拦截功能 |
| `ENABLE_POST_INTERCEPT` | true | 是否启用后拦截功能 |
| `ENABLE_RAG` | false | 是否启用RAG系统 |
| `FRONT_INTERCEPT_URL` | http://localhost:8001/intercept | 前拦截服务地址 |
| `POST_INTERCEPT_URL` | http://localhost:8002/intercept | 后拦截服务地址 |
| `RAG_SERVICE_URL` | http://localhost:8000/retrieve | RAG检索服务地址 |

---

## 🚨 常见问题

### Q: Safe API 启动失败？
A: 检查模型文件和数据文件是否存在，确保路径配置正确。

### Q: 主API 连接不上 Safe API？
A: 确认 Safe API 服务已启动，检查端口和URL配置。

### Q: RAG 系统不工作？
A: 确认 `ENABLE_RAG=true` 且 RAG 服务正在运行。

### Q: 想要调整 BERT 阈值？
A: 修改 Safe API 的环境变量，重启 Safe API 服务即可。

---

**总结**: 现在配置更加清晰 - Safe API 管理具体拦截逻辑和阈值，主API 管理功能开关和服务协调！
