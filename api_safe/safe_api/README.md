# 安全拦截API系统

这是一个分布式的安全内容拦截系统，将前拦截和后拦截分别部署为独立的API服务，支持并行调用以提高性能。

## 系统架构

```
Client
  ├── 前拦截API (Port 8001)
  │   ├── 高敏感词直接拦截
  │   ├── 1w黑名单检查
  │   └── BERT前拦截模型
  └── 后拦截API (Port 8002)
      └── BERT后拦截模型
```

## 功能特性

### 前拦截API (`front_intercept_api.py`)
- **高敏感词直接拦截**: 匹配到高敏感关键词立即返回安全响应
- **1w黑名单检查**: 检查1w黑名单，如匹配则使用BERT模型判断
- **BERT前拦截**: 对匹配黑名单的内容进行深度学习安全判断
- **标准部署**: 使用标准BERT模型部署，保证模型精度

### 后拦截API (`post_intercept_api.py`)
- **BERT后拦截**: 对文本内容进行最终的安全性判断
- **标准部署**: 使用标准BERT模型部署，保证模型精度
- **独立部署**: 可以独立扩缩容

## 安装和部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备模型和数据文件

确保以下文件和目录存在：

```
safe_api/
├── models/
│   ├── front_model/          # 前拦截BERT模型
│   └── post_model/           # 后拦截BERT模型
├── data/
│   ├── blacklist_1w.json     # 1w黑名单
│   └── high_sensitive_keywords.json  # 高敏感关键词
```

### 3. 环境变量配置

可以通过环境变量配置模型和数据文件路径：

```bash
# 前拦截API配置
export MODEL_FRONT_PATH="./models/front_model"
export BLACKLIST_1W_PATH="./data/blacklist_1w.json"
export HIGH_SENSITIVE_KEYWORDS_PATH="./data/high_sensitive_keywords.json"

# 后拦截API配置
export MODEL_POST_PATH="./models/post_model"
```

### 4. 启动服务

#### 启动前拦截API (端口8001)
```bash
python front_intercept_api.py
```

#### 启动后拦截API (端口8002)
```bash
python post_intercept_api.py
```

#### 使用uvicorn启动 (推荐生产环境)
```bash
# 前拦截API
uvicorn front_intercept_api:app --host 0.0.0.0 --port 8001 --workers 1

# 后拦截API
uvicorn post_intercept_api:app --host 0.0.0.0 --port 8002 --workers 1
```

## API接口文档

### 前拦截API (http://localhost:8001)

#### POST /intercept
检查文本内容的安全性（前拦截）

**请求体:**
```json
{
  "text": "要检查的文本内容"
}
```

**响应:**
```json
{
  "is_safe": true,
  "reason": "未匹配任何敏感关键词",
  "matched_keywords": null,
  "bert_results": null,
  "safety_response": null
}
```

#### GET /health
健康检查

#### GET /info
获取服务信息

### 后拦截API (http://localhost:8002)

#### POST /intercept
对文本内容进行后拦截检查

**请求体:**
```json
{
  "text": "要检查的文本内容"
}
```

**响应:**
```json
{
  "is_safe": true,
  "score": 0.9876,
  "reason": "BERT后拦截判断为安全，置信度: 0.9876",
  "safety_response": null
}
```

## 模型部署策略

### 1. 标准BERT部署
- 使用标准的BERT模型加载，不进行量化
- 保证模型的完整精度和性能
- 支持GPU和CPU环境自动切换

### 2. 设备管理
- 自动检测CUDA可用性
- GPU环境使用CUDA加速
- CPU环境使用标准加载

## 性能优化

### 1. 并行调用
客户端同时调用前拦截和后拦截API，理论上可以获得接近2倍的性能提升。

### 2. 缓存策略
可以在生产环境中添加Redis缓存：
- 缓存高频查询结果
- 缓存BERT模型输出
- 缓存正则表达式匹配结果

### 3. 负载均衡
可以部署多个实例并使用负载均衡器：
```bash
# 启动多个前拦截实例
uvicorn front_intercept_api:app --port 8001 &
uvicorn front_intercept_api:app --port 8011 &
uvicorn front_intercept_api:app --port 8021 &

# 启动多个后拦截实例  
uvicorn post_intercept_api:app --port 8002 &
uvicorn post_intercept_api:app --port 8012 &
uvicorn post_intercept_api:app --port 8022 &
```

## 生产环境部署

### Docker部署

创建 `Dockerfile.front`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY front_intercept_api.py .
COPY models/ models/
COPY data/ data/

CMD ["uvicorn", "front_intercept_api:app", "--host", "0.0.0.0", "--port", "8001"]
```

创建 `Dockerfile.post`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY post_intercept_api.py .
COPY models/ models/

CMD ["uvicorn", "post_intercept_api:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  front-intercept:
    build:
      context: .
      dockerfile: Dockerfile.front
    ports:
      - "8001:8001"
    environment:
      - MODEL_FRONT_PATH=/app/models/front_model
      - BLACKLIST_PATH=/app/data/blacklist.json
      - BLACKLIST_1W_PATH=/app/data/blacklist_1w.json
      - HIGH_SENSITIVE_KEYWORDS_PATH=/app/data/high_sensitive_keywords.json

  post-intercept:
    build:
      context: .
      dockerfile: Dockerfile.post
    ports:
      - "8002:8002"
    environment:
      - MODEL_POST_PATH=/app/models/post_model
```

## 监控和日志

### 日志配置
系统使用Python标准logging模块，可以通过以下方式配置：

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 监控指标
建议监控以下指标：
- API响应时间
- 内存使用情况
- GPU利用率（如果使用GPU）
- 错误率
- 吞吐量

## 故障排除

### 常见问题

1. **模型加载失败**
   - 检查模型路径是否正确
   - 确认模型文件完整性
   - 检查磁盘空间

2. **内存不足**
   - 减少batch_size
   - 使用CPU而非GPU
   - 考虑使用更小的模型

3. **API连接失败**
   - 检查端口是否被占用
   - 确认防火墙设置
   - 检查网络连接

4. **性能问题**
   - 使用GPU加速
   - 增加并发实例
   - 添加缓存层

## 许可证

本项目遵循MIT许可证。
