# 1. 导入必要的包
import nest_asyncio
import os
import json
from pathlib import Path
from typing import List
from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb
import Stemmer
from llama_index.core import Settings

# 在初始化任何组件之前设置
Settings.llm = None
# 应用nest_asyncio以支持异步操作
nest_asyncio.apply()


class HybridRetriever:
    """混合检索器类"""

    def __init__(
            self,
            file_path: str,
            chunk_size: int = 512,
            chunk_overlap: int = 50,
            language: str = "chinese",
            bm25_top_k: int = 3,
            vector_top_k: int = 3,
            hybrid_top_k: int = 5,
            embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        初始化混合检索器

        Args:
            file_path: 输入文件路径（支持txt或jsonl格式）
            chunk_size: 文档分块大小
            chunk_overlap: 块之间的重叠
            language: 语言设置 ("english" 或 "chinese")
            bm25_top_k: BM25检索返回的结果数
            vector_top_k: 向量检索返回的结果数
            hybrid_top_k: 混合检索最终返回的结果数
            embedding_model: 嵌入模型名称
        """
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.language = language
        self.bm25_top_k = bm25_top_k
        self.vector_top_k = vector_top_k
        self.hybrid_top_k = hybrid_top_k

        # 根据文件名自动生成存储路径
        file_stem = self.file_path.stem  # 获取文件名（不含扩展名）
        self.storage_dir = Path(f"./storage_{file_stem}")
        self.storage_dir.mkdir(exist_ok=True)

        # 存储路径
        self.docstore_path = self.storage_dir / "docstore.json"
        self.bm25_path = self.storage_dir / "bm25_retriever"
        self.chroma_path = self.storage_dir / "chroma_db"

        # 设置embedding模型
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=embedding_model,
            device="cuda"
        )

        # 检索器组件
        self.index = None
        self.bm25_retriever = None
        self.docstore = None
        self.vector_retriever = None
        self.hybrid_retriever = None

    def load_jsonl_documents(self, file_path: str) -> List[Document]:
        """加载JSONL格式的文档"""
        documents = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():  # 跳过空行
                    try:
                        data = json.loads(line)
                        # 假设每行JSON有一个'text'字段，你可以根据实际格式调整
                        if isinstance(data, dict) and 'text' in data:
                            text = data['text']
                        elif isinstance(data, str):
                            text = data
                        else:
                            # 如果是其他格式，将整个JSON转为字符串
                            text = json.dumps(data, ensure_ascii=False)

                        # 创建文档，可以添加元数据
                        metadata = {
                            'line_number': line_num,
                            'source': str(file_path)
                        }
                        # 如果JSON中有其他字段，也可以作为元数据
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if key != 'text' and isinstance(value, (str, int, float, bool)):
                                    metadata[key] = value

                        documents.append(Document(text=text, metadata=metadata))
                    except json.JSONDecodeError as e:
                        print(f"警告：第{line_num}行JSON解析失败: {e}")
                        continue

        print(f"成功加载 {len(documents)} 个文档")
        return documents

    def check_saved_indexes_exist(self) -> bool:
        """检查是否存在已保存的索引"""
        return (self.docstore_path.exists() and
                self.bm25_path.exists() and
                self.chroma_path.exists())

    def create_new_indexes(self):
        """创建新的索引"""
        # 加载文档
        print(f"正在加载文档: {self.file_path}")

        if self.file_path.suffix == '.jsonl':
            documents = self.load_jsonl_documents(str(self.file_path))
        elif self.file_path.suffix in ['.txt', '.md']:
            from llama_index.core import SimpleDirectoryReader
            documents = SimpleDirectoryReader(
                input_files=[str(self.file_path)]
            ).load_data()
        else:
            raise ValueError(f"不支持的文件格式: {self.file_path.suffix}")

        # 创建节点
        print("正在分割文档...")
        splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        nodes = splitter.get_nodes_from_documents(documents)
        print(f"创建了 {len(nodes)} 个节点")

        # 创建文档存储
        print("正在创建文档存储...")
        self.docstore = SimpleDocumentStore()
        self.docstore.add_documents(nodes)

        # 创建向量存储
        print("正在创建向量存储...")
        db = chromadb.PersistentClient(path=str(self.chroma_path))
        chroma_collection = db.get_or_create_collection("vectors")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        # 创建存储上下文和索引
        storage_context = StorageContext.from_defaults(
            docstore=self.docstore,
            vector_store=vector_store
        )

        print("正在创建向量索引...")
        self.index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            show_progress=True,
            embed_batch_size=4096
        )

        # 创建BM25检索器
        print("正在创建BM25检索器...")
        self.bm25_retriever = BM25Retriever.from_defaults(
            docstore=self.docstore,
            similarity_top_k=self.bm25_top_k,
            #stemmer=Stemmer.Stemmer(self.language),
            language=self.language
        )

        # 创建向量检索器
        self.vector_retriever = self.index.as_retriever(
            similarity_top_k=self.vector_top_k
        )

        # 保存索引
        self.save_indexes()

    def save_indexes(self):
        """保存所有索引"""
        print("正在保存索引...")
        self.docstore.persist(str(self.docstore_path))
        self.bm25_retriever.persist(str(self.bm25_path))
        print(f"索引已保存到: {self.storage_dir}")

    def load_saved_indexes(self):
        """加载已保存的索引"""
        print(f"正在加载已保存的索引: {self.storage_dir}")

        # 加载Chroma向量存储
        db = chromadb.PersistentClient(path=str(self.chroma_path))
        chroma_collection = db.get_or_create_collection("vectors")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        # 加载文档存储
        self.docstore = SimpleDocumentStore.from_persist_path(str(self.docstore_path))

        # 加载BM25检索器
        self.bm25_retriever = BM25Retriever.from_persist_dir(str(self.bm25_path))

        # 重建存储上下文和索引
        storage_context = StorageContext.from_defaults(
            docstore=self.docstore,
            vector_store=vector_store
        )
        self.index = VectorStoreIndex(nodes=[], storage_context=storage_context)

        # 创建向量检索器
        self.vector_retriever = self.index.as_retriever(
            similarity_top_k=self.vector_top_k
        )

        print("索引加载完成!")

    def initialize(self, force_rebuild: bool = False):
        """
        初始化检索器

        Args:
            force_rebuild: 是否强制重建索引
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        if force_rebuild or not self.check_saved_indexes_exist():
            if not force_rebuild and self.check_saved_indexes_exist():
                print(f"发现已存在的索引: {self.storage_dir}")
                user_input = input("是否重建索引？(y/n，默认n): ")
                if user_input.lower() != 'y':
                    self.load_saved_indexes()
                else:
                    self.create_new_indexes()
            else:
                self.create_new_indexes()
        else:
            self.load_saved_indexes()

        # 创建混合检索器
        print("正在创建混合检索器...")
        self.hybrid_retriever = QueryFusionRetriever(
            [self.vector_retriever, self.bm25_retriever],
            similarity_top_k=self.hybrid_top_k,
            num_queries=1,
            use_async=True,
            mode="simple",  # 或者尝试其他不强制需要LLM的模式，如 "simple"
            )
        print("\n=== 混合检索系统已准备就绪 ===\n")

    def retrieve(self, query: str, show_details: bool = True):
        """执行检索并展示结果"""
        print("\n" + "=" * 80)
        print(f"查询: {query}")
        print("=" * 80)

        results = {}

        # if show_details:
        #     # BM25检索结果
        #     print("\n【BM25关键词检索结果】")
        #     print("-" * 40)
        #     results['bm25'] = self.bm25_retriever.retrieve(query)
        #     for i, node in enumerate(results['bm25'], 1):
        #         print(f"\nBM25结果 {i}:")
        #         print(f"  相似度分数: {node.score:.4f}")
        #         print(f"  文本内容: {node.text[:300]}...")
        #
        #     # 向量检索结果
        #     print("\n【向量检索结果】")
        #     print("-" * 40)
        #     results['vector'] = self.vector_retriever.retrieve(query)
        #     for i, node in enumerate(results['vector'], 1):
        #         print(f"\n向量结果 {i}:")
        #         print(f"  相似度分数: {node.score:.4f}")
        #         print(f"  文本内容: {node.text[:300]}...")
        #
        # 混合检索结果
        print("\n【混合检索结果（BM25 + 向量融合）】")
        print("-" * 40)
        results['hybrid'] = self.hybrid_retriever.retrieve(query)
        for i, node in enumerate(results['hybrid'], 1):
            print(f"\n混合结果 {i}:")
            print(f"  融合分数: {node.score:.4f}")
            print(f"  文本内容: {node.text[:400]}...")

        return results


# 主程序
if __name__ == "__main__":
    # 创建检索器实例
    retriever = HybridRetriever(
        file_path=os.getenv("RAG_DATA_PATH", "./data/sample_corpus.jsonl"),
        chunk_size=512,
        chunk_overlap=50,
        language="chinese",
        bm25_top_k=3,
        vector_top_k=3,
        hybrid_top_k=5
    )

    # 初始化（自动检查是否需要创建或加载索引）
    retriever.initialize()

    # 测试查询
    test_queries = ["中央", "通讯社", "社会主义"]
    for query in test_queries:
        retriever.retrieve(query, show_details=True)

    # 交互式查询
    while True:
        user_query = input("\n输入查询（输入'exit'退出）: ")
        if user_query.lower() == 'exit':
            break
        if user_query.strip():
            retriever.retrieve(user_query)
