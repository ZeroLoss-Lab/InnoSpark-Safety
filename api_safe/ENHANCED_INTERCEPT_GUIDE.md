# 增强版拦截器使用指南

## 概述

增强版拦截器实现了完整的多层安全拦截逻辑，集成了RAG（检索增强生成）系统，提供更智能、更安全的内容过滤和回答生成。

## 拦截逻辑流程

```
用户输入 → 前拦截器
    ↓
1. 高敏感关键词检查
    ├─ 匹配 → 直接拦截 ❌
    └─ 未匹配 → 继续
        ↓
2. BERT双阈值判断
    ├─ flag=0 (高阈值) → 直接拦截 ❌
    ├─ flag=1 (低阈值) → 直接通过 → 正常模型回答 ✅
    └─ flag=2 (中间阈值) → 继续检查
        ↓
3. 次高敏感关键词检查
    ├─ 匹配 → 拦截 ❌
    └─ 未匹配 → 继续
        ↓
4. RAG系统处理（如果启用）
    ├─ 检索成功 → RAG增强回答 🔍
    └─ 检索失败 → 默认通过 ✅
        ↓
模型回答 → 后拦截器
    ├─ BERT判断不安全 → 拦截 ❌
    └─ BERT判断安全 → 输出结果 ✅
```

## 核心特性

### 1. 多层安全防护
- **第一层**: 高敏感关键词精确匹配
- **第二层**: BERT双阈值智能判断
- **第三层**: 次高敏感关键词补充检查
- **第四层**: RAG系统安全增强
- **第五层**: 后拦截BERT最终检查

### 2. RAG系统集成
- 自动调用外部RAG检索服务
- JSON结果智能转换为文本
- 安全合规的prompt模板
- 权威信息源引导回答

### 3. 灵活配置
- 可独立启用/禁用各个拦截层
- 可调节BERT阈值参数
- 支持本地和远程拦截模式
- 支持自定义关键词库

## 快速开始

### 1. 配置环境

```bash
# 复制配置文件
cp config_enhanced_intercept.env .env

# 编辑配置文件
vim .env
```

### 2. 关键配置项

```bash
# 启用拦截器
ENABLE_FRONT_INTERCEPT=true
ENABLE_POST_INTERCEPT=true
USE_LOCAL_INTERCEPT=true

# 启用RAG系统
ENABLE_RAG=true
RAG_SERVICE_URL=http://localhost:8000/retrieve
RAG_TOP_K=5

# BERT双阈值设置
BERT_FRONT_HIGH_THRESHOLD=0.97
BERT_FRONT_LOW_THRESHOLD=0.00002
BERT_POST_THRESHOLD=0.5

# 关键词库路径
HIGH_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords.json
MEDIUM_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords-2.json
```

### 3. 启动服务

```bash
# 启动主API服务
python main.py

# 或使用配置文件启动
python main.py --enable-front-intercept --enable-post-intercept
```

### 4. 测试验证

```bash
# 运行完整测试
python test_enhanced_intercept.py

# 运行演示示例
python demo_enhanced_intercept.py
```

## 详细配置说明

### BERT双阈值配置

```bash
# 高阈值：>=此值直接拦截（建议0.95-0.99）
BERT_FRONT_HIGH_THRESHOLD=0.97

# 低阈值：>此值但<高阈值时进入中间判断（建议1e-5到1e-4）
BERT_FRONT_LOW_THRESHOLD=0.00002

# 后拦截阈值：>=此值拦截输出（建议0.3-0.7）
BERT_POST_THRESHOLD=0.5
```

### RAG系统配置

```bash
# RAG检索服务地址
RAG_SERVICE_URL=http://localhost:8000/retrieve

# 检索返回的结果数量
RAG_TOP_K=5

# RAG服务超时时间
RAG_TIMEOUT=10.0
```

### 关键词库配置

