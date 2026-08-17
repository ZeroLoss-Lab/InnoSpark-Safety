# 统一安全响应消息配置指南

## 📋 概述

系统现在支持统一配置所有拦截场景的安全响应消息，通过一个环境变量控制所有拦截器的拒绝话术。

## 🔧 配置参数

### 环境变量
```bash
SAFETY_RESPONSE_MESSAGE="您的自定义安全响应消息"
```

### 默认消息
```
根据相关法律法规以及道德伦理规范，我无法提供关于这个问题的回答，建议换一个话题。
```

## 📍 影响范围

统一的安全响应消息会应用于以下所有拦截场景：

### 1. 前拦截触发
- 高敏感关键词匹配
- BERT前拦截双阈值判断
- 次高敏感关键词匹配

### 2. 后拦截触发
- BERT后拦截判断为不安全

### 3. 系统异常
- 拦截服务调用失败
- 模型推理异常
- 网络超时等错误

### 4. 流式响应拦截
- 流式输出后拦截触发

## 🚀 使用方法

### 方法1: 环境变量设置

#### 临时设置（当前会话）
```bash
export SAFETY_RESPONSE_MESSAGE="抱歉，根据安全策略，我无法回答此类问题。请尝试其他话题。"
```

#### 永久设置（添加到配置文件）
```bash
# 编辑 .env 文件
echo 'SAFETY_RESPONSE_MESSAGE="抱歉，根据安全策略，我无法回答此类问题。请尝试其他话题。"' >> .env
```

### 方法2: 启动脚本中设置

#### 修改 Safe API 启动脚本
```bash
# 编辑 start_safe_api.sh
export SAFETY_RESPONSE_MESSAGE="您的自定义消息"
```

#### 修改主 API 启动脚本
```bash
# 编辑 start_main_api.sh  
export SAFETY_RESPONSE_MESSAGE="您的自定义消息"
```

### 方法3: 命令行直接设置
```bash
# 启动时设置
SAFETY_RESPONSE_MESSAGE="您的自定义消息" ./start_safe_api.sh
SAFETY_RESPONSE_MESSAGE="您的自定义消息" ./start_main_api.sh
```

## 💡 消息模板建议

### 1. 基础模板
```
根据相关法律法规以及道德伦理规范，我无法提供关于这个问题的回答，建议换一个话题。
```

### 2. 简洁模板
```
抱歉，我无法回答此类问题，请尝试其他话题。
```

### 3. 详细模板
```
为了确保内容安全和合规，我无法提供关于此问题的信息。请您理解并尝试询问其他内容。
```

### 4. 引导模板
```
根据安全策略，我无法回答此问题。如需帮助，请咨询相关专业机构或尝试其他话题。
```

### 5. 多语言模板
```
Sorry, I cannot provide information on this topic due to safety policies. Please try asking about something else. / 抱歉，出于安全考虑，我无法回答此类问题，请尝试其他话题。
```

## 🧪 测试验证

### 1. 测试配置是否生效
```bash
# 设置自定义消息
export SAFETY_RESPONSE_MESSAGE="这是测试消息"

# 启动服务
./start_safe_api.sh
./start_main_api.sh

# 测试拦截
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "user", "content": "placeholder_request_alpha"}
    ]
  }'
```

### 2. 验证响应内容
响应中的 `content` 字段应该包含您设置的自定义消息：
```json
{
  "choices": [{
    "message": {
      "content": "这是测试消息"
    }
  }]
}
```

## 📊 配置示例

### 完整的环境变量配置示例
```bash
# .env 文件示例

# === 统一安全响应消息 ===
SAFETY_RESPONSE_MESSAGE="根据相关法律法规以及道德伦理规范，我无法提供关于这个问题的回答，建议换一个话题。"

# === Safe API 配置 ===
BERT_FRONT_HIGH_THRESHOLD=0.97
BERT_FRONT_LOW_THRESHOLD=0.00002
BERT_POST_THRESHOLD=0.5

# === 主 API 功能开关 ===
ENABLE_FRONT_INTERCEPT=true
ENABLE_POST_INTERCEPT=true
ENABLE_RAG=true

# === 服务地址 ===
FRONT_INTERCEPT_URL=http://localhost:8001/intercept
POST_INTERCEPT_URL=http://localhost:8002/intercept
```

## 🔄 动态更新

### 运行时更新（需要重启服务）
1. 修改环境变量
2. 重启 Safe API 服务：`./stop_safe_api.sh && ./start_safe_api.sh`
3. 重启主 API 服务：重启 `main.py`

### 不停机更新（高级用法）
如需不停机更新消息，可以考虑：
1. 使用配置管理系统
2. 实现配置热重载功能
3. 使用负载均衡进行滚动更新

## ⚠️ 注意事项

### 1. 消息长度限制
- 建议消息长度不超过200字符
- 过长的消息可能影响用户体验

### 2. 内容合规性
- 确保自定义消息符合相关法规要求
- 避免使用可能引起误解的表述

### 3. 多语言支持
- 如需多语言支持，建议在消息中包含主要语言
- 可以根据用户语言偏好动态选择消息

### 4. 日志记录
- 系统会记录实际使用的安全响应消息
- 便于审计和监控

## 🔗 相关文档

- [STARTUP_GUIDE_UNIFIED.md](./STARTUP_GUIDE_UNIFIED.md) - 统一启动指南
- [config.py](./config.py) - 配置文件说明
- [FIX_NAMEERROR.md](./FIX_NAMEERROR.md) - 错误修复说明
