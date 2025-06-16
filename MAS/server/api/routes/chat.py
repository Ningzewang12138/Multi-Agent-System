from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import json
import sys
import os
import logging
import time
import asyncio
from server.services.vector_db_service import VectorDBService
from server.services.embedding_manager import EmbeddingManager
from server.mcp.manager import mcp_manager, ToolCall
# 使用极简版本
try:
    from server.services.tool_enhanced_chat_service_minimal import ToolEnhancedChatService
except ImportError:
    try:
        from server.services.tool_enhanced_chat_service_intent_fixed import ToolEnhancedChatService
    except ImportError:
        try:
            from server.services.tool_enhanced_chat_service_intent import ToolEnhancedChatService
        except ImportError:
            try:
                from server.services.tool_enhanced_chat_service_ultra_simple import ToolEnhancedChatService
            except ImportError:
                try:
                    from server.services.tool_enhanced_chat_service_simple import ToolEnhancedChatService
                except ImportError:
                    try:
                        from server.services.tool_enhanced_chat_service_v2 import ToolEnhancedChatService
                    except ImportError:
                        from server.services.tool_enhanced_chat_service import ToolEnhancedChatService


# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, server_dir)

from server.services.ollama_service import OllamaService

# 创建 logger 实例
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = Field(default=None, description="Model name or 'auto' for automatic selection")
    messages: List[ChatMessage]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Available tools in OpenAI format")
    tool_choice: Optional[str] = Field(default="auto", description="Tool choice strategy: auto, none, or specific tool name")
    session_id: Optional[str] = Field(default=None, description="Session ID for workspace management")

def get_ollama_service(request: Request) -> OllamaService:
    """从 FastAPI 应用状态获取 OllamaService"""
    return request.app.state.services.ollama_service

def get_tool_chat_service(request: Request) -> ToolEnhancedChatService:
    """获取工具增强的聊天服务"""
    ollama_service = request.app.state.services.ollama_service
    if not hasattr(request.app.state.services, 'tool_chat_service'):
        request.app.state.services.tool_chat_service = ToolEnhancedChatService(
            ollama_service
        )
    return request.app.state.services.tool_chat_service

