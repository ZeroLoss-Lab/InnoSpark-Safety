import re
import torch
from typing import List, Tuple, Dict
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

class EducationalGuardrailSystem:
    """
    A simplified safety guardrail system focusing ONLY on the front-end Semantic Assessor.
    """

    def __init__(self, model_path_front: str):
        """
        Initializes the front-end guardrail model.

        Args:
            model_path_front (str): Path to the query moderation model.
        """
        self.device = 0 if torch.cuda.is_available() else -1
        
        # --- Load Guardrail Model (Front Only) ---
        print(f"Loading Granular Semantic Assessor from {model_path_front}...")
        try:
            self.tokenizer_front = AutoTokenizer.from_pretrained(model_path_front)
            self.model_front = AutoModelForSequenceClassification.from_pretrained(model_path_front)
            self.classifier_front = pipeline(
                "text-classification", 
                model=self.model_front, 
                tokenizer=self.tokenizer_front, 
                device=self.device, 
                truncation=True, 
                max_length=512
            )
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise e

    def bert_judge_front(self, text: str, thr_safe_prob: float = 0.97, thr_unsafe_prob: float = 0.04) -> Tuple[int, List[str], List[float], Dict[str, float]]:
        """
        Evaluates the query using the Granular Semantic Assessor.
        
        Returns:
            tuple: (flag, bad_sentences, bad_scores, sentence_scores_dict)
            - flag (int): 0 (Definite Unsafe), 1 (Definite Safe), 2 (Suspicious/Grey).
        """
        # Remove noise characters
        text = text.replace("*", "").replace("#", "")
        # Split sentences by CJK or English periods
        sentences = re.split(r'(?<=[\u3002.])', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

        # If text is too short or empty, treat as Safe (or handle as edge case)
        if not sentences:
            return 1, [], [], {}

        # Run inference
        outputs = self.classifier_front(sentences)

        # Normalize outputs to "Unsafe Probability"
        processed_results = []
        for item in outputs:
            score = item["score"]
            label = item["label"]
            # Assumption: LABEL_1 is Safe, LABEL_0 is Unsafe
            if label == "LABEL_1":
                unsafe_score = 1 - score
            else:
                unsafe_score = score
            processed_results.append({"score": unsafe_score, "label": label})

        judge_labels = []
        final_scores = []
        
        for item in processed_results:
            u_score = item["score"]
            original_label = item["label"]
            
            # Logic mapping based on thresholds
            if original_label == "LABEL_0" and u_score >= thr_safe_prob: 
                judge_labels.append("LABEL_0") # High-Risk / Definite Unsafe
            elif original_label == "LABEL_1" and u_score <= thr_unsafe_prob:
                judge_labels.append("LABEL_1") # Low-Risk / Definite Safe
            else:
                judge_labels.append("LABEL_2") # Medium-Risk / Grey Area

            final_scores.append(u_score)

        sentence_score_map = dict(zip(sentences, [round(v, 2) for v in final_scores]))
        
        # Final Flag Determination Logic
        # Priority: Unsafe (0) > Grey (2) > Safe (1)
        if "LABEL_0" in judge_labels:
            indices = [i for i, x in enumerate(judge_labels) if x == "LABEL_0"]
            return 0, [sentences[i] for i in indices], [final_scores[i] for i in indices], sentence_score_map
        elif "LABEL_2" in judge_labels:
            return 2, [], [], sentence_score_map
        else:
            return 1, [], [], sentence_score_map

    def eval_query(self, query: str) -> str:
        """
        Simple wrapper to get a safe/unsafe/uncertain verdict based purely on model_front.
        """
        flag, bad_sents, scores, _ = self.bert_judge_front(query)
        
        if flag == 0:
            return f"UNSAFE (Detected: {bad_sents})"
        elif flag == 2:
            return "UNCERTAIN (Grey Area - would normally trigger secondary checks)"
        else:
            return "SAFE"

# --- Usage Example ---
if __name__ == "__main__":
    # Configuration
    model_path = "./models/front_model"

    print("\n" + "="*60)
    print("Initializing Front-End Guardrail Only...")
    print("="*60)

    try:
        guardrail = EducationalGuardrailSystem(model_path_front=model_path)
        
        # Test Cases
        test_queries = [
            "Can you explain photosynthesis?",
            "Summarize the main idea of a paragraph.",
            "What is the water cycle?",
            "This is a neutral placeholder sentence."
        ]

        print("\nStarting Evaluation...")
        for q in test_queries:
            flag, bad_sentences, scores, detail_map = guardrail.bert_judge_front(q)
            
            print(f"\nQuery: {q}")
            print(f" -> Flag: {flag} (0=Unsafe, 1=Safe, 2=Grey)")
            print(f" -> Unsafe Scores: {scores}")
            if flag == 0:
                print(f" -> Bad Sentences: {bad_sentences}")

    except Exception as e:
        print(f"\nInitialization failed: {e}")
