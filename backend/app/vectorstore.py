import os
import uuid
from typing import List
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from .scanner import CodeChunk


CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "chroma_db"
)


class Document:
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}


def _sanitize_metadata_value(value) -> str:
    """清理元数据值中的潜在危险字符，避免 ChromaDB 解析报错。"""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace("\\", "/")
    value = value.replace("\x00", "")
    return value


def _sanitize_metadata(metadata: dict) -> dict:
    """清理整个 metadata dict，确保所有字符串值是安全的。"""
    if not metadata:
        return {}
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = _sanitize_metadata_value(value)
    return sanitized


def _create_embedding_function():
    try:
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
        )
    except Exception:
        pass

    try:
        return embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        pass

    return None


class VectorStore:
    def __init__(self, collection_name: str = "code_audit", persist_directory: str = None):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or CHROMA_PERSIST_DIR
        self._client = None
        self._embedding_fn = None

    @property
    def client(self):
        if self._client is None:
            persist_path = Path(self.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(persist_path))
        return self._client

    @property
    def embedding_fn(self):
        if self._embedding_fn is None:
            self._embedding_fn = _create_embedding_function()
            if self._embedding_fn is None:
                raise RuntimeError(
                    "无法初始化 embedding 函数。请安装 sentence-transformers: "
                    "pip install sentence-transformers"
                )
        return self._embedding_fn

    def _get_or_create_collection(self, project_id: str):
        collection_name = f"{self.collection_name}_{project_id}"
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
        )

    def index_chunks(self, chunks: List[CodeChunk], project_id: str = "default") -> int:
        if not chunks:
            return 0

        collection = self._get_or_create_collection(project_id)

        if collection.count() > 0:
            try:
                all_ids = collection.get()["ids"]
                if all_ids:
                    collection.delete(ids=all_ids)
            except Exception:
                pass

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            ids.append(chunk_id)
            documents.append(chunk.content)
            raw_metadata = {
                "file_path": chunk.file_path,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "file_type": chunk.file_type,
            }
            metadatas.append(_sanitize_metadata(raw_metadata))

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            collection.add(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
            )

        return len(chunks)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        project_id: str = "default",
    ) -> List[Document]:
        if not self.has_index(project_id):
            return []

        collection = self._get_or_create_collection(project_id)
        results = collection.query(
            query_texts=[query],
            n_results=k,
        )

        documents = []
        if results["documents"] and len(results["documents"]) > 0:
            for i, doc_text in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                documents.append(Document(
                    page_content=doc_text,
                    metadata=_sanitize_metadata(metadata),
                ))

        return documents

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        project_id: str = "default",
    ) -> List[tuple]:
        if not self.has_index(project_id):
            return []

        collection = self._get_or_create_collection(project_id)
        results = collection.query(
            query_texts=[query],
            n_results=k,
        )

        docs_with_scores = []
        if results["documents"] and len(results["documents"]) > 0:
            for i, doc_text in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                doc = Document(
                    page_content=doc_text,
                    metadata=_sanitize_metadata(metadata),
                )
                docs_with_scores.append((doc, distance))

        return docs_with_scores

    def has_index(self, project_id: str = "default") -> bool:
        try:
            collection = self._get_or_create_collection(project_id)
            return collection.count() > 0
        except Exception:
            return False
