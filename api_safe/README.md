# vLLM Proxy API

一个企业级的OpenAI兼容vLLM转发API服务，支持智能对话管理、流式输出和完整用户追踪。

## ✨ 核心特性

- 🔄 **智能转发**: 将请求转发到vLLM API，支持OpenAI完全兼容
- 🗣️ **双模式对话**: 默认单轮对话 + 可选多轮上下文管理
- 🌊 **流式输出**: 完美支持流式和非流式响应
- 👥 **用户管理**: 基于API Key的用户识别和统计
- 💬 **Session管理**: 基于Session ID的对话会话管理
- 📊 **完整日志**: 详细记录用户请求、响应和系统状态
- ⚡ **高并发**: 支持并发调用，QPS 40+
- 🔐 **安全认证**: API密钥验证和用户隔离
- 📈 **监控统计**: 用户和会话的详细统计信息

## 🚀 快速部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key（可选）

如果需要启用API鉴权，请设置环境变量：

```bash
# 方式1：环境变量
export API_KEY=your-secret-api-key-here

# 方式2：创建.env文件
cp config_example.env .env
# 编辑.env文件，设置API_KEY值
```

### 3. 启动服务

```bash
python run.py --vllm-api "your-vllm-api-url" --port 8001
```

**完整启动参数**：
```bash
python run.py \
  --vllm-api "https://your-vllm-server.com/v1" \
  --port 8001 \
  --api-key "your-secret-api-key" \
  --log-level INFO
```

### 4. 验证部署

访问API文档：http://localhost:8001/docs  
健康检查：http://localhost:8001/health

**测试API鉴权**：
```bash
# 无鉴权测试
curl http://localhost:8001/health

# 有鉴权测试
curl -H "Authorization: Bearer your-api-key-here" \
     http://localhost:8001/health
```

## 📖 API 使用指南

### 认证方式

#### API Key鉴权（可选）
如果在配置文件中设置了`API_KEY`，则所有请求都需要在Header中提供API Key：
```bash
Authorization: Bearer your-api-key-here
```

#### 用户ID识别
从版本更新后，支持两种用户识别方式：

1. **显式用户ID**（推荐）：在请求体中直接指定`user_id`参数
2. **向后兼容**：使用`user`字段，或者对于匿名用户使用`"anonymous"`

```json
{
  "model": "default",
  "messages": [...],
  "user_id": "user123",  // 新增：明确的用户ID
  "session_id": "session001"  // 可选：会话ID
}
```

### 完整的API调用示例

```bash
# 使用用户ID参数的聊天请求
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "default",
    "messages": [
      {
        "role": "user",
        "content": "你好，我是用户123"
      }
    ],
    "user_id": "user123",
    "session_id": "session001",
    "enable_context": true,
    "max_context_turns": 5,
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

## 🐍 Python API调用

支持多种方式调用API：标准OpenAI客户端（单轮对话）、requests库（支持所有功能）、以及专用客户端。

### 方式1：使用专用客户端（推荐）

```python
# 使用项目中的 VLLMProxyClient（支持所有功能）
from client_example import VLLMProxyClient

# 创建客户端
client = VLLMProxyClient(
    base_url="http://localhost:8001",
    api_key="your-api-key-here"  # 如果启用了API鉴权
)

# 单轮对话 - 流式输出
response = client.chat_completion(
    messages=[{"role": "user", "content": "你好"}],
    model="default",
    user_id="user123",  # 指定用户ID
    stream=False
)

# 多轮对话 - 自动上下文管理
session_id = "session_001"
response1 = client.chat_completion(
    messages=[{"role": "user", "content": "我想学习Python"}],
    model="default",
    user_id="user123",
    session_id=session_id,
    enable_context=True,
    max_context_turns=5
)

response2 = client.chat_completion(
    messages=[{"role": "user", "content": "给我一个示例"}],
    model="default",
    user_id="user123",
    session_id=session_id,
    enable_context=True,
    max_context_turns=5
)
```

### 方式2：使用requests库（支持所有功能）

```python
import requests
import json

