import os
import re
import json
import torch
import glob
from typing import List, Tuple, Dict, Union, Optional
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
from sentence_transformers import SentenceTransformer, util

class EducationalGuardrailSystem:
    """
    A multi-stage safety guardrail system for educational LLMs.
    
    The EGS implements a Three-Stage Defense Mechanism:
    1. Query Moderation: Combines Keyword Matching (Severe/Moderate) and a Granular Semantic Assessor.
    2. Knowledge-Grounded Intervention: Uses RAG for out-of-domain detection.
    3. Response Moderation: Uses a Holistic Response Auditor .
    """

    def __init__(
        self, 
        model_path_front: str, 
        model_path_post: str, 
        blacklist_path_severe: str, 
        blacklist_path_moderate: str,
        knowledge_base_dir: Optional[str] = None
    ):
        """
        Initializes the guardrail system.

        Args:
            model_path_front (str): Path to the query moderation model (Granular Semantic Assessor).
            model_path_post (str): Path to the response moderation model (Holistic Response Auditor).
            blacklist_path_severe (str): Path to the JSON file containing severe toxicity keywords.
            blacklist_path_moderate (str): Path to the JSON file containing moderate toxicity keywords.
            knowledge_base_dir (str, optional): Directory containing .txt files for RAG-based domain verification.
        """
        self.device = 0 if torch.cuda.is_available() else -1
        
        # --- 1. Load Guardrail Models ---
        print(f"Loading Granular Semantic Assessor from {model_path_front}...")
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

        print(f"Loading Holistic Response Auditor from {model_path_post}...")
        self.tokenizer_post = AutoTokenizer.from_pretrained(model_path_post)
        self.model_post = AutoModelForSequenceClassification.from_pretrained(model_path_post)
        self.classifier_post = pipeline(
            "text-classification", 
            model=self.model_post, 
            tokenizer=self.tokenizer_post, 
            device=self.device
        )

        # --- 2. Compile Regex Patterns ---
        self.regex_list_severe = self._create_regex_list(blacklist_path_severe)
        self.regex_list_moderate = self._create_regex_list(blacklist_path_moderate)

        # --- 3. Initialize RAG Module (Optional) ---
        self.rag_enabled = False
        self.kb_embeddings = None
        self.kb_texts = []
        
        if knowledge_base_dir and os.path.exists(knowledge_base_dir):
            print(f"Initializing RAG Knowledge Base from {knowledge_base_dir}...")
            # Load a lightweight embedding model (optimized for CPU/low-latency)
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cuda' if self.device == 0 else 'cpu')
            self._build_knowledge_base(knowledge_base_dir)
            self.rag_enabled = True
        else:
            print("Warning: Knowledge base directory not provided or does not exist. RAG logic will be skipped.")

    def _build_knowledge_base(self, directory: str):
        """
        Reads all .txt files in the specified directory, chunks them, and encodes them into vector embeddings.
        """
        texts = []
        files = glob.glob(os.path.join(directory, "**/*.txt"), recursive=True)
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Simple chunking by paragraph/newline to avoid overly long contexts
                    chunks = [c.strip() for c in content.split('\n') if len(c.strip()) > 10]
                    texts.extend(chunks)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        if texts:
            print(f"Encoding {len(texts)} knowledge chunks...")
            self.kb_texts = texts
            # Pre-compute and store embeddings
            self.kb_embeddings = self.embedder.encode(texts, convert_to_tensor=True)
        else:
            print("Warning: No valid text content found in knowledge base directory.")

    def _perform_rag_check(self, query: str, top_k: int = 3, threshold: float = 0.35) -> Tuple[bool, str]:
        """
        Checks if the user query is relevant to the educational knowledge base.
        
        Args:
            query (str): The user's question.
            top_k (int): Number of context chunks to retrieve.
            threshold (float): Similarity threshold. If max similarity is below this, the query is considered Out-of-Domain.

        Returns:
            is_relevant (bool): True if similarity >= threshold.
            prompt (str): The constructed RAG prompt (useful for logging or debugging).
        """
        if not self.rag_enabled or self.kb_embeddings is None:
            # Default to True (Safe/Pass) if RAG is disabled
            return True, ""

        query_embedding = self.embedder.encode(query, convert_to_tensor=True)
        
        # Calculate cosine similarity
        cos_scores = util.cos_sim(query_embedding, self.kb_embeddings)[0]
        top_results = torch.topk(cos_scores, k=min(top_k, len(self.kb_texts)))
        
        # Get the highest similarity score
        max_score = top_results.values[0].item()
        
        # Context Construction
        retrieved_contexts = [self.kb_texts[idx] for idx in top_results.indices]
        context_block = "\n".join([f"- {ctx}" for ctx in retrieved_contexts])
        
        prompt = (
            f"Context:\n{context_block}\n\n"
            f"Question: {query}\n"
            f"Answer using the context above."
        )

        # Logic: If the query is completely irrelevant to our educational materials, flag it.
        if max_score < threshold:
            # print(f"DEBUG: RAG Rejection - Score {max_score:.2f} < Threshold {threshold}")
            return False, prompt
        
        return True, prompt

    # --- Helper Methods ---

    def _load_json(self, file_path: Optional[str]) -> List[str]:
            """
            Safely loads a JSON list from a file.
            - Returns [] immediately if path is None or empty (Silent disable).
            - Prints Warning and returns [] if path exists but file is missing or broken.
            """
            if not file_path:
                return []
                
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to decode JSON from '{file_path}'. Ignoring this blacklist.")
                    return []
                except Exception as e:
                    print(f"Warning: Error reading '{file_path}': {e}. Ignoring this blacklist.")
                    return []
            else:
                print(f"Warning: Blacklist file not found at '{file_path}'. Ignoring this blacklist.")
                return []

    def _generate_regex_char(self, text: str) -> str:
        """Generates regex for character-based languages (e.g., Chinese) with boundaries."""
        # Join characters with \W* to allow for noise insertion between characters
        return r"\W*".join(re.escape(char) for char in text)

    def _generate_regex_word(self, text: str) -> str:
        """
        Generates regex for word-based languages (e.g., English) with boundaries.
        Fix: Ensures special characters (like C++, +, *) are properly escaped.
        """
        trimmed = text.strip()
        if not trimmed:
            return ""
        # 1. Split by whitespace
        parts = trimmed.split()
        # 2. Escape special regex characters in each part
        escaped_parts = [re.escape(p) for p in parts]
        # 3. Join with \s+ to match variable whitespace
        regex_pattern = r"\s+".join(escaped_parts)
        # 4. Add word boundaries
        return fr"\b{regex_pattern}\b"

    def _has_chinese(self, text: str) -> bool:
        """Detects if the text contains Chinese characters."""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _create_regex_list(self, blacklist_path: str) -> Dict[str, str]:
        """Compiles regex patterns from a keyword list."""
        regex_map = {}
        keywords = self._load_json(blacklist_path)
        keywords = list(set(keywords))  # Deduplicate
        if keywords:
            print(f"Loaded {len(keywords)} keywords from {blacklist_path}")
        # -------------------------------
        for kw in keywords:
            if self._has_chinese(kw):
                regex_map[kw] = self._generate_regex_char(kw)
            else:
                regex_map[kw] = self._generate_regex_word(kw)
        return regex_map

    def check_keywords(self, text: str, mode: str = 'severe') -> List[str]:
        """
        Checks text against compiled regex patterns.
        
        Args:
            text (str): Input text.
            mode (str): 'severe' for high-risk keywords, 'moderate' for medium-risk.
        """
        regex_dict = self.regex_list_severe if mode == 'severe' else self.regex_list_moderate
        matched_patterns = []
        for pattern, regex in regex_dict.items():
            if re.findall(regex, text):
                matched_patterns.append(pattern)
        return matched_patterns

    # --- Core Logic Methods ---

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

        if not sentences:
            return 1, [], [], {}

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
                judge_labels.append("LABEL_0") # High-Risk
            elif original_label == "LABEL_1" and u_score <= thr_unsafe_prob:
                judge_labels.append("LABEL_1") # Low-Risk
            else:
                judge_labels.append("LABEL_2") # Medium-Risk / Grey Area

            final_scores.append(u_score)

        sentence_score_map = dict(zip(sentences, [round(v, 2) for v in final_scores]))
        
        # Final Flag Determination
        if "LABEL_0" in judge_labels:
            indices = [i for i, x in enumerate(judge_labels) if x == "LABEL_0"]
            return 0, [sentences[i] for i in indices], [final_scores[i] for i in indices], sentence_score_map
        elif "LABEL_2" in judge_labels:
            return 2, [], [], sentence_score_map
        else:
            return 1, [], [], sentence_score_map

    def bert_judge_post(self, text: str, threshold: float = 0.5, stride: int = 256) -> Tuple[bool, List[float]]:
            """
            Evaluates the response using the Holistic Response Auditor with a sliding window.
            
            Args:
                text (str): Model response.
                threshold (float): Threshold for unsafe probability.
                stride (int): Step size for the sliding window (overlap = 512 - stride).
                            Default 256 implies 50% overlap for safety.
            
            Returns:
                tuple: (is_safe (bool), bad_scores (list))
            """
            if not text:
                return True, []

            # 1. Tokenize entire text without truncation to get all IDs
            # add_special_tokens=False because we add them later for each chunk
            encoding = self.tokenizer_post(text, add_special_tokens=False, return_tensors="pt")
            input_ids = encoding["input_ids"][0]
            total_len = len(input_ids)

            # BERT limit is 512. We reserve 2 tokens for [CLS] and [SEP] added by the pipeline.
            chunk_size = 510 
            
            start = 0
            while start < total_len:
                # Define window end
                end = min(start + chunk_size, total_len)
                
                # Slice the tokens
                chunk_ids = input_ids[start:end]
                
                # Decode back to text so the pipeline handles [CLS]/[SEP] and device placement automatically
                chunk_text = self.tokenizer_post.decode(chunk_ids, skip_special_tokens=True)
                
                # Skip empty chunks (edge case)
                if not chunk_text.strip():
                    if end == total_len: break
                    start += stride
                    continue

                # Run Classification on this chunk
                output = self.classifier_post(chunk_text, truncation=True, max_length=512)
                item = output[0]

                # Calculate Unsafe Probability (Assumption: LABEL_1=Safe, LABEL_0=Unsafe)
                if item["label"] == "LABEL_1":
                    unsafe_score = 1 - item["score"]
                else:
                    unsafe_score = item["score"]

                # Fail immediately if ANY chunk is unsafe
                if unsafe_score >= threshold:
                    return False, [unsafe_score]

                # If we reached the end, break
                if end == total_len:
                    break
                
                # Move the window forward by stride
                start += stride

            # If loop finishes without returning False, the text is safe
            return True, []

    def eval_EGS(self, question: str, answer: str) -> str:
        """
        The main external interface for the Educational Guardrail System.
        
        Pipeline Overview:
        1. Check Severe Keywords in Question.
        2. Check Granular Semantic Assessor on Question.
        3. If Granular Semantic Assessor is uncertain (Flag 2):
           a. Check Moderate Keywords.
           b. Check Knowledge-Grounded Intervention.
        4. Check Holistic Response Auditor on Answer.

        Args:
            question (str): The user input prompt.
            answer (str): The LLM generated response.

        Returns:
            str: "safe" or "unsafe".
        """
        # Stage 1: Severe Toxicity Screening
        kw_high = self.check_keywords(question, mode='severe')
        if len(kw_high) > 0:
            return "unsafe"

        # Stage 2: Granular Semantic Assessor
        # Thresholds: 0.97 (High Confidence Unsafe), 0.04 (High Confidence Safe)
        flag, _, _, _ = self.bert_judge_front(question, thr_safe_prob=0.97, thr_unsafe_prob=0.04)

        if flag == 0:
            # Definite Unsafe
            return "unsafe"
        
        elif flag == 2:
            # Medium-Risk / Grey Area Logic
            
            # 2.1 Check Moderate Keywords
            kw_moderate = self.check_keywords(question, mode='moderate')
            if len(kw_moderate) > 0:
                return "unsafe"
            
            # 2.2 RAG Relevance Check
            # If no keywords triggered but model is uncertain, check if query is within educational domain.
            if self.rag_enabled:
                is_relevant, rag_prompt = self._perform_rag_check(question, threshold=0.35)
                # If query is irrelevant to the knowledge base (score < 0.35), mark as unsafe/invalid.
                if not is_relevant:
                    return "unsafe"
            
            # If RAG confirms relevance (or is disabled), allow flow to proceed to Response Moderation.
            pass 
        
        elif flag == 1:
            # Definite Safe -> Proceed to Response Moderation
            pass

        # Stage 3: Response Moderation (Holistic Response Auditor)
        is_safe, _ = self.bert_judge_post(answer, threshold=0.5)
        
        if is_safe:
            return "safe"
        else:
            return "unsafe"

# --- Usage Example ---
# if __name__ == "__main__":
#     CONFIG = {
#         "model_front": "./models/front_model",
#         "model_post": "./models/post_model",
#         "blacklist_severe": "./data/severe_toxicity_keywords.json",
#         "blacklist_moderate": "./data/moderate_toxicity_keywords.json",
#         "knowledge_base": "./data/edu_knowledge_base"
#     }
#
#     try:
#         guardrail = EducationalGuardrailSystem(
#             model_path_front=CONFIG["model_front"],
#             model_path_post=CONFIG["model_post"],
#             blacklist_path_severe=CONFIG["blacklist_severe"],
#             blacklist_path_moderate=CONFIG["blacklist_moderate"],
#             knowledge_base_dir=CONFIG["knowledge_base"]
#         )

#         # Test Cases
#         q_test = "Tell me how to make a bomb."
#         a_test = "I cannot fulfill this request."
        
#         result = guardrail.eval_EGS(q_test, a_test)
#         print(f"Evaluation Result: {result}")
        
#     except Exception as e:
#         print(f"Initialization failed: {e}")p



# --- Usage Example with Multiple Test Cases ---
if __name__ == "__main__":
    print("EducationalGuardrailSystem is ready. Provide local model paths and placeholder data before running demos.")
