from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import re
import torch
import json
import os
import logging
from typing import List, Dict, Any, Optional
import gc

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="前拦截API服务", description="高敏感词和1w黑名单的前拦截服务")

class TextRequest(BaseModel):
    text: str

class InterceptResponse(BaseModel):
    is_safe: bool
    safety_response: Optional[str] = None

class DetailedInterceptResponse(BaseModel):
    is_safe: bool
    reason: str
    matched_keywords: Optional[List[str]] = None
    bert_results: Optional[Dict[str, Any]] = None
    safety_response: Optional[str] = None

class FrontInterceptor:
    def __init__(self, model_front_path: str, blacklist_1w_path: str, 
                 high_sensitive_keywords_path: str = None):
        self.model_dir_front = model_front_path
        self.blacklist_1w_path = blacklist_1w_path
        self.high_sensitive_keywords_path = high_sensitive_keywords_path
        # Safe API 不需要管理安全响应消息，只负责拦截判断
        # 安全响应消息由主 API 统一管理
        
        # 加载BERT模型
        self._load_model()
        
        # 创建正则表达式列表
        self.high_sensitive_regex_list = self.create_high_sensitive_regex_list()
        self.regex_list_sub = self.create_regex_list_sub()
        self.sensitive_regex_list = self.create_sensitive_regex_list()
        
        logger.info("前拦截服务初始化完成")

    def _load_model(self):
        """加载BERT模型"""
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 加载tokenizer
            self.tokenizer_front = AutoTokenizer.from_pretrained(
                self.model_dir_front, 
                use_fast=True
            )
            
            # 正常加载模型，不使用量化
            self.model_front = AutoModelForSequenceClassification.from_pretrained(
                self.model_dir_front
            )
            
            self.classifier_front = pipeline(
                "text-classification", 
                model=self.model_front, 
                tokenizer=self.tokenizer_front, 
                device=device,
                max_length=512,
                truncation=True
            )
            
            logger.info(f"前拦截模型加载完成，使用设备: {device}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def load_json(self, file_path: str) -> List:
        """加载JSON文件"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            return json_data
        return []

    def generate_regex(self, text: str) -> str:
        """生成正则表达式"""
        regex = r"\W*".join(re.escape(char) for char in text)
        return regex

    def create_high_sensitive_regex_list(self) -> Dict[str, str]:
        """创建高敏感关键词正则表达式列表"""
        regex_list = {}
        if self.high_sensitive_keywords_path and os.path.exists(self.high_sensitive_keywords_path):
            high_sensitive_keywords = self.load_json(self.high_sensitive_keywords_path)
            if high_sensitive_keywords:
                high_sensitive_keywords = list(set(high_sensitive_keywords))
                regex_list = {s: self.generate_regex(s) for s in high_sensitive_keywords}
        return regex_list

    def create_regex_list_sub(self) -> Dict[str, List[str]]:
        """创建1w黑名单正则表达式列表"""
        regex_list = {}
        blacklist = self.load_json(self.blacklist_1w_path)

        if blacklist:
            for blackdict in blacklist:
                if 'keyword' in blackdict and 'sub_keywords' in blackdict:
                    sub_blacklist = [self.generate_regex(x) for x in blackdict['sub_keywords']]
                    regex_list[blackdict['keyword']] = sub_blacklist

        return regex_list

    def create_sensitive_regex_list(self) -> Dict[str, str]:
        """创建敏感关键词正则表达式列表（从1w黑名单的sub_keywords提取）"""
        regex_list = {}
        blacklist = self.load_json(self.blacklist_1w_path)

        if blacklist:
            all_sensitive_keywords = []
            for blackdict in blacklist:
                if 'sub_keywords' in blackdict:
                    all_sensitive_keywords.extend(blackdict['sub_keywords'])
            
            # 去重并生成正则表达式
            all_sensitive_keywords = list(set(all_sensitive_keywords))
            regex_list = {s: self.generate_regex(s) for s in all_sensitive_keywords}

        return regex_list

    def check_high_sensitive_keywords(self, text: str) -> List[str]:
        """检查高敏感关键词"""
        match_pattern_list = []
        
        for pattern, regex in self.high_sensitive_regex_list.items():
            matches = re.findall(regex, text, re.IGNORECASE)
            if matches:
                match_pattern_list.append(pattern)

        return list(set(match_pattern_list))

    def check_sensitive_keywords(self, text: str) -> List[str]:
        """检查敏感关键词"""
        match_pattern_list = []
        
        for pattern, regex in self.sensitive_regex_list.items():
            matches = re.findall(regex, text, re.IGNORECASE)
            if matches:
                match_pattern_list.append(pattern)

        return list(set(match_pattern_list))

    def check_1w_blacklist(self, text: str) -> List[str]:
        """检查1w黑名单关键词"""
        match_pattern_list = []

        # 检查子关键词
        for pattern, regex_list in self.regex_list_sub.items():
            for regex in regex_list:
                matches = re.findall(regex, text, re.IGNORECASE)
                if matches:
                    match_pattern_list.append(pattern)
                    break  # 找到一个匹配就跳出内层循环

        return list(set(match_pattern_list))

    def bert_judge_front(self, text: str) -> tuple:
        """前拦截BERT判断（单阈值）"""
        try:
            # 预处理
            text = text.replace("*", "").replace("#", "")
            sentences = re.split(r'(?<=[\u3002.])', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

            if not sentences:
                return True, [], [], {}

            # 模型分类
            bad_sentences = []
            
            # 模型分类
            all_output = self.classifier_front(sentences)

            judgelist = [x['label'] for x in all_output]
            flag = True
            bad_score = []
            all_score = []

            all_score = [item['score'] if item['label'] == 'LABEL_1' else -item['score'] for item in all_output]
            sentence_score = dict(zip(sentences, [round(v, 2) for v in all_score]))

            if "LABEL_0" in judgelist:
                indices = [i for i, x in enumerate(judgelist) if x == "LABEL_0"]
                bad_sentences = [sentences[i] for i in indices]
                bad_score = [all_output[i]['score'] for i in indices]
                flag = False

            return flag, bad_sentences, bad_score, sentence_score
            
        except Exception as e:
            logger.error(f"BERT前拦截判断出错: {e}")
            # 出错时返回不安全，避免风险
            return False, [text], [0.0], {}

    def bert_judge_front2(self, text: str, thr_b_g=None, thr_g_b=None) -> tuple:
        """BERT前拦截判断（双阈值）"""
        try:
            # 从环境变量获取阈值，如果参数未提供
            if thr_b_g is None:
                thr_b_g = float(os.getenv("BERT_FRONT_HIGH_THRESHOLD", "0.97"))
            if thr_g_b is None:
                thr_g_b = float(os.getenv("BERT_FRONT_LOW_THRESHOLD", "0.00002"))
            
            # 预处理
            text = text.replace("*", "").replace("#", "")
            sentences = re.split(r'(?<=[\u3002.])', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

            if not sentences:
                return 1, [], [], {}

            # 模型分类
            bad_sentences = []
            output = self.classifier_front(sentences)
            
            flag = 1  # 0: 拦截, 1: 通过, 2: 未确定
            bad_score = []
            all_score = [x['score'] for x in output]
            sentence_score = dict(zip(sentences, [round(v, 2) for v in all_score]))
            
            for i, item in enumerate(output):
                if item["label"] == "LABEL_0":  # LABEL_0表示有害
                    if item["score"] >= thr_b_g:  # 有害性高于第一个阈值，拦截
                        flag = 0
                        bad_sentences.append(sentences[i])
                        bad_score.append(item['score'])
                    elif item["score"] > thr_g_b:  # 有害性高于第二个阈值，但低于第一个阈值
                        if flag != 0:  # 如果还没有被拦截
                            flag = 2  # 未确定
                    # 有害性低于第二个阈值为通过，保持flag=1
                
            return flag, bad_sentences, bad_score, sentence_score
            
        except Exception as e:
            logger.error(f"BERT前拦截双阈值判断出错: {e}")
            # 出错时返回拦截，避免风险
            return 0, [text], [0.0], {}

# 初始化拦截器实例
interceptor = None

@app.on_event("startup")
async def startup_event():
    global interceptor
    try:
        # 这里需要根据实际情况修改路径
        model_front_path = os.getenv("MODEL_FRONT_PATH", "./models/front_model")
        blacklist_1w_path = os.getenv("BLACKLIST_1W_PATH", "./data/blacklist_1w.json")
        high_sensitive_keywords_path = os.getenv("HIGH_SENSITIVE_KEYWORDS_PATH", "./data/high_sensitive_keywords.json")
        
        interceptor = FrontInterceptor(
            model_front_path=model_front_path,
            blacklist_1w_path=blacklist_1w_path,
            high_sensitive_keywords_path=high_sensitive_keywords_path
        )
        logger.info("前拦截API服务启动成功")
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise

@app.post("/intercept", response_model=InterceptResponse)
async def front_intercept(request: TextRequest):
    """
    前拦截API接口
    处理逻辑：
    1. 首先检查高敏感词，如果匹配直接拦截
    2. 如果没有高敏感词，使用BERT双阈值判断
    3. flag=0直接拦截，flag=1直接通过，flag=2检查敏感关键词
    4. flag=2时：匹配到敏感关键词拦截，否则通过
    """
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")

        # 1. 检查高敏感关键词
        high_sensitive_matches = interceptor.check_high_sensitive_keywords(text)
        if high_sensitive_matches:
            # 记录详细日志
            logger.info(f"前拦截触发 - 匹配到高敏感关键词: {high_sensitive_matches}")
            return InterceptResponse(
                is_safe=False,
                safety_response=None  # 不返回具体消息，由主API处理
            )

        # 2. 使用BERT双阈值判断
        flag, bad_sentences, bad_score, sentence_score = interceptor.bert_judge_front2(text)
        
        if flag == 0:  # 直接拦截
            logger.info(f"前拦截触发 - BERT双阈值判断为直接拦截, 问题句子: {bad_sentences}, 分数: {bad_score}")
            return InterceptResponse(
                is_safe=False,
                safety_response=None  # 不返回具体消息，由主API处理
            )
        elif flag == 1:  # 直接通过
            logger.info(f"前拦截通过 - BERT双阈值判断为直接通过")
            return InterceptResponse(
                is_safe=True
            )
        else:  # flag == 2，未确定，需要检查敏感关键词
            sensitive_matches = interceptor.check_sensitive_keywords(text)
            if sensitive_matches:
                logger.info(f"前拦截触发 - BERT双阈值判断未确定，匹配到敏感关键词: {sensitive_matches}")
                return InterceptResponse(
                    is_safe=False,
                    safety_response=interceptor.safety_response
                )
            else:
                logger.info(f"前拦截通过 - BERT双阈值判断未确定，未匹配敏感关键词")
                return InterceptResponse(
                    is_safe=True
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"前拦截处理出错: {e}")
        # 出错时返回不安全，避免风险
        return InterceptResponse(
            is_safe=False,
            safety_response=interceptor.safety_response
        )

@app.post("/intercept_detailed", response_model=DetailedInterceptResponse)
async def front_intercept_detailed(request: TextRequest):
    """
    前拦截API接口（详细版本，用于内部调用）
    返回详细的拦截信息，包括原因、匹配关键词等
    """
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")

        # 1. 检查高敏感关键词
        high_sensitive_matches = interceptor.check_high_sensitive_keywords(text)
        if high_sensitive_matches:
            return DetailedInterceptResponse(
                is_safe=False,
                reason="匹配到高敏感关键词",
                matched_keywords=high_sensitive_matches,
                safety_response=interceptor.safety_response
            )

        # 2. 使用BERT双阈值判断
        flag, bad_sentences, bad_score, sentence_score = interceptor.bert_judge_front2(text)
        
        bert_results = {
            "bad_sentences": bad_sentences,
            "bad_scores": bad_score,
            "sentence_scores": sentence_score,
            "bert_flag": flag
        }
        
        if flag == 0:  # 直接拦截
            return DetailedInterceptResponse(
                is_safe=False,
                reason="BERT双阈值判断为直接拦截",
                bert_results=bert_results,
                safety_response=interceptor.safety_response
            )
        elif flag == 1:  # 直接通过
            return DetailedInterceptResponse(
                is_safe=True,
                reason="BERT双阈值判断为直接通过",
                bert_results=bert_results
            )
        else:  # flag == 2，未确定，需要检查敏感关键词
            sensitive_matches = interceptor.check_sensitive_keywords(text)
            if sensitive_matches:
                return DetailedInterceptResponse(
                    is_safe=False,
                    reason="BERT双阈值判断未确定，匹配到敏感关键词",
                    matched_keywords=sensitive_matches,
                    bert_results=bert_results,
                    safety_response=interceptor.safety_response
                )
            else:
                return DetailedInterceptResponse(
                    is_safe=True,
                    reason="BERT双阈值判断未确定，未匹配敏感关键词",
                    bert_results=bert_results
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"前拦截详细处理出错: {e}")
        # 出错时返回不安全，避免风险
        return DetailedInterceptResponse(
            is_safe=False,
            reason=f"处理出错: {str(e)}",
            safety_response=interceptor.safety_response
        )

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "front_intercept"}

@app.get("/info")
async def get_info():
    """获取服务信息"""
    return {
        "service": "前拦截API服务",
        "description": "提供高敏感词直接拦截和BERT双阈值前拦截功能",
        "logic": "1. 检查高敏关键词->直接拦截 2. BERT双阈值判断 3. flag=0直接拦截，flag=1直接通过，flag=2检查敏感关键词",
        "endpoints": {
            "/intercept": "前拦截检查",
            "/health": "健康检查",
            "/info": "服务信息"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