def call_api_with_auth(messages, user_id, session_id=None, enable_context=False, stream=False):
    """使用requests库调用API - 支持所有功能和鉴权"""
    url = "http://localhost:8001/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key-here"  # API Key鉴权
    }
    
    data = {
        "model": "default",
        "messages": messages,
        "user_id": user_id,  # 用户ID
        "session_id": session_id,  # 会话ID（可选）
        "enable_context": enable_context,  # 是否启用上下文
        "max_context_turns": 5,
        "stream": stream,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    if stream:
        # 流式响应处理
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        if 'choices' in chunk_data and chunk_data['choices']:
                            content = chunk_data['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                print(content, end="", flush=True)
                                full_response += content
                    except json.JSONDecodeError:
                        continue
        print()  # 换行
        return full_response
    else:
        # 非流式响应
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']

# 使用示例
if __name__ == "__main__":
    # 单轮对话
    response = call_api_with_auth(
        messages=[{"role": "user", "content": "你好，请介绍一下你自己"}],
        user_id="user123"
    )
    print(f"单轮对话响应: {response}")
    
    # 多轮对话 - 流式输出
    session_id = "session_001"
    print("\n多轮对话第一轮:")
    response1 = call_api_with_auth(
        messages=[{"role": "user", "content": "我想学习Python编程"}],
        user_id="user123",
        session_id=session_id,
        enable_context=True,
        stream=True
    )
    
    print("\n多轮对话第二轮:")
    response2 = call_api_with_auth(
        messages=[{"role": "user", "content": "请给我一个Hello World示例"}],
        user_id="user123",
        session_id=session_id,
        enable_context=True,
        stream=True
    )
```

### 方式3：标准OpenAI客户端（仅单轮对话）

```bash
pip install openai
```

```python
from openai import OpenAI

def get_response_stream(prompt, openai_api_base="http://localhost:8001/v1"):
    """
    使用OpenAI客户端调用转发API - 流式输出
    注意：此方式不支持user_id和多轮对话等自定义参数
    """
    openai_api_key = "your-api-key-here"  # 你的API Key
    client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base,
    )

    # 获取可用模型（可选）
    models = client.models.list()
    model = models.data[0].id
    print(f"使用模型: {model}")

    # 发起流式请求
    response_stream = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        stream=True,  # ✅ 关键参数：启用流式返回
        max_tokens=1000,
    )

    # 实时打印每段内容
    full_response = ""
    for chunk in response_stream:
        if chunk.choices and chunk.choices[0].delta.content:
            partial = chunk.choices[0].delta.content
            print(partial, end="", flush=True)  # 实时打印
            full_response += partial

    print()  # 换行
    return full_response

# 使用示例
if __name__ == "__main__":
    response = get_response_stream("请介绍一下华东师范大学")
```

## 🔐 鉴权和用户管理

### API Key鉴权
- **启用鉴权**：在配置中设置`API_KEY`后，所有API请求都需要提供正确的API Key
- **鉴权方式**：在请求头中添加`Authorization: Bearer your-api-key-here`
- **无鉴权模式**：如果未设置`API_KEY`，则无需鉴权（适用于内网环境）

### 用户ID管理
- **显式用户ID**：推荐在请求中直接指定`user_id`参数
- **向后兼容**：支持使用`user`字段
- **匿名用户**：如果未指定用户ID，将使用`"anonymous"`

### 流式输出和多轮对话完全支持
- ✅ **流式输出**：支持API key鉴权和用户ID识别
- ✅ **多轮对话**：上下文管理基于用户ID进行隔离
- ✅ **日志记录**：所有用户行为都会记录完整的用户信息
- ✅ **统计功能**：用户统计和会话统计都支持鉴权访问

### 用户隔离保证
- 不同用户的对话历史完全隔离
- 上下文管理基于`user_id + session_id`
- 日志记录包含完整的用户身份信息
- 统计数据按用户ID分别计算

### 完整示例文件

我们提供了完整的客户端示例文件：

1. **`client_example.py`** - 完整的客户端示例（推荐）
   - 支持API key鉴权
   - 支持用户ID参数
   - 支持流式输出
   - 支持多轮对话
   - 包含错误处理

```bash
# 运行完整功能示例（推荐）
python client_example.py
```

### 错误处理示例

```python
import requests