```bash
# 高敏感关键词（第一层拦截）
HIGH_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords.json

# 次高敏感关键词（第三层拦截）  
MEDIUM_SENSITIVE_KEYWORDS_PATH=./safe_api/data/high_sensitive_keywords-2.json

# 1w黑名单（用于BERT判断触发条件）
BLACKLIST_1W_PATH=./safe_api/data/blacklist_1w.json
```

## API使用示例

### 基本调用

```python
import requests

headers = {
    "Authorization": "Bearer your_api_key",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen7b-in",
    "messages": [
        {"role": "user", "content": "中国有哪些重要的法律法规？"}
    ],
    "temperature": 0.7,
    "max_tokens": 1000
}

response = requests.post(
    "http://localhost:8001/v1/chat/completions",
    headers=headers,
    json=payload
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

### 响应结果说明

```json
{
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "基于检索的权威资料..."
        },
        "finish_reason": "stop"  // 或 "content_filter" 表示被拦截
    }],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "total_tokens": 300
    }
}
```

## 拦截结果类型

### 1. 正常通过
```json
{
    "finish_reason": "stop",
    "content": "正常的回答内容..."
}
```

### 2. 安全拦截
```json
{
    "finish_reason": "content_filter", 
    "content": "根据相关法律法规，我无法提供关于这个问题的回答，建议换一个话题。"
}
```

### 3. RAG增强回答
```json
{
    "finish_reason": "stop",
    "content": "根据检索的权威资料：[具体的合规回答]"
}
```

## 监控和日志

### 日志文件
- `logs/api.log`: 主要API日志
- `logs/user_requests.log`: 用户请求详细日志

### 关键日志信息
```
INFO - Request xxx: 执行前拦截检查
INFO - 前拦截触发 - 匹配到高敏感关键词: ['敏感词']
INFO - BERT双阈值判断: flag=2, 问题句子数=0
INFO - 未匹配次高敏关键词，启动RAG系统
INFO - RAG检索成功，返回RAG增强结果
INFO - Request xxx: 已应用RAG增强prompt
```

## 性能优化建议

### 1. 本地模式优化
```bash
# 使用本地集成模式，减少网络开销
USE_LOCAL_INTERCEPT=true

# 合理设置worker数量
WORKERS=2

# 优化超时设置
INTERCEPT_TIMEOUT=3.0
RAG_TIMEOUT=8.0
```

### 2. 关键词库优化
- 定期更新关键词库
- 移除重复和过时的关键词
- 按敏感度合理分类

### 3. BERT阈值调优
- 根据实际业务场景调整阈值
- 监控拦截率和误报率
- 定期评估模型效果

## 故障排除

### 1. 拦截器初始化失败
```bash
# 检查模型文件是否存在
ls -la ./safe_api/models/

# 检查关键词文件是否存在
ls -la ./safe_api/data/

# 检查依赖是否安装
pip install torch transformers aiohttp
```

### 2. RAG服务连接失败
```bash
# 检查RAG服务是否启动
curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query": "测试", "top_k": 5}'

# 检查网络连接
ping localhost

# 检查端口是否开放
netstat -an | grep 8000
```

### 3. 拦截效果不佳
- 检查关键词库是否完整
- 调整BERT阈值参数
- 查看详细日志分析原因
- 更新模型文件

## 安全建议

1. **定期更新**: 及时更新关键词库和模型文件
2. **监控日志**: 定期检查拦截日志，发现新的风险模式
3. **阈值调优**: 根据业务需求调整拦截阈值
4. **备份配置**: 保留有效的配置文件备份
5. **权限控制**: 限制模型文件和配置文件的访问权限

## 技术支持

如遇到问题，请查看：
1. 日志文件中的错误信息
2. 运行测试脚本的输出结果
3. 配置文件的参数设置
4. RAG服务的运行状态

---

**注意**: 本系统设计用于内容安全防护，请根据实际业务需求和法律法规要求进行配置和使用。
