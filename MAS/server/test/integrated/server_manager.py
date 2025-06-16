#!/usr/bin/env python3
"""
MAS 服务器管理工具
整合了服务器启动、测试和管理功能
"""

import os
import sys
import subprocess
import time
import signal
import argparse
import webbrowser
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class ServerManager:
    """服务器管理器"""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.server_path = PROJECT_ROOT / "server" / "main.py"
        self.test_suite_path = Path(__file__).parent / "test_suite.py"
        self.test_console_path = Path(__file__).parent / "test_console.html"
        self.base_url = "http://localhost:8000"
        
    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f" {text}")
        print(f"{'='*60}{Colors.ENDC}\n")
        
    def print_success(self, text: str):
        """打印成功消息"""
        print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")
        
    def print_error(self, text: str):
        """打印错误消息"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
        
    def print_info(self, text: str):
        """打印信息"""
        print(f"{Colors.CYAN}→ {text}{Colors.ENDC}")
        
    def check_ollama(self) -> bool:
        """检查Ollama是否运行"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
            
    def start_server(self, debug: bool = False) -> bool:
        """启动服务器"""
        self.print_header("Starting MAS Server")
        
        # 检查Ollama
        if not self.check_ollama():
            self.print_error("Ollama is not running!")
            self.print_info("Please start Ollama first: ollama serve")
            return False
            
        # 检查服务器文件
        if not self.server_path.exists():
            self.print_error(f"Server file not found: {self.server_path}")
            return False
            
        # 构建启动命令
        cmd = [sys.executable, str(self.server_path)]
        if debug:
            cmd.append("--debug")
            
        try:
            # 启动服务器
            self.print_info(f"Starting server from: {self.server_path}")
            self.server_process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            self.print_info("Waiting for server to start...")
            for i in range(30):  # 最多等待30秒
                time.sleep(1)
                try:
                    import requests
                    response = requests.get(f"{self.base_url}/api/system/health", timeout=1)
                    if response.status_code == 200:
                        self.print_success("Server started successfully!")
                        self.print_info(f"Server URL: {self.base_url}")
                        return True
                except:
                    if i % 5 == 0:
                        self.print_info(f"Still waiting... ({i}s)")
                        
            self.print_error("Server failed to start within 30 seconds")
            self.stop_server()
            return False
            
        except Exception as e:
            self.print_error(f"Failed to start server: {e}")
            return False
            
    def stop_server(self):
        """停止服务器"""
        if self.server_process:
            self.print_info("Stopping server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
            self.print_success("Server stopped")
            
    def run_tests(self, verbose: bool = False, test_name: Optional[str] = None):
        """运行测试套件"""
        self.print_header("Running Test Suite")
        
        cmd = [sys.executable, str(self.test_suite_path)]
        if verbose:
            cmd.append("--verbose")
        if test_name:
            cmd.extend(["--test", test_name])
            
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            self.print_error("Tests failed")
            return False
        except FileNotFoundError:
            self.print_error(f"Test suite not found: {self.test_suite_path}")
            return False
            
        return True
        
    def open_test_console(self):
        """打开测试控制台"""
        self.print_header("Opening Test Console")
        
        if not self.test_console_path.exists():
            self.print_error(f"Test console not found: {self.test_console_path}")
            return False
            
        # 检查服务器是否运行
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/system/health", timeout=2)
            if response.status_code != 200:
                self.print_error("Server is not running!")
                return False
        except:
            self.print_error("Server is not running!")
            return False
            
        # 打开浏览器
        url = f"file:///{self.test_console_path.as_posix()}"
        self.print_info(f"Opening: {url}")
        webbrowser.open(url)
        self.print_success("Test console opened in browser")
        return True
        
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            self.print_header("MAS Server Manager")
            print("1. Start Server")
            print("2. Start Server (Debug Mode)")
            print("3. Stop Server")
            print("4. Run All Tests")
            print("5. Run Specific Test")
            print("6. Open Test Console")
            print("7. Check Server Status")
            print("0. Exit")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.start_server(debug=False)
            elif choice == "2":
                self.start_server(debug=True)
            elif choice == "3":
                self.stop_server()
            elif choice == "4":
                self.run_tests()
            elif choice == "5":
                test_name = input("Enter test name (e.g., chat_non_stream): ").strip()
                if test_name:
                    self.run_tests(test_name=test_name)
            elif choice == "6":
                self.open_test_console()
            elif choice == "7":
                self.check_status()
            elif choice == "0":
                self.stop_server()
                break
            else:
                self.print_error("Invalid option")
                
            input("\nPress Enter to continue...")
            
    def check_status(self):
        """检查服务器状态"""
        self.print_header("Server Status")
        
        # 检查Ollama
        if self.check_ollama():
            self.print_success("Ollama is running")
        else:
            self.print_error("Ollama is not running")
            
        # 检查服务器
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/system/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.print_success(f"Server is running (Status: {data['status']})")
                self.print_info(f"Models available: {data.get('model_count', 0)}")
                self.print_info(f"Default model: {data.get('default_model', 'None')}")
            else:
                self.print_error("Server is not healthy")
        except:
            self.print_error("Server is not running")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MAS Server Manager")
    parser.add_argument("command", nargs="?", choices=["start", "stop", "test", "console", "status", "menu"],
                       default="menu", help="Command to execute")
    parser.add_argument("--debug", action="store_true", help="Start server in debug mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output for tests")
    parser.add_argument("--test", help="Run specific test")
    
    args = parser.parse_args()
    
    manager = ServerManager()
    
    try:
        if args.command == "start":
            if manager.start_server(debug=args.debug):
                print("\nServer is running. Press Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    manager.stop_server()
        elif args.command == "stop":
            manager.stop_server()
        elif args.command == "test":
            manager.run_tests(verbose=args.verbose, test_name=args.test)
        elif args.command == "console":
            manager.open_test_console()
        elif args.command == "status":
            manager.check_status()
        else:  # menu
            manager.interactive_menu()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        manager.stop_server()
        sys.exit(0)


if __name__ == "__main__":
    main()
