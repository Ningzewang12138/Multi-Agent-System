"""
MCP API 测试脚本
测试MCP服务端API的各项功能
"""
import requests
import json
import time
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000/api/mcp"

def print_response(response: requests.Response, title: str):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'='*60}\n")

def test_list_services():
    """测试获取MCP服务列表"""
    print("\n🔍 Testing MCP Services List...")
    response = requests.get(f"{BASE_URL}/services")
    print_response(response, "MCP Services List")
    return response.json()

def test_list_tools(category: str = None):
    """测试获取MCP工具列表"""
    print("\n🔧 Testing MCP Tools List...")
    params = {"category": category} if category else {}
    response = requests.get(f"{BASE_URL}/tools", params=params)
    print_response(response, f"MCP Tools List (category: {category or 'all'})")
    return response.json()

def test_create_workspace(device_id: str):
    """测试创建工作空间"""
    print("\n📁 Testing Create Workspace...")
    data = {
        "device_id": device_id
    }
    response = requests.post(f"{BASE_URL}/workspace/create", json=data)
    print_response(response, "Create Workspace")
    return response.json()

def test_execute_tool(tool_name: str, parameters: Dict[str, Any], device_id: str, session_id: str = None):
    """测试执行MCP工具"""
    print(f"\n⚡ Testing Execute Tool: {tool_name}...")
    data = {
        "tool_name": tool_name,
        "parameters": parameters,
        "device_id": device_id
    }
    if session_id:
        data["session_id"] = session_id
    
    response = requests.post(f"{BASE_URL}/execute", json=data)
    print_response(response, f"Execute Tool: {tool_name}")
    return response.json()

def test_list_workspace_files(session_id: str):
    """测试列出工作空间文件"""
    print(f"\n📋 Testing List Workspace Files...")
    response = requests.get(f"{BASE_URL}/workspace/{session_id}/files")
    print_response(response, "List Workspace Files")
    return response.json()

def test_download_file(session_id: str, filename: str):
    """测试下载工作空间文件"""
    print(f"\n📥 Testing Download File: {filename}...")
    response = requests.get(f"{BASE_URL}/workspace/{session_id}/file/{filename}")
    print_response(response, f"Download File: {filename}")
    return response.json()

def main():
    """主测试流程"""
    print("🚀 Starting MCP API Tests...")
    print(f"API Base URL: {BASE_URL}")
    
    # 测试设备ID
    test_device_id = "test_device_001"
    
    try:
        # 1. 获取服务列表
        services = test_list_services()
        
        # 2. 获取所有工具
        all_tools = test_list_tools()
        
        # 3. 获取特定类别的工具
        filesystem_tools = test_list_tools("filesystem")
        
        # 4. 创建工作空间
        workspace_info = test_create_workspace(test_device_id)
        session_id = workspace_info["session_id"]
        print(f"✅ Created workspace with session_id: {session_id}")
        
        # 5. 测试文件写入工具
        write_result = test_execute_tool(
            tool_name="write_file",
            parameters={
                "path": "@workspace/test_output.txt",
                "content": "Hello from MCP!\n这是一个测试文件。\n当前时间: " + time.strftime("%Y-%m-%d %H:%M:%S")
            },
            device_id=test_device_id,
            session_id=session_id
        )
        
        # 6. 测试JSON处理工具
        json_data = {
            "name": "MCP Test",
            "version": "1.0",
            "features": ["filesystem", "web", "data"],
            "test_data": {
                "numbers": [1, 2, 3, 4, 5],
                "status": "active"
            }
        }
        
        json_result = test_execute_tool(
            tool_name="json_process",
            parameters={
                "data": json.dumps(json_data),
                "operation": "format",
                "indent": 4
            },
            device_id=test_device_id,
            session_id=session_id
        )
        
        # 7. 测试CSV处理工具
        csv_data = """name,age,city
Alice,25,Beijing
Bob,30,Shanghai
Charlie,35,Guangzhou"""
        
        csv_result = test_execute_tool(
            tool_name="csv_process",
            parameters={
                "data": csv_data,
                "operation": "to_json"
            },
            device_id=test_device_id,
            session_id=session_id
        )
        
        # 8. 测试文本分析工具
        text_result = test_execute_tool(
            tool_name="text_analysis",
            parameters={
                "text": "This is a test text for MCP analysis. It contains multiple words and sentences. Let's see how the analysis works!",
                "operation": "summary"
            },
            device_id=test_device_id,
            session_id=session_id
        )
        
        # 9. 测试数据转换工具
        convert_result = test_execute_tool(
            tool_name="data_convert",
            parameters={
                "data": json.dumps(json_data),
                "from_format": "json",
                "to_format": "yaml",
                "options": {
                    "save_to_workspace": True,
                    "filename": "converted_data.yaml"
                }
            },
            device_id=test_device_id,
            session_id=session_id
        )
        
        # 10. 列出工作空间文件
        files = test_list_workspace_files(session_id)
        
        # 11. 下载一个文件
        if files and len(files) > 0:
            first_file = files[0]["name"]
            file_content = test_download_file(session_id, first_file)
        
        # 12. 测试HTTP请求工具（可选）
        if input("\n是否测试HTTP请求工具？(y/n): ").lower() == 'y':
            http_result = test_execute_tool(
                tool_name="http_request",
                parameters={
                    "url": "https://api.github.com/repos/anthropics/anthropic-sdk-python",
                    "method": "GET"
                },
                device_id=test_device_id,
                session_id=session_id
            )
        
        print("\n✅ All tests completed successfully!")
        
        # 清理提示
        if input("\n是否删除测试工作空间？(y/n): ").lower() == 'y':
            response = requests.delete(f"{BASE_URL}/workspace/{session_id}")
            print_response(response, "Delete Workspace")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
