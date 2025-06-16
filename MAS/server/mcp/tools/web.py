"""
网络请求相关的 MCP 工具
"""
import aiohttp
import json
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from ..base import MCPTool, ToolDefinition, ToolParameter, ToolResult


class HttpRequestTool(MCPTool):
    """发送 HTTP 请求"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="http_request",
            description="Send an HTTP request and get the response",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to send the request to"
                ),
                ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP method (GET, POST, PUT, DELETE, etc.)",
                    required=False,
                    default="GET",
                    enum=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                ),
                ToolParameter(
                    name="headers",
                    type="object",
                    description="HTTP headers as key-value pairs",
                    required=False,
                    default={}
                ),
                ToolParameter(
                    name="body",
                    type="string",
                    description="Request body (for POST, PUT, PATCH)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="json_body",
                    type="object",
                    description="JSON request body (will be serialized)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds",
                    required=False,
                    default=30
                )
            ],
            returns="object"
        )
    
    async def execute(self, url: str, method: str = "GET", 
                     headers: Dict[str, str] = None, 
                     body: str = None, 
                     json_body: Dict[str, Any] = None,
                     timeout: int = 30) -> ToolResult:
        try:
            headers = headers or {}
            
            # 处理请求体
            data = None
            if json_body is not None:
                data = json.dumps(json_body)
                headers['Content-Type'] = 'application/json'
            elif body is not None:
                data = body
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    # 读取响应
                    response_text = await response.text()
                    
                    # 尝试解析为 JSON
                    response_json = None
                    try:
                        response_json = json.loads(response_text)
                    except:
                        pass
                    
                    result = {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": response_text,
                        "json": response_json
                    }
                    
                    return ToolResult(
                        success=True,
                        result=result,
                        metadata={
                            "url": str(response.url),
                            "method": method
                        }
                    )
        except aiohttp.ClientTimeout:
            return ToolResult(
                success=False,
                result=None,
                error=f"Request timeout after {timeout} seconds"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class WebScrapeTool(MCPTool):
    """网页内容抓取"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_scrape",
            description="Scrape text content from a web page",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to scrape"
                ),
                ToolParameter(
                    name="selector",
                    type="string",
                    description="CSS selector to extract specific content",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="extract_links",
                    type="boolean",
                    description="Extract all links from the page",
                    required=False,
                    default=False
                )
            ],
            returns="object"
        )
    
    async def execute(self, url: str, selector: str = None, 
                     extract_links: bool = False) -> ToolResult:
        try:
            from bs4 import BeautifulSoup
            
            # 获取网页内容
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()
            
            # 解析 HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            result = {}
            
            # 提取标题
            title = soup.find('title')
            result['title'] = title.text if title else None
            
            # 提取指定内容
            if selector:
                elements = soup.select(selector)
                result['selected_content'] = [elem.get_text(strip=True) for elem in elements]
            else:
                # 提取所有文本
                result['text'] = soup.get_text(strip=True)
            
            # 提取链接
            if extract_links:
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # 转换相对链接为绝对链接
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(url, href)
                    links.append({
                        'text': link.get_text(strip=True),
                        'href': href
                    })
                result['links'] = links
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "url": url,
                    "content_length": len(html)
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


def register_web_tools(registry):
    """注册网络工具"""
    registry.register(HttpRequestTool(), category="web")
    registry.register(WebScrapeTool(), category="web")
