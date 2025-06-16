"""
服务器状态检查和测试运行器
"""
import subprocess
import time
import requests
import sys
import os

def check_server_status():
    """检查服务器是否运行"""
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ 服务器正在运行")
            print(f"   版本: {data.get('version', 'unknown')}")
            print(f"   状态: {data.get('status', 'unknown')}")
            
            # 检查各项功能
            features = data.get('features', {})
            print("\n功能状态:")
            for feature, enabled in features.items():
                status = "✅" if enabled else "❌"
                print(f"   {status} {feature}: {enabled}")
            
            return True
    except requests.exceptions.ConnectionError:
        print("❌ 服务器未运行")
        return False
    except Exception as e:
        print(f"❌ 检查服务器失败: {e}")
        return False

def start_server():
    """尝试启动服务器"""
    print("\n正在尝试启动服务器...")
    
    # 切换到server目录
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
    
    # 启动服务器进程
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=server_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    print("等待服务器启动", end="")
    for i in range(30):  # 最多等待30秒
        time.sleep(1)
        print(".", end="", flush=True)
        
        if check_server_status():
            print("\n✅ 服务器启动成功！")
            return process
    
    print("\n❌ 服务器启动超时")
    process.terminate()
    return None

def run_tests():
    """运行测试"""
    print("\n" + "="*50)
    print("开始运行测试...")
    print("="*50)
    
    # 运行错误处理测试
    test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server", "test", "test_error_handling.py")
    
    if not os.path.exists(test_path):
        print(f"❌ 测试文件不存在: {test_path}")
        return False
    
    result = subprocess.run(
        [sys.executable, test_path],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    """主函数"""
    print("MAS 项目 - 错误处理修复测试")
    print("="*50)
    
    # 检查服务器状态
    server_running = check_server_status()
    server_process = None
    
    if not server_running:
        print("\n服务器未运行，请选择：")
        print("1. 自动启动服务器并运行测试")
        print("2. 手动启动服务器后继续")
        print("3. 退出")
        
        choice = input("\n请选择 (1/2/3): ")
        
        if choice == "1":
            server_process = start_server()
            if not server_process:
                print("服务器启动失败，退出测试")
                return
        elif choice == "2":
            print("\n请在另一个终端执行以下命令启动服务器：")
            print("  cd server")
            print("  python main.py")
            input("\n启动后按回车继续...")
            
            if not check_server_status():
                print("服务器仍未运行，退出测试")
                return
        else:
            print("退出测试")
            return
    
    # 运行测试
    try:
        success = run_tests()
        
        if success:
            print("\n✅ 所有测试通过！")
        else:
            print("\n❌ 测试失败！")
    
    finally:
        # 如果自动启动了服务器，询问是否关闭
        if server_process:
            input("\n按回车关闭服务器...")
            server_process.terminate()
            print("服务器已关闭")

if __name__ == "__main__":
    main()
