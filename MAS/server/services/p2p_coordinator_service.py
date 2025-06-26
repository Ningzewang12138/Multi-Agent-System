"""
P2P协调服务
负责管理P2P连接信息和协助NAT穿透
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import socket
import struct

logger = logging.getLogger(__name__)


@dataclass
class P2PEndpoint:
    """P2P端点信息"""
    device_id: str
    device_name: str
    local_ip: str          # 内网IP
    local_port: int        # 监听端口
    public_ip: str         # 公网IP（从连接中获取）
    public_port: int       # 公网端口（可能被NAT映射）
    nat_type: str          # NAT类型：full_cone, restricted, symmetric
    last_updated: datetime
    is_relay_needed: bool = False  # 是否需要中继
    
    def to_dict(self):
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data


class P2PCoordinatorService:
    """P2P协调服务"""
    
    def __init__(self):
        self.endpoints: Dict[str, P2PEndpoint] = {}
        self.pending_punches: Dict[str, List[Tuple[str, datetime]]] = {}  # 待处理的打洞请求
        self._lock = asyncio.Lock()
        
    async def register_endpoint(self, device_id: str, device_name: str, 
                              local_ip: str, local_port: int, 
                              public_ip: str) -> P2PEndpoint:
        """注册P2P端点"""
        async with self._lock:
            # 检测NAT类型（简化版）
            nat_type = await self._detect_nat_type(public_ip, local_ip)
            
            endpoint = P2PEndpoint(
                device_id=device_id,
                device_name=device_name,
                local_ip=local_ip,
                local_port=local_port,
                public_ip=public_ip,
                public_port=local_port,  # 初始假设端口未改变
                nat_type=nat_type,
                last_updated=datetime.now()
            )
            
            self.endpoints[device_id] = endpoint
            logger.info(f"Registered P2P endpoint: {device_id} ({local_ip}:{local_port} -> {public_ip})")
            
            # 清理过期的端点
            await self._cleanup_stale_endpoints()
            
            return endpoint
    
    async def get_peer_info(self, device_id: str, peer_id: str) -> Optional[Dict]:
        """获取对等设备的连接信息"""
        async with self._lock:
            if peer_id not in self.endpoints:
                return None
            
            peer = self.endpoints[peer_id]
            requester = self.endpoints.get(device_id)
            
            if not requester:
                return None
            
            # 判断是否在同一局域网
            same_network = self._check_same_network(requester.local_ip, peer.local_ip)
            
            # 判断是否需要NAT穿透
            needs_punch = not same_network and (
                requester.nat_type == "symmetric" or 
                peer.nat_type == "symmetric"
            )
            
            return {
                "device_id": peer.device_id,
                "device_name": peer.device_name,
                "endpoints": {
                    "local": {
                        "ip": peer.local_ip,
                        "port": peer.local_port
                    },
                    "public": {
                        "ip": peer.public_ip,
                        "port": peer.public_port
                    }
                },
                "same_network": same_network,
                "nat_type": peer.nat_type,
                "needs_punch": needs_punch,
                "relay_needed": peer.is_relay_needed
            }
    
    async def request_nat_punch(self, device_id: str, peer_id: str) -> Dict:
        """请求NAT打洞协助"""
        async with self._lock:
            # 记录打洞请求
            if peer_id not in self.pending_punches:
                self.pending_punches[peer_id] = []
            
            self.pending_punches[peer_id].append((device_id, datetime.now()))
            
            # 获取双方信息
            device = self.endpoints.get(device_id)
            peer = self.endpoints.get(peer_id)
            
            if not device or not peer:
                return {"success": False, "error": "Device not found"}
            
            # 生成打洞令牌
            punch_token = f"{device_id}:{peer_id}:{datetime.now().timestamp()}"
            
            return {
                "success": True,
                "punch_token": punch_token,
                "instructions": {
                    "device": {
                        "target_ip": peer.public_ip,
                        "target_port": peer.public_port,
                        "local_port": device.local_port
                    },
                    "peer": {
                        "target_ip": device.public_ip,
                        "target_port": device.public_port,
                        "local_port": peer.local_port
                    }
                },
                "timeout": 30  # 30秒超时
            }
    
    async def update_endpoint_port(self, device_id: str, observed_port: int):
        """更新观察到的公网端口（用于STUN）"""
        async with self._lock:
            if device_id in self.endpoints:
                self.endpoints[device_id].public_port = observed_port
                self.endpoints[device_id].last_updated = datetime.now()
                logger.info(f"Updated public port for {device_id}: {observed_port}")
    
    async def list_available_peers(self, device_id: str) -> List[Dict]:
        """列出可用的对等设备"""
        async with self._lock:
            peers = []
            device = self.endpoints.get(device_id)
            
            if not device:
                return peers
            
            for peer_id, peer in self.endpoints.items():
                if peer_id == device_id:
                    continue
                
                # 检查是否在线（5分钟内更新过）
                if datetime.now() - peer.last_updated > timedelta(minutes=5):
                    continue
                
                same_network = self._check_same_network(device.local_ip, peer.local_ip)
                
                peers.append({
                    "device_id": peer.device_id,
                    "device_name": peer.device_name,
                    "same_network": same_network,
                    "nat_type": peer.nat_type,
                    "online": True
                })
            
            return peers
    
    def _check_same_network(self, ip1: str, ip2: str) -> bool:
        """检查两个IP是否在同一网段（简化版）"""
        try:
            # 获取前三段
            prefix1 = '.'.join(ip1.split('.')[:3])
            prefix2 = '.'.join(ip2.split('.')[:3])
            return prefix1 == prefix2
        except:
            return False
    
    async def _detect_nat_type(self, public_ip: str, local_ip: str) -> str:
        """检测NAT类型（简化版）"""
        # 如果公网IP和内网IP相同，说明没有NAT
        if public_ip == local_ip:
            return "none"
        
        # 简化判断，实际需要更复杂的STUN测试
        # 这里假设大多数家用路由器是restricted NAT
        return "restricted"
    
    async def _cleanup_stale_endpoints(self):
        """清理过期的端点"""
        now = datetime.now()
        stale_timeout = timedelta(minutes=10)
        
        stale_devices = []
        for device_id, endpoint in self.endpoints.items():
            if now - endpoint.last_updated > stale_timeout:
                stale_devices.append(device_id)
        
        for device_id in stale_devices:
            del self.endpoints[device_id]
            logger.info(f"Removed stale endpoint: {device_id}")
    
    async def handle_stun_request(self, data: bytes, addr: Tuple[str, int]) -> Optional[bytes]:
        """处理简单的STUN请求（用于端口检测）"""
        # 简单的STUN响应，返回观察到的地址
        if len(data) >= 20 and data[0:2] == b'\x00\x01':  # Binding Request
            # 构建STUN响应
            response = bytearray(b'\x01\x01\x00\x0c')  # Binding Response, length 12
            response += data[4:20]  # Transaction ID
            
            # MAPPED-ADDRESS attribute
            response += b'\x00\x01\x00\x08'  # Type and length
            response += b'\x00\x01'  # Family (IPv4)
            response += struct.pack('!H', addr[1])  # Port
            response += socket.inet_aton(addr[0])  # IP
            
            return bytes(response)
        
        return None


# 全局实例
p2p_coordinator = P2PCoordinatorService()
