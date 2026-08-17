# Safe API阈值配置说明

## 概述

Safe API现在支持通过环境变量配置BERT模型的阈值，这使得主API能够动态控制前后拦截的敏感度。

## 环境变量配置

### BERT阈值环境变量

| 环境变量名 | 描述 | 默认值 | 示例 |
|-----------|------|-------|------|
| `BERT_FRONT_HIGH_THRESHOLD` | 前拦截高阈值（超过此值直接拦截） | 0.97 | 0.95 |
| `BERT_FRONT_LOW_THRESHOLD` | 前拦截低阈值（低于此值直接通过） | 0.00002 | 0.0001 |
| `BERT_POST_THRESHOLD` | 后拦截阈值（超过此值拦截响应） | 0.5 | 0.6 |

### 模型路径环境变量

| 环境变量名 | 描述 | 默认值 |
|-----------|------|-------|
| `MODEL_FRONT_PATH` | 前拦截BERT模型路径 | ./models/front_model |
| `MODEL_POST_PATH` | 后拦截BERT模型路径 | ./models/post_model |

## 使用方法

### 1. 通过start_main_api.py自动配置

```bash
# start_main_api.py会自动设置这些环境变量并传递给Safe API
python start_main_api.py \
  --bert-front-high 0.95 \
  --bert-front-low 0.0001 \
  --bert-post 0.6 \
  --front-url http://localhost:8001 \
  --post-url http://localhost:8002
```

### 2. 手动启动Safe API服务

```bash
# 设置环境变量
export BERT_FRONT_HIGH_THRESHOLD=0.95
export BERT_FRONT_LOW_THRESHOLD=0.0001
export BERT_POST_THRESHOLD=0.6

# 启动前拦截API
cd safe_api
python -m uvicorn front_intercept_api:app --host 0.0.0.0 --port 8001

# 启动后拦截API  
python -m uvicorn post_intercept_api:app --host 0.0.0.0 --port 8002
```

### 3. 使用Safe API专用启动脚本

```bash
# 使用带阈值配置的启动脚本
cd safe_api
python start_with_thresholds.py \
  --bert-front-high 0.95 \
  --bert-front-low 0.0001 \
  --bert-post 0.6
```

## 阈值说明

### 前拦截双阈值机制

前拦截使用双阈值机制：

1. **高阈值 (BERT_FRONT_HIGH_THRESHOLD)**：
   - 如果BERT分数 ≥ 高阈值 → 直接拦截
   - 建议范围：0.9 - 0.99
   - 数值越高，拦截越严格

2. **低阈值 (BERT_FRONT_LOW_THRESHOLD)**：
   - 如果BERT分数 ≤ 低阈值 → 直接通过
   - 建议范围：0.00001 - 0.001
   - 数值越低，通过越容易

3. **中间状态**：
   - 如果 低阈值 < BERT分数 < 高阈值 → 进入二次检查
   - 会检查中等敏感关键词
   - 如果未匹配关键词，可能触发RAG系统

### 后拦截单阈值机制

后拦截使用单阈值机制：

1. **后拦截阈值 (BERT_POST_THRESHOLD)**：
   - 如果BERT分数 ≥ 后拦截阈值 → 拦截响应
   - 如果BERT分数 < 后拦截阈值 → 允许输出
   - 建议范围：0.3 - 0.8
   - 数值越高，拦截越宽松

## 阈值调优建议

### 保守配置（严格拦截）
```bash
BERT_FRONT_HIGH_THRESHOLD=0.90   # 较低的高阈值，更容易拦截
BERT_FRONT_LOW_THRESHOLD=0.0001  # 较高的低阈值，更难直接通过
BERT_POST_THRESHOLD=0.3          # 较低的后拦截阈值，更严格
```

### 平衡配置（推荐）
```bash
BERT_FRONT_HIGH_THRESHOLD=0.97   # 默认配置
BERT_FRONT_LOW_THRESHOLD=0.00002 # 默认配置
BERT_POST_THRESHOLD=0.5          # 默认配置
```

### 宽松配置（更多通过）
```bash
BERT_FRONT_HIGH_THRESHOLD=0.99   # 较高的高阈值，更难拦截
BERT_FRONT_LOW_THRESHOLD=0.001   # 较低的低阈值，更容易直接通过
BERT_POST_THRESHOLD=0.8          # 较高的后拦截阈值，更宽松
```

## 测试验证

### 1. 测试Safe API阈值配置
```bash
python test_safe_api_thresholds.py
```

### 2. 完整集成测试
```bash
python test_complete_integration.py
```

### 3. 手动验证阈值效果
```bash
# 测试前拦截
curl -X POST "http://localhost:8001/intercept" \
  -H "Content-Type: application/json" \
  -d '{"text": "测试文本"}'

# 测试后拦截
curl -X POST "http://localhost:8002/intercept" \
  -H "Content-Type: application/json" \
  -d '{"text": "测试响应"}'
```

## 注意事项

1. **环境变量优先级**：
   - 函数参数 > 环境变量 > 默认值

2. **阈值范围**：
   - 所有阈值应在 0.0 - 1.0 范围内
   - 前拦截高阈值应大于低阈值

3. **性能考虑**：
   - 较低的阈值可能导致更多误拦截
   - 较高的阈值可能导致更多漏检

4. **模型依赖**：
   - 需要确保BERT模型文件存在且可访问
   - 模型路径可通过环境变量配置

5. **日志监控**：
   - 建议监控拦截日志以调优阈值
   - 关注误拦截和漏检情况

## 故障排除

### 常见问题

1. **阈值不生效**：
   - 检查环境变量是否正确设置
   - 确认Safe API服务重启后生效

2. **服务启动失败**：
   - 检查模型文件路径是否正确
   - 确认端口未被占用

3. **拦截效果异常**：
   - 验证阈值设置是否合理
   - 检查BERT模型是否加载成功

### 调试命令

```bash
# 检查环境变量
env | grep BERT

# 检查Safe API服务状态
curl http://localhost:8001/health
curl http://localhost:8002/health

# 查看服务日志
tail -f logs/api.log
```

## 集成流程

1. **主API启动时**：
   - `start_main_api.py` 设置环境变量
   - 环境变量包含用户指定的BERT阈值

2. **Safe API启动时**：
   - 读取环境变量中的阈值配置
   - 如果环境变量不存在，使用默认值

3. **拦截处理时**：
   - 使用配置的阈值进行BERT判断
   - 根据阈值结果决定拦截或通过

4. **动态调整**：
   - 修改环境变量后重启Safe API服务
   - 新的阈值配置立即生效
