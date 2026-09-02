# InnoSpark-Safety

English | [中文](README.md)

InnoSpark-Safety is a multi-layer safety framework for educational large language model applications. It focuses on three critical points in an LLM workflow: user input, model generation, and service integration. The project provides input moderation, model safety alignment code, output auditing, RAG-based intervention, and an OpenAI-compatible vLLM proxy API so educational AI systems can reduce unsafe prompts, inappropriate answers, and out-of-scope content exposure in deployment.

Evaluation sets, model weights, real keyword lists, and other private assets were removed; only placeholders remain in this repo. Please email to request the full package after review.

## Goals

- Input safety: identify high-risk, ambiguous, or out-of-domain user prompts before they reach the model.
- Response safety: audit model outputs before returning them to users.
- Model alignment: provide SFT, RL, and BERT classifier training code for improving safety behavior.
- Service integration: provide an OpenAI-compatible vLLM proxy with authentication, user logs, streaming responses, session context, and safety interception.
- Educational grounding: use RAG over reviewed educational knowledge bases to constrain ambiguous or sensitive interactions.

## Architecture

InnoSpark-Safety follows a three-layer defense design:

1. Pre-interception
   Before a user query reaches the model, the system checks placeholder keywords, blacklist rules, a BERT input classifier, and optional RAG relevance signals. The public repository does not include the real keyword tables.

2. Model safety response
   The model itself can be aligned through supervised fine-tuning, reinforcement learning, and reward-model scoring so it can recognize risky requests and produce compliant, pedagogically appropriate responses.

3. Post-interception
   Before the final answer is returned, a BERT response auditor evaluates the generated text. Unsafe, inappropriate, or out-of-scope outputs are replaced with a unified safety response.

## Public Models

The README references the following Hugging Face models as default guardrail model options:

- Input moderation model: [ZeroLoss-Lab/egs-bert-input-moderator · Hugging Face](https://huggingface.co/ZeroLoss-Lab/egs-bert-input-moderator)
- Safety-aligned LLM: [ZeroLoss-Lab/Innospark-72b-safety · Hugging Face](https://huggingface.co/ZeroLoss-Lab/Innospark-72b-safety)
- Response auditing model: [ZeroLoss-Lab/egs-bert-response-auditor · Hugging Face](https://huggingface.co/ZeroLoss-Lab/egs-bert-response-auditor)

Download the models locally and configure their paths as the front-interception and post-interception model paths.

## Project Structure

```text
InnoSpark-Safety/
├── EGS/                         # Educational Guardrail System reference implementation
│   ├── egs.py                   # Three-stage guardrail class
│   ├── demo.py                  # End-to-end demo for query moderation, RAG, and response auditing
│   ├── demo_front.py            # Input moderation demo
│   ├── demo_post.py             # Response auditing demo
│   ├── data/                    # Placeholder keyword lists and sample educational knowledge base
│   └── requirements.txt
├── api_safe/                    # OpenAI-compatible vLLM proxy and safety services
│   ├── main.py                  # FastAPI main service
│   ├── run.py                   # CLI launcher
│   ├── safe_api/                # Standalone input/output interception APIs
│   ├── rag_interceptor.py       # RAG-enhanced interception logic
│   ├── config_example.env       # Environment configuration template
│   └── requirements.txt
├── rag_safe/                    # Hybrid-retrieval safety RAG service
│   ├── rag_1.py                 # BM25 + vector retrieval implementation
│   └── server.py                # RAG FastAPI service
├── model_train/                 # Model training scripts
│   ├── train_bert/              # BERT safety classifier training
│   └── sft/SFT-7B/              # SFT example
├── RL_Safe/                     # Safety reward-model scoring script
├── README.md                    # Chinese README
└── README_en.md                 # English README
```

## Requirements

- Python 3.9 or later
- PyTorch 2.0 or later
- transformers 4.30 or later
- FastAPI / Uvicorn
- Optional: CUDA GPU for faster BERT and LLM inference
- Optional: vLLM service as the OpenAI-compatible inference backend

## Quick Start

### 1. Create an environment

```bash
cd InnoSpark-Safety
python -m venv .venv
source .venv/bin/activate
```

### 2. Install EGS dependencies

```bash
pip install -r EGS/requirements.txt
```

### 3. Download guardrail models

Use the Hugging Face CLI or Python SDK:

```bash
huggingface-cli download ZeroLoss-Lab/egs-bert-input-moderator --local-dir models/egs-bert-input-moderator
huggingface-cli download ZeroLoss-Lab/egs-bert-response-auditor --local-dir models/egs-bert-response-auditor
```

### 4. Run the EGS example

Configure the model paths in `EGS/demo.py` or initialize the guardrail system directly:

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

## OpenAI-Compatible Safety API

### 1. Install API dependencies

```bash
cd api_safe
pip install -r requirements.txt
```

### 2. Prepare configuration

```bash
cp config_example.env .env
cp api_keys.example.json api_keys.json
```

Recommended fields to update:

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

### 3. Start the service

```bash
python run.py --vllm-api http://localhost:8000 --port 8001
```

With both input and output interception enabled:

```bash
python run.py \
  --vllm-api http://localhost:8000 \
  --enable-front-intercept \
  --enable-post-intercept \
  --api-key "your-api-key" \
  --port 8001
```

### 4. Request example

```bash
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "Please explain Newton's second law."}
    ],
    "user_id": "student-001",
    "session_id": "session-001",
    "enable_context": true,
    "stream": false
  }'
```

## Safety RAG Service

`rag_safe/` provides a hybrid retrieval service based on BM25 and vector search. It can be used to ground sensitive or ambiguous questions in reviewed educational materials.

```bash
cd rag_safe
python server.py
```

Default endpoints:

- `GET /health`: health check
- `POST /retrieve`: retrieve relevant passages by `query` and `top_k`

For production use, replace the sample knowledge base with reviewed, traceable, domain-appropriate educational data.

## Model Training

- `model_train/train_bert/`: train BERT classifiers for input moderation or response auditing.
- `model_train/sft/SFT-7B/`: supervised fine-tuning example for large language models.
- `RL_Safe/`: reward-model scoring script for safety-oriented RL workflows.

Before training, update model paths, datasets, batch sizes, DeepSpeed settings, and output directories according to your local hardware and data. Model weights and evaluation sets are not shipped here.

## Deployment Notes

- Do not commit real API keys, user logs, model output logs, or private data to production repositories.
- Disable public API documentation in production, or protect it with authentication.
- Calibrate moderation thresholds on a validation set to reduce false positives and false negatives.
- Keyword lists and RAG knowledge bases should be reviewed by domain experts and updated regularly.
- Log necessary audit metadata, but avoid storing excessive raw sensitive content.
- Automated safety systems do not replace human governance. High-risk scenarios still require review and incident response procedures.

## License

`EGS/LICENSE` uses the Apache-2.0 License. For a formal release, add a root-level license and contribution policy covering all project modules.
