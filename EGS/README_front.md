---
language:
- en
- zh
tags:
- text-classification
- safety
- education
- guardrails
- deberta
pipeline_tag: text-classification
license: apache-2.0
---

# Educational Guardrail System - Granular Semantic Assessor

## Model Details

- **Model Name:** Granular Semantic Assessor (Query Moderation)
- **Model Architecture:** [DeBERTa-v3-Base](https://huggingface.co/microsoft/deberta-v3-base)
- **Task:** Query Moderation
- **Domain:** K-12 Education & General AI Safety
- **Language:** English

## Model Description

This model serves as the **Granular Semantic Assessor**, the core component of the "Query Moderation" stage in the **Educational Guardrail System (EGS)**. It is designed to act as a "System 1" fast-response filter to detect potential safety risks in user queries before they reach the LLM.

Unlike standard content moderation models, this model is fine-tuned specifically for **educational contexts**, aiming to distinguish between benign pedagogical inquiry (e.g., "History of wars") and harmful intent.

### Key Features
* **DeBERTa-v3 Architecture:** Leverages DeBERTa's superior NLU capabilities for detecting implicit adversarial patterns like metaphorical abuse and irony.
* **Granular Assessment:** Supports a **Tri-State Mechanism** (Safe, Unsafe, Medium Risk) to handle ambiguity, rather than a rigid binary block.
* **Anti-Dilution Strategy:** Designed to work with a **Sentence-Level Max-Pooling** inference strategy to prevent localized toxicity from being diluted in long contexts.

## Safety Taxonomy & Capability

The model is trained to align with the **EGS Safety Taxonomy**, covering three critical dimensions:
1.  **Universal Ethical Safety:** Countering terrorism, extremism, hate speech, and violence.
2.  **Regional Legal Safety:** Ensuring compliance with regional regulations and cultural norms.
3.  **Pedagogical Developmental Safety:** Protecting minors from age-inappropriate content (e.g., horror, cognitive offloading hints).

## Label Mapping & Risk Logic

The underlying model outputs binary labels/probabilities, which are mapped to **three risk levels** in the EGS inference pipeline.

### 1. Raw Model Outputs
- **LABEL_0:** Predicted **Unsafe** (High Risk)
- **LABEL_1:** Predicted **Safe** (Low Risk)
- **LABEL_2:** Predicted **Ambiguous** (Medium Risk)

### 2. EGS System Logic (Tri-State Risk Levels)
According to our ablation studies, we utilize optimal thresholds ($T_1=0.04, T_2=0.92$) to minimize False Positives in educational settings.

| Logic Label | Risk Level | Condition ($P_{unsafe}$) | Action |
| :--- | :--- | :--- | :--- |
| **0** | **High Risk** (Unsafe) | $P_{unsafe} > 0.92$ | **Block Immediately** |
| **2** | **Medium Risk** (Grey Area) | $0.04 < P_{unsafe} \le 0.92$ | **Trigger Secondary Checks**  |
| **1** | **Low Risk** (Safe) | $P_{unsafe} \le 0.04$ | **Pass to LLM** |

*> Note: The thresholds (0.92/0.04) are empirically derived to maximize F1 score on educational benchmarks.*

## Intended Use & Inference Strategy

**Critical Note:** To replicate the performance reported in the paper, you should split long inputs into sentences and aggregate scores using a **Max-Pooling** strategy.

### Recommended Logic (Python)

```python
import torch
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_name = "YourOrg/Granular Semantic Assessor"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

def get_risk_level(text):
    # 1. Segmentation (Crucial for preventing toxicity dilution)
    # Split by periods or CJK delimiters
    sentences = re.split(r'(?<=[\u3002.])', text) 
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if not sentences: sentences = [text]

    # 2. Inference
    inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    
    # Assuming LABEL_0 is Unsafe. Check your specific config!
    # Calculate Unsafe Score for each sentence
    sent_unsafe_scores = probs[:, 0].tolist() 
    
    # 3. Max-Pooling Aggregation
    max_unsafe_score = max(sent_unsafe_scores)
    
    # 4. Tri-State Logic (Thresholds from Paper)
    T_high = 0.92
    T_low = 0.04
    
    if max_unsafe_score > T_high:
        return 0, "High Risk"
    elif max_unsafe_score > T_low:
        return 2, "Medium Risk"
    else:
        return 1, "Low Risk"