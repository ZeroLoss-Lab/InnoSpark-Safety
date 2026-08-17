# 主API服务启动说明

## 🎯 设计理念

这个启动脚本专门用于启动主API服务，连接到你已经独立运行的：
- Safe API服务（前后拦截BERT）
- RAG服务
- vLLM服务

**主启动脚本负责控制所有功能开关和阈值配置**

## 🚀 基本使用

### 默认启动
```bash
python start_main_api.py
```
- 连接到 `http://localhost:8001/intercept` (前拦截)
- 连接到 `http://localhost:8002/intercept` (后拦截)
- 连接到 `http://localhost:8000/retrieve` (RAG)
- 连接到 `http://localhost:8000` (vLLM)
- 主API运行在 `8003` 端口

## 🔧 功能控制

### 拦截功能开关
```bash
# 禁用前拦截
python start_main_api.py --no-front

# 禁用后拦截
python start_main_api.py --no-post

# 禁用所有拦截
python start_main_api.py --no-front --no-post
```

### RAG功能开关
```bash
# 禁用RAG
python start_main_api.py --no-rag

# 自定义RAG服务地址
python start_main_api.py --rag-url http://192.168.1.100:9000/retrieve
```

### API文档控制
```bash
# 启用API文档（默认禁用）
python start_main_api.py --enable-docs
```

## ⚙️ BERT阈值配置

### 前拦截双阈值
```bash
# 自定义前拦截阈值
python start_main_api.py \
  --bert-front-high 0.95 \
  --bert-front-low 0.0001
```

### 后拦截阈值
```bash
# 自定义后拦截阈值
python start_main_api.py --bert-post 0.6
```

### 完整阈值配置
```bash
python start_main_api.py \
  --bert-front-high 0.98 \
  --bert-front-low 0.00001 \
  --bert-post 0.4
```

## 🔗 外部服务地址配置

### 自定义服务地址
```bash
python start_main_api.py \
  --front-url http://192.168.1.100:8001/intercept \
  --post-url http://192.168.1.100:8002/intercept \
  --rag-url http://192.168.1.101:9000/retrieve \
  --vllm http://192.168.1.102:8000
```

### 分布式部署示例
```bash
python start_main_api.py \
  --port 80 \
  --front-url http://front-server:8001/intercept \
  --post-url http://post-server:8002/intercept \
  --rag-url http://rag-server:9000/retrieve \
  --vllm http://vllm-server:8000
```

## 📋 完整参数列表

```bash
python start_main_api.py [选项]

基本配置:
  --host HOST                    服务绑定地址 (默认: 0.0.0.0)
  --port PORT                    主API服务端口 (默认: 8003)
  --vllm URL                     vLLM服务地址 (默认: http://localhost:8000)

外部服务地址:
  --front-url URL                前拦截API地址 (默认: http://localhost:8001/intercept)
  --post-url URL                 后拦截API地址 (默认: http://localhost:8002/intercept)
  --rag-url URL                  RAG服务地址 (默认: http://localhost:8000/retrieve)

功能开关:
  --no-front                     禁用前拦截功能
  --no-post                      禁用后拦截功能
  --no-rag                       禁用RAG功能
  --enable-docs                  启用API文档访问（默认禁用）

BERT阈值配置:
  --bert-front-high FLOAT        BERT前拦截高阈值 (默认: 0.97)
  --bert-front-low FLOAT         BERT前拦截低阈值 (默认: 0.00002)
  --bert-post FLOAT              BERT后拦截阈值 (默认: 0.5)

RAG配置:
  --rag-top-k INT                RAG检索top-k数量 (默认: 5)
  --rag-timeout FLOAT            RAG服务超时时间 (默认: 10.0秒)

API密钥配置:
  --api-keys FILE                API密钥JSON文件路径 (默认: api_keys.json)
  --single-key KEY               使用单个API密钥（向后兼容）

超时配置:
  --intercept-timeout FLOAT      拦截服务超时时间 (默认: 10.0秒)
```

## 🎯 使用场景示例

### 场景1：开发测试
```bash
# 启用所有功能，包括文档
python start_main_api.py --enable-docs --port 8080
```

