// 服务器配置 - 用于 Android 设备连接到局域网服务器

class AppConfigAndroid {
  // 重要：将这里的 IP 地址改为您的电脑在局域网中的 IP 地址
  // 查看方法：
  // Windows: 打开命令提示符，输入 ipconfig，找到 IPv4 地址
  // 例如：192.168.1.100

  // 将 localhost 改为您的实际 IP 地址
  static const String SERVER_IP = "192.168.1.3"; // <-- 修改这里！
  static const String SERVER_PORT = "8000";

  static String get multiAgentServer => 'http://$SERVER_IP:$SERVER_PORT';
}

// 使用说明：
// 1. 在 Windows 上运行 ipconfig 查看您的 IP 地址
// 2. 将上面的 SERVER_IP 修改为您的实际 IP 地址
// 3. 确保您的手机和电脑在同一个 WiFi 网络下
// 4. 确保 Windows 防火墙允许端口 8000 的访问
