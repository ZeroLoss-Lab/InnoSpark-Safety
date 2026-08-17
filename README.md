# InnoSpark-Safety

[English](README_en.md) | 中文

InnoSpark-Safety 是面向教育场景大语言模型的多层安全防护项目。项目围绕用户输入、模型生成与服务化调用三个关键环节，提供前置拦截、模型安全对齐、后置审核、RAG 检索干预和 OpenAI 兼容 API 代理能力，帮助教育类智能体在真实部署环境中降低不安全输入、不当回答和越界内容传播的风险。评测集等需要完整内容的请邮件申请，待人工审核后发放。

## 核心目标

- 输入安全：对用户问题进行关键词、语义分类和 RAG 相关性检查，尽早识别高风险、灰区或越界请求。
- 响应安全：对大模型输出进行后置审核，拦截不符合教育场景、法律法规或伦理规范的回复。
- 模型对齐：提供 SFT、RL 与 BERT 分类器训练相关代码，用于增强底座模型和安全审核模型能力。
- 服务集成：提供 OpenAI 兼容的 vLLM Proxy API，支持鉴权、多用户日志、流式响应、多轮会话和安全拦截链路。
- 教育可控：结合教育知识库 RAG，对敏感或模糊请求进行知识约束，减少幻觉和不当泛化。

## 系统架构

InnoSpark-HPedSafe 采用三层防护思路：

1. 前拦截系统
   用户输入进入模型前，系统会通过占位关键词、黑名单、BERT 前置分类器和可选 RAG 检索进行安全判断。公开仓库不包含真实拦截词表，相关内容需要单独申请。

2. 模型安全响应系统
   通过监督微调、强化学习和安全奖励模型等方式提升模型自身的安全识别与拒答能力，使模型在面对风险请求时能够给出合规、稳健、符合教育场景的响应。

3. 后拦截系统
   模型生成结果返回用户前，系统通过 BERT 后置审核模型再次检查输出内容。如果回复包含危险、不当、越界或不适合教育场景的信息，则返回统一安全响应。

## 公开模型

项目 README 中推荐使用以下两个 Hugging Face 模型作为前后拦截参考模型：

