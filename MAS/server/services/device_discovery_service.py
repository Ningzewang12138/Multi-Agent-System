# server/services/device_discovery_service.py

import asyncio
import json
import socket
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass, asdict
import platform
import netifaces

logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    """设备信息"""
    id: str
    name: str
    type: str  # 'server', 'mobile', 'desktop'
    platform: str  # 'windows', 'android', 'ios', 'linux'
    ip_address: str
    port: int
    version: str
    capabilities: List[str]  # ['knowledge_base', 'mcp', 'chat']
    last_seen: datetime
    status: str = 'online'  # 'online', 'offline'
    
    def to_dict(self):
        data = asdict(self)
        data['last_seen'] = self.last_seen.isoformat()
        return data

class DeviceDiscoveryService:
    """设备发现服务"""
    
    def __init__(self, host: str = "0.0.0.0", discovery_port: int = 8001, api_port: int = 8000):
        self.host = host
        self.discovery_port = discovery_port
        self.api_port = api_port
        
        # 本设备信息
        self.device_id = self._get_device_id()
        self.device_info = self._create_device_info()
        
        # 已发现的设备
        self.discovered_devices: Dict[str, DeviceInfo] = {}
        self._devices_lock = threading.Lock()
        
        # 广播相关
        self.broadcast_interval = 5  # 秒
        self.device_timeout = 30  # 秒
        self.running = False
        self._broadcast_thread = None
        self._listener_thread = None
        
    def _get_device_id(self) -> str:
        """获取或生成设备ID"""
        # TODO: 从配置文件读取持久化的设备ID
        return str(uuid.uuid4())
    
    def _create_device_info(self) -> DeviceInfo:
        """创建本设备信息"""
        device_type = 'server'
        if platform.system() == 'Windows':
            device_type = 'desktop'
        elif platform.system() in ['Darwin', 'Linux']:
            device_type = 'desktop' if not self._is_mobile() else 'mobile'
            
        return DeviceInfo(
            id=self.device_id,
            name=platform.node(),
            type=device_type,
            platform=platform.system().lower(),
            ip_address=self._get_local_ip(),
            port=self.api_port,
            version="1.0.0",
            capabilities=['knowledge_base', 'mcp', 'chat'],
            last_seen=datetime.now()
        )
    
    def _is_mobile(self) -> bool:
        """检测是否为移动设备"""
        # 简单判断，实际需要更复杂的逻辑
        return False
    
    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            # 获取所有网络接口
            interfaces = netifaces.interfaces()
            
            for interface in interfaces:
                addrs = netifaces.ifaddresses(interface)
                
                # 获取IPv4地址
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        # 过滤掉回环地址
                        if not ip.startswith('127.'):
                            return ip
            
            # 如果没找到，使用备用方法
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def start(self):
        """启动设备发现服务"""
        if self.running:
            return
            
        self.running = True
        
        # 启动广播线程
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop)
        self._broadcast_thread.daemon = True
        self._broadcast_thread.start()
        
        # 启动监听线程
        self._listener_thread = threading.Thread(target=self._listen_loop)
        self._listener_thread.daemon = True
        self._listener_thread.start()
        
        logger.info(f"Device discovery service started on port {self.discovery_port}")
    
    def stop(self):
        """停止设备发现服务"""
        logger.info("Stopping device discovery service...")
        self.running = False
        
        # 等待线程结束
        if self._broadcast_thread and self._broadcast_thread.is_alive():
            self._broadcast_thread.join(timeout=5)
            if self._broadcast_thread.is_alive():
                logger.warning("Broadcast thread did not stop gracefully")
        
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
            if self._listener_thread.is_alive():
                logger.warning("Listener thread did not stop gracefully")
            
        logger.info("Device discovery service stopped")
    
    def _broadcast_loop(self):
        """广播循环"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # 记录广播开始
        logger.info(f"Starting broadcast loop on port {self.discovery_port}")
        logger.info(f"Local IP: {self.device_info.ip_address}")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"Device Name: {self.device_info.name}")
        
        broadcast_count = 0
        
        while self.running:
            try:
                # 更新设备信息
                self.device_info.last_seen = datetime.now()
                
                # 创建广播消息
                message = {
                    'type': 'device_announcement',
                    'device': self.device_info.to_dict()
                }
                
                # 发送广播
                data = json.dumps(message).encode('utf-8')
                bytes_sent = sock.sendto(data, ('<broadcast>', self.discovery_port))
                
                broadcast_count += 1
                logger.debug(f"Broadcast #{broadcast_count} sent: {self.device_info.name} ({bytes_sent} bytes)")
                
            except socket.error as e:
                logger.error(f"Socket error during broadcast: {e}")
                # 尝试重新创建socket
                try:
                    sock.close()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    logger.info("Socket recreated after error")
                except Exception as e2:
                    logger.error(f"Failed to recreate socket: {e2}")
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
            
            time.sleep(self.broadcast_interval)
        
        logger.info("Broadcast loop stopped")
        sock.close()
    
    def _listen_loop(self):
        """监听循环"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 在Windows上，可能需要这个选项
        if platform.system() == 'Windows':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            sock.bind((self.host, self.discovery_port))
            logger.info(f"Listening on {self.host}:{self.discovery_port}")
        except OSError as e:
            logger.error(f"Failed to bind to port {self.discovery_port}: {e}")
            logger.error("Another instance might be running or port is in use")
            return
        
        sock.settimeout(1.0)  # 设置超时以便能够检查running状态
        
        received_count = 0
        
        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                received_count += 1
                
                message = json.loads(data.decode('utf-8'))
                logger.debug(f"Received message #{received_count} from {addr[0]}:{addr[1]}")
                
                if message['type'] == 'device_announcement':
                    self._handle_device_announcement(message['device'], addr[0])
                    
            except socket.timeout:
                # 超时是正常的，继续循环
                pass
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received from {addr if 'addr' in locals() else 'unknown'}: {e}")
            except Exception as e:
                logger.error(f"Listen error: {e}")
            
            # 清理离线设备
            self._cleanup_offline_devices()
        
        logger.info("Listen loop stopped")
        sock.close()
    
    def _handle_device_announcement(self, device_data: dict, sender_ip: str):
        """处理设备公告"""
        # 忽略自己的广播
        if device_data['id'] == self.device_id:
            logger.debug("Ignoring own broadcast")
            return
        
        # 更新发送者的IP（以实际接收到的为准）
        device_data['ip_address'] = sender_ip
        device_data['last_seen'] = datetime.fromisoformat(device_data['last_seen'])
        
        device_info = DeviceInfo(**device_data)
        
        with self._devices_lock:
            is_new = device_info.id not in self.discovered_devices
            self.discovered_devices[device_info.id] = device_info
            
        if is_new:
            logger.info(f"New device discovered: {device_info.name} ({device_info.ip_address}) - Type: {device_info.type}, Platform: {device_info.platform}")
        else:
            logger.debug(f"Device updated: {device_info.name} ({device_info.ip_address})")
    
    def _cleanup_offline_devices(self):
        """清理离线设备"""
        now = datetime.now()
        timeout_threshold = timedelta(seconds=self.device_timeout)
        
        with self._devices_lock:
            offline_devices = []
            
            for device_id, device in self.discovered_devices.items():
                if now - device.last_seen > timeout_threshold:
                    device.status = 'offline'
                    offline_devices.append(device_id)
            
            # 移除长时间离线的设备（比如超过5分钟）
            for device_id in offline_devices:
                if now - self.discovered_devices[device_id].last_seen > timedelta(minutes=5):
                    del self.discovered_devices[device_id]
                    logger.info(f"Device removed: {device_id}")
    
    def get_online_devices(self) -> List[DeviceInfo]:
        """获取在线设备列表"""
        with self._devices_lock:
            now = datetime.now()
            timeout_threshold = timedelta(seconds=self.device_timeout)
            
            online_devices = []
            for device in self.discovered_devices.values():
                if now - device.last_seen <= timeout_threshold:
                    device.status = 'online'
                    online_devices.append(device)
                else:
                    device.status = 'offline'
                    
            return online_devices
    
    def get_all_devices(self) -> List[DeviceInfo]:
        """获取所有设备（包括离线）"""
        with self._devices_lock:
            devices = list(self.discovered_devices.values())
            logger.info(f"Total devices: {len(devices)}")
            for device in devices:
                logger.debug(f"  - {device.name} ({device.ip_address}): {device.status}")
            return devices
    
    def get_device_by_id(self, device_id: str) -> Optional[DeviceInfo]:
        """根据ID获取设备"""
        with self._devices_lock:
            # 如果是本设备
            if device_id == self.device_id:
                return self.device_info
            return self.discovered_devices.get(device_id)
    
    def register_device(self, device_id: str, device_name: str = None, 
                       device_type: str = "unknown", ip_address: str = "unknown") -> DeviceInfo:
        """注册新设备（用于自动注册）"""
        if not device_name:
            device_name = device_id
        
        device_info = DeviceInfo(
            id=device_id,
            name=device_name,
            type=device_type,
            platform="unknown",
            ip_address=ip_address,
            port=0,
            version="unknown",
            capabilities=[],
            last_seen=datetime.now(),
            status='online'
        )
        
        with self._devices_lock:
            self.discovered_devices[device_id] = device_info
            logger.info(f"Auto-registered device: {device_name} ({device_id})")
        
        return device_info

# 全局实例
discovery_service = DeviceDiscoveryService()