### 场景2：生产环境
```bash
# 高安全配置
python start_main_api.py \
  --port 443 \
  --bert-front-high 0.99 \
  --bert-post 0.3 \
  --intercept-timeout 5.0
```

### 场景3：性能优化
```bash
# 禁用拦截，仅使用RAG
python start_main_api.py \
  --no-front --no-post \
  --rag-timeout 5.0
```

### 场景4：纯语言模型
```bash
# 禁用所有增强功能
python start_main_api.py \
  --no-front --no-post --no-rag
```

### 场景5：自定义阈值
```bash
# 严格拦截配置
python start_main_api.py \
  --bert-front-high 0.95 \
  --bert-front-low 0.0001 \
  --bert-post 0.7
```

## 🔍 服务验证

### 检查服务状态
```bash
# 主API健康检查
curl http://localhost:8003/health

# 检查外部服务（你需要确保这些服务已启动）
curl http://localhost:8001/health  # 前拦截服务
curl http://localhost:8002/health  # 后拦截服务
curl http://localhost:8000/v1/models  # vLLM服务
```

### 测试API调用
```bash
curl -X POST 'http://localhost:8003/v1/chat/completions' \
  -H 'Authorization: Bearer sk-your-api-key-1' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen7b-in",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

### 测试拦截功能
```bash
# 测试前拦截（应该被拦截）
curl -X POST 'http://localhost:8003/v1/chat/completions' \
  -H 'Authorization: Bearer sk-your-api-key-1' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen7b-in",
    "messages": [
      {"role": "user", "content": "placeholder_request_alpha"}
    ]
  }'
```

### 测试RAG功能
```bash
# 测试RAG增强回答
curl -X POST 'http://localhost:8003/v1/chat/completions' \
  -H 'Authorization: Bearer sk-your-api-key-1' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen7b-in",
    "messages": [
      {"role": "user", "content": "中国有哪些重要的法律法规"}
    ]
  }'
```

## 🏗️ 服务架构

```
你的独立服务:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Safe API       │    │  RAG Service    │    │  vLLM Service   │
│  (8001/8002)    │    │  (8000/retrieve)│    │  (8000)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ↑                       ↑                       ↑
         └───────────────────────┼───────────────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │   主API服务 (8003)       │
                    │   start_main_api.py     │
                    └─────────────────────────┘
                                 ↑
                          用户请求
```

## 📝 启动顺序

1. **先启动你的独立服务**：
   ```bash
   # 终端1：启动Safe API
   cd safe_api
   python start_services.py
   
   # 终端2：启动RAG服务
   # (你的RAG服务启动命令)
   
   # 终端3：启动vLLM服务  
   # (你的vLLM服务启动命令)
   ```

2. **然后启动主API服务**：
   ```bash
   # 终端4：启动主API
   python start_main_api.py
   ```

## 🔧 阈值说明

### 前拦截双阈值机制
- **高阈值** (--bert-front-high): ≥此值直接拦截
- **低阈值** (--bert-front-low): >此值但<高阈值时进入中间判断
- **中间判断**: 检查次高敏关键词 → RAG系统

### 后拦截阈值
- **后拦截阈值** (--bert-post): ≥此值拦截输出

### 推荐配置
- **严格模式**: `--bert-front-high 0.99 --bert-post 0.3`
- **平衡模式**: `--bert-front-high 0.97 --bert-post 0.5` (默认)
- **宽松模式**: `--bert-front-high 0.95 --bert-post 0.7`

## 🛠️ 故障排除

### 1. 外部服务连接失败
- 确认Safe API服务已启动：`curl http://localhost:8001/health`
- 确认RAG服务已启动：`curl http://localhost:8000/retrieve`
- 确认vLLM服务已启动：`curl http://localhost:8000/v1/models`

### 2. 阈值不生效
- 检查环境变量是否正确设置
- 查看启动日志中的配置信息
- 确认Safe API服务使用了传递的阈值

### 3. RAG功能异常
- 检查RAG服务地址是否正确
- 验证RAG服务的接口格式
- 查看RAG超时设置

---

这个启动脚本让你完全控制主API的所有功能和配置，同时连接到你独立运行的服务！
