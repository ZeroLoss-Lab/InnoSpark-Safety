from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import torch
import re
import logging
from typing import Dict, Any, Optional, List
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="后拦截API服务", description="BERT后拦截服务")

class TextRequest(BaseModel):
    text: str

class PostInterceptResponse(BaseModel):
    is_safe: bool
    safety_response: Optional[str] = None

class DetailedPostInterceptResponse(BaseModel):
    is_safe: bool
    reason: str
    bert_results: Optional[Dict[str, Any]] = None
    safety_response: Optional[str] = None

class PostInterceptor:
    def __init__(self, model_post_path: str):
        self.model_dir_post = model_post_path
        # Safe API 不需要管理安全响应消息，只负责拦截判断
        # 安全响应消息由主 API 统一管理
        
        # 加载BERT模型
        self._load_model()
        
        logger.info("后拦截服务初始化完成")

    def _load_model(self):
        """加载BERT模型"""
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 加载tokenizer
            self.tokenizer_post = AutoTokenizer.from_pretrained(
                self.model_dir_post, 
                use_fast=True
            )
            
            # 正常加载模型，不使用量化
            self.model_post = AutoModelForSequenceClassification.from_pretrained(
                self.model_dir_post
            )
            
            self.classifier_post = pipeline(
                "text-classification", 
                model=self.model_post, 
                tokenizer=self.tokenizer_post, 
                device=device,
                max_length=512,
                truncation=True
            )
            
            logger.info(f"后拦截模型加载完成，使用设备: {device}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def bert_judge_post(self, text: str, thr=None) -> tuple:
        """后拦截BERT判断"""
        try:
            # 从环境变量获取阈值，如果参数未提供
            if thr is None:
                thr = float(os.getenv("BERT_POST_THRESHOLD", "0.5"))
            
            # 预处理
            text = text.replace("*", "").replace("#", "")
            sentences = re.split(r'(?<=[\u3002.])', text)  # 正向零宽断言保留句号或英文句号
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]  # 去除空段和长度小于等于5的字符串
            
            if not sentences:
                return True, [], [], {}

            # 模型分类
            bad_sentences = []
            output = self.classifier_post(sentences)
            
            judgelist = list([x['label'] for x in output])
            flag = True  # True表示通过，False表示拦截
            bad_score = []
            all_score = [x['score'] for x in output]
            sentence_score = dict(zip(sentences, [round(v, 2) for v in all_score]))
            
            for i, item in enumerate(output):
                if item["label"] == "LABEL_0" and item["score"] >= thr:
                    # LABEL_0表示有害，分数高于阈值则拦截
                    flag = False
                    bad_sentences.append(sentences[i])
                    bad_score.append(item['score'])
                    
            return flag, bad_sentences, bad_score, sentence_score
            
        except Exception as e:
            logger.error(f"BERT后拦截判断出错: {e}")
            # 出错时返回不安全，避免风险
            return False, [text], [0.0], {}

# 初始化拦截器实例
interceptor = None

@app.on_event("startup")
async def startup_event():
    global interceptor
    try:
        # 这里需要根据实际情况修改路径
        model_post_path = os.getenv("MODEL_POST_PATH", "./models/post_model")
        
        interceptor = PostInterceptor(model_post_path=model_post_path)
        logger.info("后拦截API服务启动成功")
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise

@app.post("/intercept", response_model=PostInterceptResponse)
async def post_intercept(request: TextRequest):
    """
    后拦截API接口
    使用BERT模型对文本进行安全性判断
    """
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")

        # 使用BERT模型进行后拦截判断
        flag, bad_sentences, bad_score, sentence_score = interceptor.bert_judge_post(text)
        
        if not flag:  # BERT判断为不安全
            logger.info(f"后拦截触发 - BERT判断为不安全, 问题句子: {bad_sentences}, 分数: {bad_score}")
            return PostInterceptResponse(
                is_safe=False,
                safety_response=None  # 不返回具体消息，由主API处理
            )
        else:
            logger.info(f"后拦截通过 - BERT判断为安全")
            return PostInterceptResponse(
                is_safe=True
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后拦截处理出错: {e}")
        # 出错时返回不安全，避免风险
        return PostInterceptResponse(
            is_safe=False,
            safety_response=None  # 不返回具体消息，由主API处理
        )

@app.post("/intercept_detailed", response_model=DetailedPostInterceptResponse)
async def post_intercept_detailed(request: TextRequest):
    """
    后拦截API接口（详细版本，用于内部调用）
    返回详细的拦截信息，包括BERT结果等
    """
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")

        # 使用BERT模型进行后拦截判断
        flag, bad_sentences, bad_score, sentence_score = interceptor.bert_judge_post(text)
        
        bert_results = {
            "bad_sentences": bad_sentences,
            "bad_scores": bad_score,
            "sentence_scores": sentence_score
        }
        
        if not flag:  # BERT判断为不安全
            return DetailedPostInterceptResponse(
                is_safe=False,
                reason="BERT后拦截判断为不安全",
                bert_results=bert_results,
                safety_response=interceptor.safety_response
            )
        else:
            return DetailedPostInterceptResponse(
                is_safe=True,
                reason="BERT后拦截判断为安全",
                bert_results=bert_results
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后拦截详细处理出错: {e}")
        # 出错时返回不安全，避免风险
        return DetailedPostInterceptResponse(
            is_safe=False,
            reason=f"处理出错: {str(e)}",
            safety_response=interceptor.safety_response
        )

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "post_intercept"}

@app.get("/info")
async def get_info():
    """获取服务信息"""
    return {
        "service": "后拦截API服务",
        "description": "提供BERT后拦截功能，对文本内容进行安全性判断",
        "endpoints": {
            "/intercept": "后拦截检查",
            "/health": "健康检查",
            "/info": "服务信息"
        },
        "model_info": {
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "optimization": "标准加载"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
