"""
RAG服务模块
提供检索增强生成功能
"""

import logging
from typing import List, Dict, Any, Optional
from server.services.vector_db_service import VectorDBService
from server.services.embedding_manager import EmbeddingManager
from server.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

class RAGService:
    """RAG服务类"""
    
    def __init__(
        self,
        vector_db_service: VectorDBService,
        embedding_manager: EmbeddingManager,
        ollama_service: OllamaService
    ):
        self.vector_db = vector_db_service
        self.embedding_manager = embedding_manager
        self.ollama = ollama_service
    
    def search_knowledge_base(
        self,
        knowledge_base_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_manager.embed_text(query)
            
            # 搜索向量数据库
            results = self.vector_db.search(
                collection_name=knowledge_base_id,
                query_embedding=query_embedding,
                n_results=limit
            )
            
            return results["results"]
        except Exception as e:
            logger.error(f"Knowledge base search error: {e}")
            raise
    
    def generate_rag_response(
        self,
        query: str,
        context_documents: List[str],
        model: str,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """基于检索结果生成回答"""
        # 构建上下文
        context = "\n\n".join([
            f"[Document {i+1}]:\n{doc}"
            for i, doc in enumerate(context_documents)
        ])
        
        # 构建系统提示
        if not system_prompt:
            system_prompt = """You are a helpful assistant with access to a knowledge base. 
Use the following context to answer the user's question accurately.
If the context doesn't contain relevant information, acknowledge this and provide the best answer based on your general knowledge.

Context from knowledge base:
{context}"""
        
        system_prompt = system_prompt.format(context=context)
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        # 调用LLM
        response = self.ollama.chat(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature
        )
        
        return response["message"]["content"]
    
    def rag_query(
        self,
        knowledge_base_id: str,
        query: str,
        model: str,
        search_limit: int = 5,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """执行完整的RAG查询"""
        # 搜索相关文档
        search_results = self.search_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            query=query,
            limit=search_limit
        )
        
        # 提取文档内容
        context_documents = [result["document"] for result in search_results]
        
        # 生成回答
        response = self.generate_rag_response(
            query=query,
            context_documents=context_documents,
            model=model,
            temperature=temperature
        )
        
        return {
            "response": response,
            "sources": search_results,
            "model": model
        }
