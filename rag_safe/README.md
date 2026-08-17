# 安全RAG系统

公开仓库只保留很小的示例语料和检索代码。
`sample_corpus.jsonl` 是占位文件，真实语料请在审核后单独接入。

## 组件

- `rag_1.py`: 混合检索器
- `server.py`: FastAPI 服务

## 运行

```bash
python server.py
```

## 接口

- `GET /health`
- `POST /retrieve`

## 说明

通过 `RAG_DATA_PATH` 指向你自己的语料文件，公开仓库不包含真实数据集。