- 输入审核模型：[ZeroLoss-Lab/egs-bert-input-moderator · Hugging Face](https://huggingface.co/ZeroLoss-Lab/egs-bert-input-moderator)
- 响应审核模型：[ZeroLoss-Lab/egs-bert-response-auditor · Hugging Face](https://huggingface.co/ZeroLoss-Lab/egs-bert-response-auditor)

可将模型下载到本地目录后，在配置中分别设置为前拦截模型路径和后拦截模型路径。

## 项目结构

```text
InnoSpark-Safety/
├── EGS/                         # Educational Guardrail System，教育安全护栏核心示例
│   ├── egs.py                   # 三阶段护栏主类
│   ├── demo.py                  # 输入审核、RAG 检查和响应审核演示
│   ├── demo_front.py            # 前拦截演示
│   ├── demo_post.py             # 后拦截演示
│   ├── data/                    # 占位词表与示例知识库
│   └── requirements.txt
├── api_safe/                    # OpenAI 兼容 vLLM 代理与安全拦截服务
│   ├── main.py                  # FastAPI 主服务
│   ├── run.py                   # 命令行启动入口
│   ├── safe_api/                # 独立前拦截/后拦截 API 服务
│   ├── rag_interceptor.py       # RAG 增强拦截逻辑
│   ├── config_example.env       # 配置模板
│   └── requirements.txt
├── rag_safe/                    # 混合检索安全 RAG 服务
│   ├── rag_1.py                 # BM25 + 向量检索实现
│   └── server.py                # RAG FastAPI 服务
├── model_train/                 # 模型训练脚本
│   ├── train_bert/              # BERT 安全分类器训练
│   └── sft/SFT-7B/              # SFT 训练示例
├── RL_Safe/                     # 安全奖励模型评分相关脚本
├── README.md                    # 中文说明
└── README_en.md                 # English README
```

## 环境要求

- Python 3.9 或更高版本
- PyTorch 2.0 或更高版本
- transformers 4.30 或更高版本
- FastAPI / Uvicorn
- 可选：CUDA GPU，用于提升 BERT 和大模型推理速度
- 可选：vLLM 服务，用于提供 OpenAI 兼容模型推理后端

## 快速开始

### 1. 创建环境

```bash
cd InnoSpark-Safety
python -m venv .venv
source .venv/bin/activate
```

### 2. 安装 EGS 依赖

```bash
pip install -r EGS/requirements.txt
```

### 3. 下载安全审核模型

可以使用 Hugging Face CLI 或 Python SDK 下载模型：

```bash
huggingface-cli download ZeroLoss-Lab/egs-bert-input-moderator --local-dir models/egs-bert-input-moderator
huggingface-cli download ZeroLoss-Lab/egs-bert-response-auditor --local-dir models/egs-bert-response-auditor
```

### 4. 运行 EGS 示例

在 `EGS/demo.py` 或自己的脚本中配置模型路径：

```python
from EGS.egs import EducationalGuardrailSystem

guardrail = EducationalGuardrailSystem(
    model_path_front="models/egs-bert-input-moderator",
    model_path_post="models/egs-bert-response-auditor",
    blacklist_path_severe="EGS/data/severe_toxicity_keywords.json",
    blacklist_path_moderate="EGS/data/moderate_toxicity_keywords.json",
    knowledge_base_dir="EGS/data/edu_knowledge_base"
)

result = guardrail.eval_EGS(
    query="Can you explain Newton's second law?",
    response="Newton's second law states that force equals mass times acceleration."
)
print(result)
```

## 启动 OpenAI 兼容安全 API

### 1. 安装 API 依赖

```bash
cd api_safe
pip install -r requirements.txt
```

### 2. 准备配置

```bash
cp config_example.env .env
cp api_keys.example.json api_keys.json
```

建议重点修改以下配置：

```env
VLLM_API_BASE=http://localhost:8000
API_KEY=your-api-key
MODEL_FRONT_PATH=../models/egs-bert-input-moderator
MODEL_POST_PATH=../models/egs-bert-response-auditor
ENABLE_FRONT_INTERCEPT=true
ENABLE_POST_INTERCEPT=true
USE_LOCAL_INTERCEPT=true
ENABLE_RAG=false
```

### 3. 启动服务

```bash
python run.py --vllm-api http://localhost:8000 --port 8001
```

启用完整前后拦截时：

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "your-api-key" \
  --port 8001
```

### 4. 调用示例

```bash
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "请解释牛顿第二定律"}
    ],
    "user_id": "student-001",
    "session_id": "session-001",
    "enable_context": true,
    "stream": false
  }'
```

## 安全 RAG 服务

`rag_safe/` 提供基于 BM25 和向量检索的混合检索服务，可用于敏感或灰区问题的知识约束。

```bash
cd rag_safe
python server.py
```

默认接口：

- `GET /health`：健康检查
- `POST /retrieve`：按 `query` 和 `top_k` 检索知识片段

公开仓库仅包含占位知识库；生产或正式评测时请替换为你自己审核过的数据源。

## 模型训练

- `model_train/train_bert/`：用于训练输入审核或响应审核 BERT 分类器。
- `model_train/sft/SFT-7B/`：用于大模型监督微调示例。
- `RL_Safe/`：包含安全奖励模型评分相关脚本。

训练前请根据本地模型、数据集和算力修改脚本中的路径、batch size、DeepSpeed 配置和保存目录。评测集与模型权重不随仓库分发。

## 配置与部署建议

- 不要在生产仓库中提交真实 API Key、用户日志、模型输出日志或隐私数据。
- 生产环境建议关闭公开文档入口，或开启文档鉴权。
- 前后拦截阈值应根据验证集进行校准，避免过度拦截或漏拦。
- 真实拦截词表和 RAG 知识库应由领域专家审核，并建立定期更新机制。
- 对所有被拦截请求记录必要审计信息，但应避免保存过多原始敏感内容。
- 安全系统不能替代人工治理；高风险场景仍需人工复核和应急流程。

## 许可证

`EGS/LICENSE` 使用 Apache-2.0 许可证。其他子模块如无单独声明，建议在正式发布前统一补充根目录许可证与贡献说明。
