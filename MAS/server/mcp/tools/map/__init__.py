"""
高德地图 MCP 工具
提供高德地图相关功能，如路线规划、地点搜索等
"""
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...base import MCPTool, ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)

# 高德地图API配置
AMAP_API_KEY = "your_amap_api_key_here"  # 需要替换为实际的API密钥
AMAP_BASE_URL = "https://restapi.amap.com/v3"


class AmapRoutePlanningTool(MCPTool):
    """高德地图路线规划工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="amap_route_planning",
            description="高德地图路线规划，支持驾车、步行、公交等多种出行方式",
            parameters=[
                ToolParameter(
                    name="origin",
                    type="string",
                    description="起点位置，可以是经纬度(如116.481028,39.989643)或地点名称",
                    required=True
                ),
                ToolParameter(
                    name="destination", 
                    type="string",
                    description="终点位置，可以是经纬度或地点名称",
                    required=True
                ),
                ToolParameter(
                    name="mode",
                    type="string",
                    description="出行方式",
                    required=False,
                    default="driving",
                    enum=["driving", "walking", "transit", "riding"]
                ),
                ToolParameter(
                    name="city",
                    type="string",
                    description="城市名称(公交路线规划时需要)",
                    required=False
                )
            ]
        )
    
    async def execute(self, origin: str, destination: str, 
                     mode: str = "driving", city: Optional[str] = None) -> ToolResult:
        """执行路线规划"""
        try:
            # 根据不同出行方式调用不同的API
            if mode == "driving":
                url = f"{AMAP_BASE_URL}/direction/driving"
                params = {
                    "key": AMAP_API_KEY,
                    "origin": origin,
                    "destination": destination,
                    "extensions": "all"
                }
            elif mode == "walking":
                url = f"{AMAP_BASE_URL}/direction/walking"
                params = {
                    "key": AMAP_API_KEY,
                    "origin": origin,
                    "destination": destination
                }
            elif mode == "transit":
                url = f"{AMAP_BASE_URL}/direction/transit/integrated"
                params = {
                    "key": AMAP_API_KEY,
                    "origin": origin,
                    "destination": destination,
                    "city": city or "北京"
                }
            elif mode == "riding":
                url = f"{AMAP_BASE_URL}/direction/bicycling"
                params = {
                    "key": AMAP_API_KEY,
                    "origin": origin,
                    "destination": destination
                }
            else:
                return ToolResult(
                    success=False,
                    error=f"Unsupported mode: {mode}"
                )

            # 如果API密钥未设置，返回模拟数据
            if AMAP_API_KEY == "your_amap_api_key_here":
                # 返回模拟的路线规划结果
                mock_result = self._generate_mock_route(origin, destination, mode)
                
                # 生成出行计划文本
                plan_text = self._format_route_plan(mock_result, mode)
                
                return ToolResult(
                    success=True,
                    result=mock_result,
                    metadata={
                        "output_file": {
                            "name": f"route_plan_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            "content": plan_text
                        }
                    }
                )

            # 实际API调用
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "1":
                            # 格式化路线信息
                            route_info = self._parse_route_data(data, mode)
                            
                            # 生成出行计划文本
                            plan_text = self._format_route_plan(route_info, mode)
                            
                            return ToolResult(
                                success=True,
                                result=route_info,
                                metadata={
                                    "output_file": {
                                        "name": f"route_plan_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        "content": plan_text
                                    }
                                }
                            )
                        else:
                            return ToolResult(
                                success=False,
                                error=f"API error: {data.get('info', 'Unknown error')}"
                            )
                    else:
                        return ToolResult(
                            success=False,
                            error=f"HTTP error: {response.status}"
                        )
                        
        except Exception as e:
            logger.error(f"Error in route planning: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _generate_mock_route(self, origin: str, destination: str, mode: str) -> Dict[str, Any]:
        """生成模拟的路线数据"""
        routes = {
            "driving": {
                "distance": "15.3公里",
                "duration": "25分钟",
                "steps": [
                    {"instruction": "从起点向正北方向出发", "distance": "100米"},
                    {"instruction": "右转进入建国路", "distance": "2.5公里"},
                    {"instruction": "左转进入东三环路", "distance": "8.2公里"},
                    {"instruction": "右转进入朝阳路", "distance": "4.3公里"},
                    {"instruction": "到达终点", "distance": "200米"}
                ],
                "traffic_lights": 12,
                "toll": "0元"
            },
            "walking": {
                "distance": "2.1公里",
                "duration": "28分钟",
                "steps": [
                    {"instruction": "从起点向东步行", "distance": "300米"},
                    {"instruction": "穿过人民公园", "distance": "800米"},
                    {"instruction": "沿着中山路继续前行", "distance": "900米"},
                    {"instruction": "到达终点", "distance": "100米"}
                ]
            },
            "transit": {
                "distance": "12.5公里",
                "duration": "45分钟",
                "transits": [
                    {
                        "type": "地铁",
                        "line": "地铁2号线",
                        "departure_stop": "建国门站",
                        "arrival_stop": "朝阳门站",
                        "num_stops": 5
                    },
                    {
                        "type": "公交",
                        "line": "101路",
                        "departure_stop": "朝阳门站",
                        "arrival_stop": "三里屯站",
                        "num_stops": 8
                    }
                ],
                "walking_distance": "500米",
                "cost": "5元"
            }
        }
        
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "route": routes.get(mode, routes["driving"])
        }
    
    def _format_route_plan(self, route_info: Dict[str, Any], mode: str) -> str:
        """格式化路线规划为文本"""
        lines = []
        lines.append(f"{'='*50}")
        lines.append(f"出行计划 - {self._get_mode_name(mode)}")
        lines.append(f"{'='*50}")
        lines.append(f"起点: {route_info['origin']}")
        lines.append(f"终点: {route_info['destination']}")
        lines.append("")
        
        route = route_info['route']
        lines.append(f"总距离: {route['distance']}")
        lines.append(f"预计时间: {route['duration']}")
        
        if mode == "driving":
            lines.append(f"红绿灯数: {route.get('traffic_lights', 'N/A')}")
            lines.append(f"过路费: {route.get('toll', '0元')}")
        elif mode == "transit":
            lines.append(f"步行距离: {route.get('walking_distance', 'N/A')}")
            lines.append(f"票价: {route.get('cost', 'N/A')}")
        
        lines.append("")
        lines.append("详细路线:")
        lines.append("-" * 30)
        
        if mode == "transit" and "transits" in route:
            for i, transit in enumerate(route['transits'], 1):
                lines.append(f"{i}. {transit['type']} - {transit['line']}")
                lines.append(f"   {transit['departure_stop']} → {transit['arrival_stop']} ({transit['num_stops']}站)")
        else:
            for i, step in enumerate(route.get('steps', []), 1):
                lines.append(f"{i}. {step['instruction']} ({step['distance']})")
        
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def _get_mode_name(self, mode: str) -> str:
        """获取出行方式的中文名称"""
        mode_names = {
            "driving": "驾车",
            "walking": "步行",
            "transit": "公交",
            "riding": "骑行"
        }
        return mode_names.get(mode, mode)
    
    def _parse_route_data(self, data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """解析高德地图API返回的路线数据"""
        return {
            "origin": data.get("origin", ""),
            "destination": data.get("destination", ""),
            "mode": mode,
            "route": data.get("route", {})
        }


class AmapPlaceSearchTool(MCPTool):
    """高德地图地点搜索工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="amap_place_search",
            description="高德地图地点搜索，查找附近的餐厅、酒店、景点等",
            parameters=[
                ToolParameter(
                    name="keywords",
                    type="string",
                    description="搜索关键词，如'餐厅'、'酒店'、'公园'等",
                    required=True
                ),
                ToolParameter(
                    name="city",
                    type="string",
                    description="城市名称",
                    required=True
                ),
                ToolParameter(
                    name="location",
                    type="string",
                    description="中心点坐标(经度,纬度)，用于搜索周边",
                    required=False
                ),
                ToolParameter(
                    name="radius",
                    type="integer",
                    description="搜索半径(米)，默认3000米",
                    required=False,
                    default=3000
                )
            ]
        )
    
    async def execute(self, keywords: str, city: str, 
                     location: Optional[str] = None, radius: int = 3000) -> ToolResult:
        """执行地点搜索"""
        try:
            url = f"{AMAP_BASE_URL}/place/text"
            params = {
                "key": AMAP_API_KEY,
                "keywords": keywords,
                "city": city,
                "extensions": "all"
            }
            
            if location:
                params["location"] = location
                params["radius"] = radius

            # 如果API密钥未设置，返回模拟数据
            if AMAP_API_KEY == "your_amap_api_key_here":
                mock_places = self._generate_mock_places(keywords, city, location)
                
                # 生成搜索结果文本
                result_text = self._format_place_results(mock_places, keywords, city)
                
                return ToolResult(
                    success=True,
                    result=mock_places,
                    metadata={
                        "output_file": {
                            "name": f"places_{keywords}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            "content": result_text
                        }
                    }
                )

            # 实际API调用
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "1":
                            places = self._parse_place_data(data)
                            
                            # 生成搜索结果文本
                            result_text = self._format_place_results(places, keywords, city)
                            
                            return ToolResult(
                                success=True,
                                result=places,
                                metadata={
                                    "output_file": {
                                        "name": f"places_{keywords}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        "content": result_text
                                    }
                                }
                            )
                        else:
                            return ToolResult(
                                success=False,
                                error=f"API error: {data.get('info', 'Unknown error')}"
                            )
                    else:
                        return ToolResult(
                            success=False,
                            error=f"HTTP error: {response.status}"
                        )
                        
        except Exception as e:
            logger.error(f"Error in place search: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _generate_mock_places(self, keywords: str, city: str, location: Optional[str]) -> List[Dict[str, Any]]:
        """生成模拟的地点数据"""
        base_places = {
            "餐厅": [
                {"name": "海底捞火锅", "type": "中餐厅", "rating": 4.8, "address": "朝阳区三里屯路19号", "tel": "010-64176577", "distance": "1.2km"},
                {"name": "西贝莜面村", "type": "中餐厅", "rating": 4.5, "address": "朝阳区工体北路8号", "tel": "010-65515588", "distance": "800m"},
                {"name": "必胜客", "type": "西餐厅", "rating": 4.2, "address": "朝阳区建国路88号", "tel": "010-65890123", "distance": "1.5km"}
            ],
            "酒店": [
                {"name": "北京国贸大酒店", "type": "五星级酒店", "rating": 4.9, "address": "朝阳区建国门外大街1号", "tel": "010-65052266", "price": "¥1200起"},
                {"name": "如家快捷酒店", "type": "经济型酒店", "rating": 4.3, "address": "朝阳区东三环中路", "tel": "010-87654321", "price": "¥280起"}
            ],
            "景点": [
                {"name": "天坛公园", "type": "历史古迹", "rating": 4.8, "address": "东城区天坛东里7号", "ticket": "¥15", "opening_hours": "6:00-22:00"},
                {"name": "朝阳公园", "type": "城市公园", "rating": 4.5, "address": "朝阳区朝阳公园南路1号", "ticket": "免费", "opening_hours": "6:00-21:00"}
            ]
        }
        
        # 根据关键词返回相应的地点
        for key, places in base_places.items():
            if key in keywords:
                return places
        
        # 默认返回餐厅数据
        return base_places["餐厅"]
    
    def _format_place_results(self, places: List[Dict[str, Any]], keywords: str, city: str) -> str:
        """格式化地点搜索结果为文本"""
        lines = []
        lines.append(f"{'='*50}")
        lines.append(f"{city} - {keywords}搜索结果")
        lines.append(f"{'='*50}")
        lines.append(f"共找到 {len(places)} 个结果")
        lines.append("")
        
        for i, place in enumerate(places, 1):
            lines.append(f"{i}. {place['name']}")
            lines.append(f"   类型: {place.get('type', 'N/A')}")
            lines.append(f"   地址: {place.get('address', 'N/A')}")
            if 'tel' in place:
                lines.append(f"   电话: {place['tel']}")
            if 'rating' in place:
                lines.append(f"   评分: {place['rating']}分")
            if 'distance' in place:
                lines.append(f"   距离: {place['distance']}")
            if 'price' in place:
                lines.append(f"   价格: {place['price']}")
            if 'ticket' in place:
                lines.append(f"   门票: {place['ticket']}")
            if 'opening_hours' in place:
                lines.append(f"   开放时间: {place['opening_hours']}")
            lines.append("")
        
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def _parse_place_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析高德地图API返回的地点数据"""
        pois = data.get("pois", [])
        places = []
        
        for poi in pois:
            places.append({
                "name": poi.get("name", ""),
                "type": poi.get("type", ""),
                "address": poi.get("address", ""),
                "tel": poi.get("tel", ""),
                "location": poi.get("location", "")
            })
        
        return places


def register_map_tools(registry):
    """注册地图相关工具"""
    registry.register(AmapRoutePlanningTool(), category="map")
    registry.register(AmapPlaceSearchTool(), category="map")
    logger.info("Map tools registered")
