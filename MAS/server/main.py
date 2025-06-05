from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import sys
import os
from server.services.embedding_manager import EmbeddingManager


# 将当前文件的父目录添加到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 现在使用绝对导入
from server.api.routes import chat, knowledge, system
from server.services.ollama_service import OllamaService
from server.services.vector_db_service import VectorDBService
from server.services.document_processor import DocumentProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建一个服务容器类
class ServiceContainer:
    ollama_service: OllamaService = None
    embedding_manager: EmbeddingManager = None  
    vector_db_service: VectorDBService = None
    document_processor: DocumentProcessor = None

# 全局服务容器实例
services = ServiceContainer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    logger.info("Initializing services...")
    
    # 初始化 Ollama 服务
    services.ollama_service = OllamaService()
    logger.info("Ollama service initialized")
    
    # 初始化嵌入服务
    # 初始化嵌入管理器
    services.embedding_manager = EmbeddingManager()

# 尝试初始化不同的嵌入服务
    embedding_initialized = False

# 1. 尝试 Sentence-Transformers
    try:
        from server.services.embedding_service import EmbeddingService
        st_service = EmbeddingService()
        services.embedding_manager.register_service(
            "sentence-transformers", 
            st_service,
            set_as_default=True  # 先设为默认
        )
        logger.info("Registered sentence-transformers embedding service")
        embedding_initialized = True
    except Exception as e:
        logger.warning(f"Failed to initialize sentence-transformers: {e}")

# 2. 尝试 Ollama 嵌入
    try:
        from server.services.ollama_embedding_service import OllamaEmbeddingService
        ollama_service = OllamaEmbeddingService()
        services.embedding_manager.register_service(
            "ollama",
            ollama_service,
            set_as_default=not embedding_initialized  # 如果是第一个成功的，设为默认
        )
        logger.info("Registered Ollama embedding service")
        embedding_initialized = True
    except Exception as e:
        logger.warning(f"Failed to initialize Ollama embedding service: {e}")

    if not embedding_initialized:
        logger.error("No embedding service could be initialized!")
        logger.warning("RAG features will be disabled")
        services.embedding_manager = None
    else:
        logger.info(f"Default embedding service: {services.embedding_manager.default_service}")    
    
    # 初始化向量数据库
    try:
        services.vector_db_service = VectorDBService()
        logger.info("Vector database service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector database: {e}")
        logger.warning("Knowledge base features will be disabled")
    
    # 初始化文档处理器
    services.document_processor = DocumentProcessor()
    logger.info("Document processor initialized")
    
    # 将服务容器添加到 app.state
    app.state.services = services
    
    yield
    
    # 关闭时清理
    logger.info("Shutting down...")

# 创建FastAPI应用
app = FastAPI(
    title="Multi-Agent System API",
    description="跨平台多Agent系统的API服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS，允许移动端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(system.router, prefix="/api/system", tags=["System"])

@app.get("/")
async def root():
    return {
        "message": "Multi-Agent System API",
        "version": "1.0.0",
        "status": "running",
        "features": {
            "chat": True,
            "knowledge_base": services.vector_db_service is not None,
            "embeddings": services.embedding_manager is not None and services.embedding_manager.default_service is not None
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )