#!/usr/bin/env python3
"""
统一的服务器测试套件
整合了所有服务器端测试功能
"""

import requests
import json
import time
import sys
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from colorama import init, Fore, Style

# 初始化 colorama
init()

# 配置
DEFAULT_BASE_URL = "http://localhost:8000"
OLLAMA_URL = "http://localhost:11434"


class ServerTestSuite:
    """服务器测试套件"""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, verbose: bool = False):
        self.base_url = base_url
        self.ollama_url = OLLAMA_URL
        self.verbose = verbose
        self.test_results: List[Tuple[str, str, Optional[str]]] = []
        
    def print_header(self, title: str):
        """打印测试段落标题"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f" {title}")
        print(f"{'='*60}{Style.RESET_ALL}")
    
    def print_success(self, message: str):
        """打印成功消息"""
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
    
    def print_error(self, message: str):
        """打印错误消息"""
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
    
    def print_info(self, message: str):
        """打印信息消息"""
        print(f"{Fore.YELLOW}  {message}{Style.RESET_ALL}")
    
    def test_case(self, name: str, func):
        """执行测试用例并记录结果"""
        print(f"\n[TEST] {name}")
        try:
            result = func()
            if result:
                self.print_success("PASSED")
                self.test_results.append((name, "PASSED", None))
            else:
                self.print_error("FAILED")
                self.test_results.append((name, "FAILED", "Test returned False"))
        except Exception as e:
            self.print_error(f"FAILED: {str(e)}")
            self.test_results.append((name, "FAILED", str(e)))
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
        return True
    
    # ========== 基础连接测试 ==========
    
    def test_server_root(self):
        """测试服务器根路径"""
        response = requests.get(f"{self.base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        self.print_info(f"Server: {data['message']} v{data['version']}")
        return True
    
    def test_health_check(self):
        """测试健康检查"""
        response = requests.get(f"{self.base_url}/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        self.print_info(f"Status: {data['status']}")
        self.print_info(f"Ollama Connected: {data.get('ollama_connected', False)}")
        self.print_info(f"Model Count: {data.get('model_count', 0)}")
        return data["status"] == "healthy"
    
    def test_ollama_connectivity(self):
        """测试Ollama连接"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                self.print_info(f"Ollama models: {len(models)}")
                for model in models[:3]:
                    self.print_info(f"  - {model['name']}")
                return True
        except Exception as e:
            self.print_error(f"Cannot connect to Ollama: {e}")
            return False
    
    # ========== 模型管理测试 ==========
    
    def test_list_models(self):
        """测试模型列表"""
        response = requests.get(f"{self.base_url}/api/chat/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        self.print_info(f"Available models: {len(data['data'])}")
        if data.get('default_model'):
            self.print_info(f"Default model: {data['default_model']}")
        for model in data['data'][:3]:
            self.print_info(f"  - {model['name']}")
        return len(data['data']) > 0
    
    def test_refresh_models(self):
        """测试刷新模型列表"""
        response = requests.post(f"{self.base_url}/api/chat/refresh-models")
        assert response.status_code == 200
        data = response.json()
        self.print_info(f"Model count: {data.get('model_count', 0)}")
        self.print_info(f"Default model: {data.get('default_model', 'None')}")
        return True
    
    # ========== 聊天功能测试 ==========
    
    def test_chat_non_stream(self):
        """测试非流式聊天"""
        response = requests.post(
            f"{self.base_url}/api/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Say 'Hello World' and nothing else"}
                ],
                "stream": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        content = data["choices"][0]["message"]["content"]
        self.print_info(f"Response: {content[:100]}...")
        self.print_info(f"Used model: {data.get('model', 'Unknown')}")
        return True
    
    def test_chat_stream(self):
        """测试流式聊天"""
        response = requests.post(
            f"{self.base_url}/api/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Count from 1 to 3"}
                ],
                "stream": True
            },
            stream=True
        )
        assert response.status_code == 200
        
        self.print_info("Streaming response: ")
        content_received = False
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        json_data = json.loads(data)
                        if "content" in json_data:
                            if self.verbose:
                                print(json_data["content"], end="", flush=True)
                            content_received = True
                    except:
                        pass
        if self.verbose:
            print()  # 新行
        return content_received
    
    # ========== 知识库测试 ==========
    
    def test_knowledge_base_list(self):
        """测试知识库列表"""
        response = requests.get(f"{self.base_url}/api/knowledge/")
        if response.status_code == 200:
            kbs = response.json()
            self.print_info(f"Found {len(kbs)} knowledge bases")
            for kb in kbs[:3]:
                self.print_info(f"  - {kb['name']}: {kb['document_count']} docs")
            return True
        return response.status_code in [200, 501]
    
    def test_create_knowledge_base(self):
        """测试创建知识库"""
        test_kb_name = f"test_kb_{int(time.time())}"
        response = requests.post(
            f"{self.base_url}/api/knowledge/",
            json={
                "name": test_kb_name,
                "description": "Test knowledge base"
            }
        )
        if response.status_code == 200:
            kb = response.json()
            self.print_info(f"Created KB: {kb['name']} (ID: {kb['id']})")
            # 清理测试数据
            delete_response = requests.delete(f"{self.base_url}/api/knowledge/{kb['id']}")
            return True
        return False
    
    # ========== RAG测试 ==========
    
    def test_rag_completions(self):
        """测试RAG聊天"""
        # 先获取知识库列表
        kb_response = requests.get(f"{self.base_url}/api/knowledge/")
        if kb_response.status_code != 200:
            self.print_info("No knowledge bases available for RAG test")
            return True  # 跳过测试
        
        kbs = kb_response.json()
        if not kbs:
            self.print_info("No knowledge bases available for RAG test")
            return True
        
        kb_id = kbs[0]['id']
        response = requests.post(
            f"{self.base_url}/api/chat/rag/completions",
            json={
                "knowledge_base_id": kb_id,
                "messages": [{"role": "user", "content": "What is this about?"}],
                "stream": False,
                "search_limit": 5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.print_info(f"RAG response received")
            if "search_results" in data:
                self.print_info(f"Found {data['search_results']['count']} relevant documents")
            return True
        return False
    
    # ========== 运行所有测试 ==========
    
    def run_all_tests(self):
        """运行所有测试"""
        self.print_header("Multi-Agent System Complete Test Suite")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {self.base_url}")
        print(f"Verbose: {self.verbose}")
        
        # 基础测试
        self.print_header("Basic Connectivity Tests")
        self.test_case("Server Root Endpoint", self.test_server_root)
        self.test_case("Health Check", self.test_health_check)
        self.test_case("Ollama Connectivity", self.test_ollama_connectivity)
        
        # 模型管理测试
        self.print_header("Model Management Tests")
        self.test_case("List Models", self.test_list_models)
        self.test_case("Refresh Models", self.test_refresh_models)
        
        # 聊天功能测试
        self.print_header("Chat Functionality Tests")
        self.test_case("Non-Streaming Chat", self.test_chat_non_stream)
        self.test_case("Streaming Chat", self.test_chat_stream)
        
        # 知识库测试
        self.print_header("Knowledge Base Tests")
        self.test_case("List Knowledge Bases", self.test_knowledge_base_list)
        self.test_case("Create Knowledge Base", self.test_create_knowledge_base)
        
        # RAG测试
        self.print_header("RAG Tests")
        self.test_case("RAG Completions", self.test_rag_completions)
        
        # 测试结果总结
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        self.print_header("Test Summary")
        passed = sum(1 for _, status, _ in self.test_results if status == "PASSED")
        failed = sum(1 for _, status, _ in self.test_results if status == "FAILED")
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"{Fore.GREEN}Passed: {passed} ✓{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {failed} ✗{Style.RESET_ALL}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
            for name, status, error in self.test_results:
                if status == "FAILED":
                    print(f"  - {name}: {error}")
        
        return failed == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Multi-Agent System Server Test Suite")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Server base URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", help="Run specific test only")
    
    args = parser.parse_args()
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{args.url}/", timeout=5)
        if response.status_code != 200:
            print(f"{Fore.RED}❌ Server is not responding properly{Style.RESET_ALL}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}❌ Cannot connect to server. Is it running?{Style.RESET_ALL}")
        print(f"   Please start the server and try again.")
        print(f"   URL: {args.url}")
        sys.exit(1)
    
    # 创建测试套件
    suite = ServerTestSuite(base_url=args.url, verbose=args.verbose)
    
    # 运行测试
    if args.test:
        # 运行特定测试
        test_method = getattr(suite, f"test_{args.test}", None)
        if test_method:
            suite.print_header(f"Running test: {args.test}")
            suite.test_case(args.test, test_method)
            suite.print_summary()
        else:
            print(f"{Fore.RED}Unknown test: {args.test}{Style.RESET_ALL}")
            print("Available tests:")
            for attr in dir(suite):
                if attr.startswith("test_") and callable(getattr(suite, attr)):
                    print(f"  - {attr[5:]}")
    else:
        # 运行所有测试
        suite.run_all_tests()
    
    # 返回状态
    success = all(status == "PASSED" for _, status, _ in suite.test_results)
    
    if success:
        print(f"\n{Fore.GREEN}✅ All tests passed! The system is working correctly.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}❌ Some tests failed. Please check the errors above.{Style.RESET_ALL}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
