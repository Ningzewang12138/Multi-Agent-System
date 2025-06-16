"""
第三方服务 MCP 工具示例 - 高德地图
注意：使用前需要配置API密钥
"""
import aiohttp
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from ..base import MCPTool, ToolDefinition, ToolParameter, ToolResult


class AmapGeocodeTool(MCPTool):
    """高德地图地理编码工具"""
    
    def __init__(self, api_key: str = None):
        super().__init__()
        # 从环境变量或配置文件读取API密钥
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://restapi.amap.com/v3/geocode/geo"
    
    def _get_api_key(self) -> str:
        """获取API密钥"""
        import os
        # 可以从环境变量获取
        key = os.environ.get("AMAP_API_KEY")
        if not key:
            # 或者从配置文件读取
            try:
                with open("config/api_keys.json", "r") as f:
                    config = json.load(f)
                    key = config.get("amap_api_key")
            except:
                pass
        return key
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="amap_geocode",
            description="Convert address to coordinates using Amap (高德地图) API",
            parameters=[
                ToolParameter(
                    name="address",
                    type="string",
                    description="Address to geocode (地址)"
                ),
                ToolParameter(
                    name="city",
                    type="string",
                    description="City name for more accurate results (城市)",
                    required=False
                )
            ],
            returns="object"
        )
    
    async def execute(self, address: str, city: str = None) -> ToolResult:
        if not self.api_key:
            return ToolResult(
                success=False,
                result=None,
                error="Amap API key not configured. Please set AMAP_API_KEY environment variable."
            )
        
        try:
            params = {
                "key": self.api_key,
                "address": address,
                "output": "json"
            }
            if city:
                params["city"] = city
            
            url = f"{self.base_url}?{urlencode(params)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
            
            if data.get("status") == "1" and data.get("geocodes"):
                geocode = data["geocodes"][0]
                location = geocode.get("location", "").split(",")
                
                result = {
                    "formatted_address": geocode.get("formatted_address"),
                    "province": geocode.get("province"),
                    "city": geocode.get("city"),
                    "district": geocode.get("district"),
                    "location": {
                        "lng": float(location[0]) if len(location) > 0 else None,
                        "lat": float(location[1]) if len(location) > 1 else None
                    },
                    "level": geocode.get("level")
                }
                
                return ToolResult(
                    success=True,
                    result=result,
                    metadata={
                        "api": "amap",
                        "count": len(data.get("geocodes", []))
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Geocoding failed: {data.get('info', 'Unknown error')}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class AmapRoutePlanTool(MCPTool):
    """高德地图路径规划工具"""
    
    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://restapi.amap.com/v3/direction/driving"
    
    def _get_api_key(self) -> str:
        """获取API密钥"""
        import os
        key = os.environ.get("AMAP_API_KEY")
        if not key:
            try:
                with open("config/api_keys.json", "r") as f:
                    config = json.load(f)
                    key = config.get("amap_api_key")
            except:
                pass
        return key
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="amap_route_plan",
            description="Plan route between two locations using Amap (高德地图) API",
            parameters=[
                ToolParameter(
                    name="origin",
                    type="string",
                    description="Origin location (起点) - can be address or coordinates (lng,lat)"
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination location (终点) - can be address or coordinates (lng,lat)"
                ),
                ToolParameter(
                    name="strategy",
                    type="number",
                    description="Route strategy (路线策略): 0=速度最快, 1=费用最少, 2=距离最短",
                    required=False,
                    default=0,
                    enum=[0, 1, 2]
                ),
                ToolParameter(
                    name="waypoints",
                    type="string",
                    description="Waypoints (途经点) - semicolon separated",
                    required=False
                )
            ],
            returns="object"
        )
    
    async def execute(self, origin: str, destination: str, 
                     strategy: int = 0, waypoints: str = None) -> ToolResult:
        if not self.api_key:
            return ToolResult(
                success=False,
                result=None,
                error="Amap API key not configured. Please set AMAP_API_KEY environment variable."
            )
        
        try:
            # 如果输入的是地址而不是坐标，需要先进行地理编码
            # 这里简化处理，假设输入的是坐标格式
            
            params = {
                "key": self.api_key,
                "origin": origin,
                "destination": destination,
                "strategy": strategy,
                "output": "json"
            }
            if waypoints:
                params["waypoints"] = waypoints
            
            url = f"{self.base_url}?{urlencode(params)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
            
            if data.get("status") == "1" and data.get("route"):
                route = data["route"]
                paths = route.get("paths", [])
                
                if paths:
                    path = paths[0]  # 取第一条路线
                    
                    # 格式化路线信息
                    steps = []
                    for step in path.get("steps", []):
                        steps.append({
                            "instruction": step.get("instruction"),
                            "distance": step.get("distance"),
                            "duration": step.get("duration")
                        })
                    
                    result = {
                        "distance": f"{int(path.get('distance', 0))/1000:.1f} km",
                        "duration": f"{int(path.get('duration', 0))/60:.0f} 分钟",
                        "strategy": path.get("strategy"),
                        "tolls": f"¥{path.get('tolls', 0)}",
                        "steps": steps,
                        "traffic_lights": path.get("traffic_lights", 0)
                    }
                    
                    # 保存到工作空间
                    output_file = {
                        "name": "route_plan.txt",
                        "content": self._format_route_plan(result)
                    }
                    
                    return ToolResult(
                        success=True,
                        result=result,
                        metadata={
                            "api": "amap",
                            "paths_count": len(paths),
                            "output_file": output_file
                        }
                    )
                else:
                    return ToolResult(
                        success=False,
                        result=None,
                        error="No route found"
                    )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Route planning failed: {data.get('info', 'Unknown error')}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def _format_route_plan(self, route_info: Dict[str, Any]) -> str:
        """格式化路线规划结果为文本"""
        lines = [
            "🗺️ 高德地图路线规划",
            "=" * 40,
            f"📏 总距离: {route_info['distance']}",
            f"⏱️ 预计时间: {route_info['duration']}",
            f"💰 过路费: {route_info['tolls']}",
            f"🚦 红绿灯数: {route_info['traffic_lights']}",
            "",
            "📍 详细路线:",
            "-" * 40
        ]
        
        for i, step in enumerate(route_info['steps'], 1):
            lines.append(f"{i}. {step['instruction']}")
            lines.append(f"   距离: {int(step['distance'])}米, 时间: {int(step['duration'])}秒")
            lines.append("")
        
        return "\n".join(lines)


def register_amap_tools(registry, api_key: str = None):
    """注册高德地图工具"""
    registry.register(AmapGeocodeTool(api_key), category="maps")
    registry.register(AmapRoutePlanTool(api_key), category="maps")


# 使用示例：
# 在 MCP manager 初始化时调用
# from server.mcp.tools.amap import register_amap_tools
# register_amap_tools(self.registry, api_key="your_api_key_here")