@router.post("/completions")
async def chat_completions(
    request: Request,
    chat_request: ChatRequest,
    ollama: OllamaService = Depends(get_ollama_service),
    tool_chat: ToolEnhancedChatService = Depends(get_tool_chat_service)
):
    """处理聊天请求（支持工具调用）"""
    if ollama is None:
        logger.error("OllamaService is not initialized")
        raise HTTPException(status_code=503, detail="Service not available")
    
    # 如果没有指定模型，使用默认模型
    model = chat_request.model
    if not model:
        model = ollama.get_default_model()
        if not model:
            raise HTTPException(status_code=503, detail="No models available")
        logger.info(f"No model specified, using default: {model}")
    
    # 检查是否需要工具调用
    if chat_request.tools and len(chat_request.tools) > 0:
        # 使用工具增强的聊天服务
        logger.info(f"Processing chat with {len(chat_request.tools)} tools available")
        
        try:
            messages = [{"role": msg.role, "content": msg.content} 
                       for msg in chat_request.messages]
            
            if chat_request.stream:
                # 流式响应
                async def generate():
                    async for chunk in tool_chat.chat_with_tools_stream(
                        model=model,
                        messages=messages,
                        tools=chat_request.tools,
                        tool_choice=chat_request.tool_choice,
                        temperature=chat_request.temperature,
                        session_id=chat_request.session_id,
                        device_id=request.headers.get('X-Device-ID', 'default'),
                        max_tokens=chat_request.max_tokens
                    ):
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    media_type="text/event-stream",
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                    }
                )
            else:
                # 非流式响应
                result = await tool_chat.chat_with_tools(
                    model=model,
                    messages=messages,
                    tools=chat_request.tools,
                    tool_choice=chat_request.tool_choice,
                    temperature=chat_request.temperature,
                    session_id=chat_request.session_id,
                    device_id=request.headers.get('X-Device-ID', 'default'),
                    max_tokens=chat_request.max_tokens
                )
                return result
                
        except Exception as e:
            logger.error(f"Tool-enhanced chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 原有的聊天逻辑（不带工具）
    try:
        messages = [{"role": msg.role, "content": msg.content} 
                   for msg in chat_request.messages]
        
        logger.info(f"Processing chat request for model: {model}")
        logger.info(f"Stream mode: {chat_request.stream}")
        
        if chat_request.stream:
            def generate():
                try:
                    for chunk in ollama.chat(
                        model=model,
                        messages=messages,
                        stream=True,
                        temperature=chat_request.temperature
                    ):
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                }
            )
        else:
            # 非流式响应
            try:
                logger.info("Calling ollama.chat with non-stream mode")
                result = ollama.chat(
                    model=model,
                    messages=messages,
                    stream=False,
                    temperature=chat_request.temperature
                )
                
                logger.info(f"Received result type: {type(result)}")
                logger.info(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
                logger.debug(f"Full result: {json.dumps(result, ensure_ascii=False)[:500]}...")
                
                # 检查响应格式
                if not isinstance(result, dict):
                    raise ValueError(f"Expected dict response, got {type(result)}")
                
                # 获取消息内容和实际使用的模型
                message = result.get("message", {})
                actual_model = result.get("model", model)
                
                if not message:
                    logger.error(f"No message in response: {result}")
                    message = {"role": "assistant", "content": ""}
                
                # 构建响应
                response = {
                    "id": "chatcmpl-" + str(abs(hash(str(messages))))[:8],
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": actual_model,  # 返回实际使用的模型
                    "choices": [{
                        "index": 0,
                        "message": message,
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_tokens": (result.get("prompt_eval_count", 0) + 
                                       result.get("eval_count", 0))
                    }
                }
                
                logger.info(f"Successfully formatted response using model: {actual_model}")
                return response
                
            except Exception as e:
                logger.error(f"Error in non-stream chat: {type(e).__name__}: {e}")
                logger.error(f"Error details: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models(
    request: Request,
    ollama: OllamaService = Depends(get_ollama_service)
):
    """获取可用模型列表"""
    if ollama is None:
        logger.error("OllamaService is not initialized")
        raise HTTPException(status_code=503, detail="Service not available")
        
    try:
        models = ollama.list_models()
        default_model = ollama.get_default_model()
        
        # 在响应中标记默认模型
        for model in models:
            model["is_default"] = (model["name"] == default_model)
        
        return {
            "data": models,
            "default_model": default_model,
            "object": "list"
        }
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh-models")
async def refresh_models(
    request: Request,
    ollama: OllamaService = Depends(get_ollama_service)
):
    """刷新模型列表"""
    if ollama is None:
        logger.error("OllamaService is not initialized")
        raise HTTPException(status_code=503, detail="Service not available")
    
    try:
        ollama.refresh_models()
        models = ollama.list_models()
        default_model = ollama.get_default_model()
        
        return {
            "message": "Models refreshed successfully",
            "model_count": len(models),
            "default_model": default_model
        }
    except Exception as e:
        logger.error(f"Failed to refresh models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 添加新的数据模型
class RAGChatRequest(BaseModel):
    model: Optional[str] = Field(default=None, description="Model name or 'auto' for automatic selection")
    messages: List[ChatMessage]
    knowledge_base_id: str = Field(..., description="Knowledge base to search")
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    search_limit: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")
    use_rerank: bool = Field(default=False, description="Whether to use reranking")

# 添加 RAG 聊天端点
@router.post("/rag/completions")
async def rag_chat_completions(
    request: Request,
    chat_request: RAGChatRequest,
    ollama: OllamaService = Depends(get_ollama_service)
):
    """使用知识库进行 RAG 聊天"""
    services = request.app.state.services
    
    if not services.vector_db_service or not services.embedding_manager:
        raise HTTPException(status_code=503, detail="RAG services not available")
    
    try:
        # 获取最后一条用户消息作为查询
        user_messages = [msg for msg in chat_request.messages if msg.role == "user"]
        if not user_messages:
            raise ValueError("No user message found")
        
        query = user_messages[-1].content
        
        # 搜索知识库
        logger.info(f"Searching knowledge base {chat_request.knowledge_base_id} for: {query}")
        query_embedding = services.embedding_manager.embed_text(query)
        
        search_results = services.vector_db_service.search(
            collection_name=chat_request.knowledge_base_id,
            query_embedding=query_embedding,
            n_results=chat_request.search_limit
        )
        
        # 构建上下文
        context_parts = []
        for i, result in enumerate(search_results["results"]):
            context_parts.append(f"[Document {i+1}]:\n{result['document']}")
        
        context = "\n\n".join(context_parts)
        
        # 构建增强的提示
        system_prompt = f"""You are a helpful assistant with access to a knowledge base. 
Use the following context to answer the user's question. 
If the context doesn't contain relevant information, say so and provide the best answer you can based on your general knowledge.

Context from knowledge base:
{context}

Remember to:
1. Be accurate and cite information from the context when relevant
2. If the context doesn't fully answer the question, acknowledge this
3. Provide a clear and helpful response"""
        
        # 修改消息列表，添加系统提示
        enhanced_messages = [{"role": "system", "content": system_prompt}]
        enhanced_messages.extend([{"role": msg.role, "content": msg.content} for msg in chat_request.messages])
        
        # 获取模型
        model = chat_request.model
        if not model:
            model = ollama.get_default_model()
            if not model:
                raise HTTPException(status_code=503, detail="No models available")
        
        # 调用 LLM
        if chat_request.stream:
            def generate():
                try:
                    # 先返回搜索结果元数据
                    yield f"data: {json.dumps({'type': 'search_results', 'count': len(search_results['results'])})}\n\n"
                    
                    # 然后流式返回 LLM 响应
                    for chunk in ollama.chat(
                        model=model,
                        messages=enhanced_messages,
                        stream=True,
                        temperature=chat_request.temperature
                    ):
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"RAG streaming error: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                }
            )
        else:
            # 非流式响应
            result = ollama.chat(
                model=model,
                messages=enhanced_messages,
                stream=False,
                temperature=chat_request.temperature
            )
            
            # 添加搜索结果到响应
            response = {
                "id": "chatcmpl-rag-" + str(abs(hash(str(enhanced_messages))))[:8],
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": result.get("message", {"role": "assistant", "content": ""}),
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": (result.get("prompt_eval_count", 0) + 
                                   result.get("eval_count", 0))
                },
                "search_results": {
                    "count": len(search_results["results"]),
                    "documents": [
                        {
                            "id": r["id"],
                            "content": r["document"][:200] + "..." if len(r["document"]) > 200 else r["document"],
                            "metadata": r["metadata"]
                        } for r in search_results["results"][:3]  # 只返回前3个
                    ]
                }
            }
            
            return response
            
    except Exception as e:
        logger.error(f"RAG chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))    