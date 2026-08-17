# simple_server.py - 简化版API服务
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime

from rag_1 import HybridRetriever

app = FastAPI(title="混合检索API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever = None


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


@app.on_event("startup")
async def startup_event():
    global retriever
    print("正在初始化检索器...")
    try:
        retriever = HybridRetriever(
            file_path=os.getenv("RAG_DATA_PATH", "./data/sample_corpus.jsonl"),
            chunk_size=768,
            chunk_overlap=50,
            language="chinese",
            bm25_top_k=5,
            vector_top_k=5,
            hybrid_top_k=10
        )
        retriever.initialize()
        print("检索器初始化成功！")
    except Exception as e:
        print(f"初始化失败: {e}")
        raise


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "retriever_loaded": retriever is not None,
        "timestamp": str(datetime.now())
    }


@app.post("/retrieve")
async def retrieve(request: QueryRequest):
    """简化的检索接口，直接返回节点"""
    if not retriever:
        raise HTTPException(status_code=503, detail="检索器未初始化")

    try:
        # 直接调用hybrid_retriever的retrieve方法
        nodes = retriever.hybrid_retriever.retrieve(request.query)

        # 格式化结果
        results = []
        for i, node in enumerate(nodes[:request.top_k]):
            results.append({
                "rank": i + 1,
                "score": float(node.score),
                "node_id": node.node_id,
                "text": node.text,
                "metadata": node.metadata if hasattr(node, 'metadata') else {}
            })

        return {
            "query": request.query,
            "timestamp": str(datetime.now()),
            "num_results": len(results),
            "results": results
        }

    except Exception as e:
        print(f"检索错误详情: {e}")  # 打印详细错误
        import traceback
        traceback.print_exc()  # 打印完整堆栈
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
