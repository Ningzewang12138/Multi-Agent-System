import requests
import json
from typing import Dict, Any, List, Generator, Optional, Union
import logging

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.timeout = 300  # 5分钟超时
        self._default_model = None  # 缓存默认模型
        # 初始化时测试连接
        self.test_connection()
        
    def test_connection(self):
        """测试与 Ollama 的连接"""
        try:
            # 使用 Ollama 原生 API
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            logger.info(f"Successfully connected to Ollama at {self.base_url}")
            models = response.json().get("models", [])
            logger.info(f"Found {len(models)} models")
            if models:
                logger.info(f"Available models: {[m.get('name', 'unknown') for m in models]}")
                # 设置默认模型
                self._default_model = models[0].get('name')
                logger.info(f"Default model set to: {self._default_model}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {type(e).__name__}: {e}")
    
    def get_default_model(self) -> Optional[str]:
        """获取默认模型（第一个可用的模型）"""
        if self._default_model:
            return self._default_model
            
        # 如果没有缓存，重新获取
        models = self.list_models()
        if models:
            self._default_model = models[0]["name"]
            return self._default_model
        return None
    
    def refresh_models(self):
        """刷新模型列表和默认模型"""
        logger.info("Refreshing model list...")
        models = self.list_models()
        if models:
            self._default_model = models[0]["name"]
            logger.info(f"Default model updated to: {self._default_model}")
        else:
            self._default_model = None
            logger.warning("No models available")
        
    def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表 - 使用 Ollama 原生 API"""
        try:
            logger.info(f"Requesting models from {self.base_url}/api/tags")
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Ollama 原生格式
            models = data.get("models", [])
            logger.info(f"Retrieved {len(models)} models")
            
            # 转换为统一格式
            formatted_models = []
            for model in models:
                formatted_models.append({
                    "name": model.get("name", ""),
                    "id": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", "")
                })
            
            return formatted_models
        except Exception as e:
            logger.error(f"Failed to list models: {type(e).__name__}: {e}")
            return []
    
    def chat(self, model: str, messages: List[Dict[str, str]], 
             stream: bool = False, temperature: float = 0.7) -> Union[Generator[str, None, None], Dict[str, Any]]:
        """与模型对话 - 使用 Ollama 原生 API"""
        try:
            # 如果没有指定模型或模型不存在，使用默认模型
            if not model or model == "auto":
                model = self.get_default_model()
                if not model:
                    raise ValueError("No models available in Ollama")
                logger.info(f"Using default model: {model}")
            
            # Ollama 原生请求格式
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature
                }
            }
            
            logger.info(f"Sending chat request to model: {model}, stream: {stream}")
            logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            # 如果模型不存在，尝试使用默认模型
            if response.status_code == 404 and "not found" in response.text:
                logger.warning(f"Model {model} not found, trying default model")
                self.refresh_models()  # 刷新模型列表
                default_model = self.get_default_model()
                if default_model and default_model != model:
                    payload["model"] = default_model
                    response = requests.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                        stream=stream,
                        timeout=self.timeout
                    )
            
            response.raise_for_status()
            
            if stream:
                # 流式模式：返回生成器
                def stream_generator():
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    if content:  # 只返回非空内容
                                        yield content
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse streaming response: {e}")
                return stream_generator()
            else:
                # 非流式模式：返回完整的响应字典
                result = response.json()
                logger.debug(f"Chat response: {json.dumps(result, ensure_ascii=False)[:200]}...")
                return result
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error in chat: {e}")
            logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Chat failed: {type(e).__name__}: {e}")
            raise
    
    def generate(self, model: str, prompt: str, 
                 stream: bool = False, temperature: float = 0.7) -> Union[Generator[str, None, None], Dict[str, Any]]:
        """生成文本 - 使用 Ollama 原生 API"""
        try:
            # 如果没有指定模型，使用默认模型
            if not model or model == "auto":
                model = self.get_default_model()
                if not model:
                    raise ValueError("No models available in Ollama")
                logger.info(f"Using default model: {model}")
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature
                }
            }
            
            logger.info(f"Sending generate request to model: {model}, stream: {stream}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            
            # 如果模型不存在，尝试使用默认模型
            if response.status_code == 404 and "not found" in response.text:
                logger.warning(f"Model {model} not found, trying default model")
                self.refresh_models()
                default_model = self.get_default_model()
                if default_model and default_model != model:
                    payload["model"] = default_model
                    response = requests.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        stream=stream,
                        timeout=self.timeout
                    )
            
            response.raise_for_status()
            
            if stream:
                # 流式模式：返回生成器
                def stream_generator():
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse streaming response")
                return stream_generator()
            else:
                # 非流式模式：返回完整的响应字典
                result = response.json()
                logger.debug(f"Generate response: {json.dumps(result, ensure_ascii=False)[:200]}...")
                return result
                
        except Exception as e:
            logger.error(f"Generate failed: {type(e).__name__}: {e}")
            raise