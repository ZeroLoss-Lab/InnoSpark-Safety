# 内容拦截功能使用指南

## 功能概述

API现在支持智能内容拦截功能，包括：

- **前拦截**：检查用户输入，在发送给LLM之前进行安全过滤
- **后拦截**：检查LLM输出，在返回给用户之前进行安全过滤

拦截功能支持两种运行模式：
1. **本地集成模式**：直接在主API中加载拦截模型（推荐）
2. **远程API模式**：调用独立的拦截服务API

## 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# ===================
# 内容拦截配置
# ===================
# 是否启用前拦截（用户输入检查）
ENABLE_FRONT_INTERCEPT=true
# 是否启用后拦截（模型输出检查）
ENABLE_POST_INTERCEPT=true

# 拦截API地址（当use_local_intercept=false时使用）
FRONT_INTERCEPT_URL=http://localhost:8001/intercept
POST_INTERCEPT_URL=http://localhost:8002/intercept

# 是否使用本地集成模式（true=直接集成到主API，false=调用独立拦截API）
USE_LOCAL_INTERCEPT=true

# 拦截模型路径配置（本地集成模式）
MODEL_FRONT_PATH=./safe_api/models/front_model
MODEL_POST_PATH=./safe_api/models/post_model
BLACKLIST_1W_PATH=./safe_api/data/blacklist_1w.json
HIGH_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords.json

# 拦截API超时时间（秒）
INTERCEPT_TIMEOUT=5.0
```

### 配置选项详解

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ENABLE_FRONT_INTERCEPT` | bool | false | 是否启用前拦截 |
| `ENABLE_POST_INTERCEPT` | bool | false | 是否启用后拦截 |
| `USE_LOCAL_INTERCEPT` | bool | true | 是否使用本地集成模式 |
| `MODEL_FRONT_PATH` | str | ./safe_api/models/front_model | 前拦截模型路径 |
| `MODEL_POST_PATH` | str | ./safe_api/models/post_model | 后拦截模型路径 |
| `BLACKLIST_1W_PATH` | str | ./safe_api/data/blacklist_1w.json | 1w黑名单路径 |
| `HIGH_SENSITIVE_KEYWORDS_PATH` | str | ./safe_api/data/high_sensitive_keywords.json | 高敏感词路径 |
| `INTERCEPT_TIMEOUT` | float | 5.0 | 拦截API超时时间 |

## 安装依赖

更新了requirements.txt，新增了以下依赖：