def safe_chat_completion(messages, user_id, api_key, api_base="http://localhost:8001/v1"):
    """带错误处理的安全调用"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": "default",
            "messages": messages,
            "user_id": user_id,
            "max_tokens": 1000,
            "temperature": 0.7,
            "timeout": 30.0
        }
        
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=data,
            timeout=30.0
        )
        
        if response.status_code == 401:
            return {
                "success": False,
                "error": "API key鉴权失败，请检查API key是否正确"
            }
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "success": True,
            "content": result['choices'][0]['message']['content'],
            "usage": result.get('usage', None)
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时，请稍后重试"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "连接失败，请检查API服务是否正常运行"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"调用失败: {str(e)}"
        }

# 使用示例
result = safe_chat_completion(
    messages=[{"role": "user", "content": "你好"}],
    user_id="user123",
    api_key="your-api-key-here"
)

if result["success"]:
    print(f"AI回复: {result['content']}")
else:
    print(f"错误: {result['error']}")
```

## 🚀 新版本特性总结

### ✅ 已完成的功能升级
- **API Key鉴权**：可选的API密钥验证，保护服务安全
- **用户ID参数**：支持明确的`user_id`参数，替代从API key中提取用户ID
- **流式输出支持**：流式响应完全支持用户ID识别和API key鉴权
- **多轮对话支持**：多轮对话上下文管理完全支持用户隔离和鉴权
- **完整日志记录**：所有用户行为都记录完整的身份信息
- **向后兼容**：保持对原有API接口的兼容性

### 🎯 使用建议
- **生产环境**：建议启用API key鉴权，使用方式1或方式2的调用方式
- **开发环境**：可以不设置API key，使用任何调用方式
- **用户区分**：推荐使用明确的`user_id`参数进行用户识别
- **多轮对话**：结合`user_id`和`session_id`实现完整的用户会话管理

### 重要配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_url` | API基础URL | `http://localhost:8001/v1` |
| `api_key` | 你的API密钥 | 可选 |
| `model` | 模型名称 | `default` |
| `user_id` | 用户ID | 推荐设置 |
| `session_id` | 会话ID（多轮对话） | 可选 |
| `enable_context` | 启用上下文 | `false` |
| `max_context_turns` | 最大上下文轮数 | `5` |
| `stream` | 流式输出 | `false` |
| `max_tokens` | 最大生成长度 | `1000` |
| `temperature` | 生成温度 | `0.7` |

### 🔥 单轮对话（默认模式）

每次请求独立处理，不保留历史上下文。

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "你好，我是用户123"}
    ],
    "user_id": "user123",
    "max_tokens": 100
  }'
```

### 💬 多轮对话（Session模式）

启用Session管理，自动维护对话上下文。

```bash
# 第一轮对话
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "我想学习Python编程"}
    ],
    "user_id": "user123",
    "session_id": "session001",
    "enable_context": true,
    "max_context_turns": 5
  }'

# 第二轮对话（自动包含上下文）
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "请给我一个Hello World示例"}
    ],
    "user_id": "user123",
    "session_id": "session001",
    "enable_context": true,
    "max_context_turns": 5
  }'
```

### 🌊 流式输出

支持Server-Sent Events (SSE)流式响应：

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "请写一首诗"}],
    "user_id": "user123",
    "stream": true,
    "max_tokens": 200
  }'
```

## 📊 管理和统计API

### 用户统计
```bash
# 获取用户统计信息
curl -H "Authorization: Bearer your-api-key-here" \
  http://localhost:8001/v1/users/user123/stats

# 获取用户所有会话
curl -H "Authorization: Bearer your-api-key-here" \
  http://localhost:8001/v1/users/user123/sessions
```

### Session统计
```bash
# 获取会话统计
curl -H "Authorization: Bearer your-api-key-here" \
  http://localhost:8001/v1/sessions/session001/stats

# 获取会话历史
curl -H "Authorization: Bearer your-api-key-here" \
  http://localhost:8001/v1/sessions/session001/history
```

## 📋 完整参数说明

### ChatCompletionRequest

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | ✅ | - | 模型名称 |
| `messages` | array | ✅ | - | 消息列表 |
| `user_id` | string | ❌ | "anonymous" | 用户ID（推荐设置） |
| `session_id` | string | ❌ | null | 会话ID（多轮对话必须） |
| `enable_context` | boolean | ❌ | false | 是否启用多轮上下文 |
| `max_context_turns` | integer | ❌ | 5 | 最大上下文轮数 |
| `stream` | boolean | ❌ | false | 是否流式输出 |
| `max_tokens` | integer | ❌ | 1000 | 最大生成token数 |
| `temperature` | float | ❌ | 0.7 | 生成温度 |
| `top_p` | float | ❌ | 1.0 | Top-p采样 |

### 重要约束

- ✅ `enable_context=false`：默认单轮模式，可选提供`session_id`
- ✅ `enable_context=true`：**必须**提供`session_id`，否则返回400错误
- ✅ `user_id`：用户标识，用于权限控制和统计
- ✅ API Key：服务访问鉴权（可选）

## 🔧 配置选项

### 命令行参数

```bash
python run.py --help

选项:
  --vllm-api TEXT     vLLM API地址 (必须)
  --port INTEGER      服务端口 [默认: 8001]  
  --api-key TEXT      API密钥 (可选)
  --log-level TEXT    日志级别 [默认: INFO]
  --help             显示帮助信息
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VLLM_API_BASE` | vLLM API地址 | - |
| `PORT` | 服务端口 | 8001 |
| `API_KEY` | API密钥 | 无（不鉴权） |
| `LOG_LEVEL` | 日志级别 | INFO |

## 📁 项目结构

```
api/
├── main.py                 # FastAPI主应用
├── vllm_client.py         # vLLM API客户端
├── conversation_manager.py # 对话管理器
├── models.py              # 数据模型定义
├── config.py              # 配置管理
├── logger_config.py       # 日志配置
├── run.py                 # 启动脚本
├── client_example.py      # 客户端示例
├── config_example.env     # 配置示例
├── requirements.txt       # 依赖包列表
├── logs/                  # 日志目录
│   ├── api.log           # 系统日志
│   ├── user_requests.log # 用户请求日志
│   └── conversations.json # 对话历史存储
└── README.md             # 项目文档
```

## 📈 性能特征

- **并发支持**: ✅ 支持高并发请求处理
- **QPS**: 40+ 请求/秒（实测）
- **响应时间**: 平均 300-500ms（取决于vLLM后端）
- **内存使用**: 低内存占用，支持长时间运行
- **数据安全**: Session数据持久化存储
- **用户隔离**: 基于用户ID的完全隔离

## 🛠️ 故障排除

### 常见问题

1. **API Key鉴权失败**
   ```bash
   HTTP 401: Invalid API key
   ```
   解决方案：检查API key是否正确设置

2. **端口被占用**
   ```bash
   ERROR: address already in use
   ```
   解决方案：更换端口或停止占用进程

3. **vLLM连接失败**
   ```bash
   Connection refused
   ```
   解决方案：检查vLLM服务是否正常运行

---

**🎯 现在您的API已经完全支持API Key鉴权和用户ID管理！**

### 日志查看

- **系统日志**: `tail -f logs/api.log`
- **用户请求**: `tail -f logs/user_requests.log | jq`
- **对话历史**: `cat logs/conversations.json | jq`

---

🚀 **开始使用**: 
```bash
# 基本启动
python run.py --vllm-api "your-api-url" --api-key "your-api-key" --port 8001

# 生产环境（推荐）
python run.py --vllm-api "your-api-url" --disable-docs --api-key "your-api-key"

# 开发环境
python run.py --vllm-api "your-api-url" --docs-no-auth
```

⚠️ **安全提醒**: 在生产环境中，建议使用 `--disable-docs` 参数完全禁用 API 文档，防止敏感信息泄露

📖 **API文档**: http://localhost:8001/docs

🔒 **安全配置**: 查看 [SECURITY.md](SECURITY.md) 了解如何配置 Swagger UI 安全防护

💡 **技术支持**: 查看日志文件或提交Issue 