```bash
# 内容拦截依赖
transformers>=4.30.0
torch>=2.0.0
aiohttp>=3.8.0
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. 本地集成模式（推荐）

**优点：**
- 延迟更低
- 无需部署独立服务
- 资源利用更高效

**配置步骤：**

1. 设置环境变量：
   ```bash
   USE_LOCAL_INTERCEPT=true
   ENABLE_FRONT_INTERCEPT=true
   ENABLE_POST_INTERCEPT=true
   ```

2. 确保模型文件路径正确：
   ```bash
   MODEL_FRONT_PATH=./safe_api/models/front_model
   MODEL_POST_PATH=./safe_api/models/post_model
   ```

3. 确保数据文件存在：
   ```bash
   BLACKLIST_1W_PATH=./safe_api/data/blacklist_1w.json
   HIGH_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords.json
   ```

4. 启动API：
   ```bash
   python main.py
   ```

### 2. 远程API模式

**优点：**
- 服务解耦
- 可独立扩展拦截服务
- 便于管理和维护

**配置步骤：**

1. 设置环境变量：
   ```bash
   USE_LOCAL_INTERCEPT=false
   ENABLE_FRONT_INTERCEPT=true
   ENABLE_POST_INTERCEPT=true
   FRONT_INTERCEPT_URL=http://localhost:8001/intercept
   POST_INTERCEPT_URL=http://localhost:8002/intercept
   ```

2. 启动独立的拦截服务：
   ```bash
   # 前拦截服务
   cd safe_api
   python front_intercept_api.py
   
   # 后拦截服务
   python post_intercept_api.py
   ```

3. 启动主API：
   ```bash
   python main.py
   ```

## 拦截工作流程

### 前拦截流程

1. 用户发送消息到 `/v1/chat/completions`
2. 提取用户消息内容
3. 如果启用前拦截，检查用户输入：
   - 检查高敏感关键词
   - 检查1w黑名单
   - 使用BERT模型判断
4. 如果触发拦截，返回安全响应：
   ```json
   {
     "id": "chatcmpl-...",
     "choices": [{
       "message": {
         "content": "根据相关法律法规，我无法提供关于这个问题的回答，建议换一个话题。"
       },
       "finish_reason": "content_filter"
     }],
     "safety_filter": {
       "triggered": true,
       "reason": "前拦截触发: 匹配到高敏感关键词"
     }
   }
   ```
5. 如果通过前拦截，继续LLM处理

### 后拦截流程

1. LLM生成响应
2. 如果启用后拦截，检查LLM输出：
   - 使用BERT模型判断内容安全性
3. 如果触发拦截，替换为安全响应
4. 如果通过后拦截，返回原始LLM响应

### 流式响应处理

对于流式响应（`stream=true`），后拦截会：
1. 收集完整的流式响应内容
2. 对完整内容进行安全检查
3. 如果触发拦截，替换整个流式响应为安全内容
4. 如果通过检查，返回原始流式响应

## 日志记录

拦截触发时会记录详细日志：

- 请求ID
- 用户ID
- 拦截类型（前拦截/后拦截）
- 拦截原因
- 匹配到的关键词
- 置信度分数

## 性能考虑

### 本地集成模式
- 首次启动会加载模型，需要一定时间
- 内存占用增加（模型大小）
- GPU使用率增加（如果有GPU）

### 远程API模式
- 网络延迟
- 需要额外的服务资源
- 更好的资源隔离

## 故障处理

### 常见问题

1. **模型加载失败**
   - 检查模型路径是否正确
   - 确保有足够的内存
   - 查看启动日志中的错误信息

2. **数据文件缺失**
   - 检查 `blacklist_1w.json` 和 `high_sensitive_keywords.json` 是否存在
   - 确保文件格式正确

3. **远程API不可用**
   - 检查拦截服务是否启动
   - 验证网络连接
   - 检查防火墙设置

### 安全降级

当拦截功能出现异常时：
- **前拦截异常**：记录错误但继续处理请求
- **后拦截异常**：返回安全响应以确保安全

## 监控和调试

### 启用拦截日志

拦截操作会在主日志中记录：

```
2024-01-01 12:00:00 INFO Request abc-123: 执行前拦截检查
2024-01-01 12:00:01 INFO Request abc-123: 前拦截触发 - 匹配到高敏感关键词
```

### 健康检查

新增的拦截器会在启动时初始化，可通过日志确认状态：

```
2024-01-01 12:00:00 INFO 前拦截器已启用并初始化
2024-01-01 12:00:00 INFO 后拦截器已启用并初始化
```

## 示例配置文件

完整的生产环境配置示例：

```bash
# 基础配置
VLLM_API_BASE=http://localhost:8000
HOST=0.0.0.0
PORT=8001

# 拦截配置
ENABLE_FRONT_INTERCEPT=true
ENABLE_POST_INTERCEPT=true
USE_LOCAL_INTERCEPT=true
MODEL_FRONT_PATH=/path/to/front_model
MODEL_POST_PATH=/path/to/post_model
BLACKLIST_1W_PATH=/path/to/blacklist_1w.json
HIGH_SENSITIVE_KEYWORDS_PATH=/path/to/high_sensitive_keywords.json
INTERCEPT_TIMEOUT=5.0

# 安全配置
API_KEY=your-secure-api-key
ENABLE_DOCS=false
DOCS_REQUIRE_AUTH=true
```

通过以上配置，您的API将具备强大的内容安全拦截能力，确保用户输入和模型输出都符合安全规范。
