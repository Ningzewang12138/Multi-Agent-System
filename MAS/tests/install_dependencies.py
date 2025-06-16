#!/usr/bin/env python
"""
安装项目依赖的Python脚本
"""
import subprocess
import sys
import os

def check_venv():
    """检查是否在虚拟环境中"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def install_dependencies():
    """安装依赖"""
    print("安装MAS项目依赖...")
    print("="*50)
    
    # 检查虚拟环境
    if not check_venv():
        print("警告：不在虚拟环境中运行")
        print("建议先激活虚拟环境")
        choice = input("是否继续？(y/n): ")
        if choice.lower() != 'y':
            return
    
    # 升级pip
    print("\n1. 升级pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # 安装基本依赖
    print("\n2. 安装基本依赖...")
    basic_deps = [
        "requests",
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
        "aiofiles"
    ]
    
    for dep in basic_deps:
        print(f"   安装 {dep}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        except:
            print(f"   {dep} 安装失败，继续...")
    
    # 如果存在requirements.txt，安装所有依赖
    if os.path.exists("requirements.txt"):
        print("\n3. 从requirements.txt安装所有依赖...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("   所有依赖安装完成")
        except Exception as e:
            print(f"   部分依赖安装失败: {e}")
            print("   尝试单独安装核心依赖...")
            
            # 核心依赖列表
            core_deps = [
                "requests==2.31.0",
                "fastapi==0.109.0",
                "uvicorn[standard]==0.27.0",
                "chromadb==0.4.22",
                "sentence-transformers==2.3.1",
                "langchain==0.1.0",
                "pypdf==3.17.4",
                "python-docx==1.1.0"
            ]
            
            for dep in core_deps:
                try:
                    print(f"   安装 {dep}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                except:
                    print(f"   {dep} 安装失败")
    
    # 验证安装
    print("\n4. 验证安装...")
    test_imports = {
        "requests": "HTTP请求库",
        "fastapi": "Web框架",
        "chromadb": "向量数据库",
        "sentence_transformers": "句子嵌入模型"
    }
    
    success_count = 0
    for module, desc in test_imports.items():
        try:
            __import__(module)
            print(f"   {module} ({desc}) - 已安装")
            success_count += 1
        except ImportError:
            print(f"   {module} ({desc}) - 未安装")
    
    print(f"\n安装完成！成功安装 {success_count}/{len(test_imports)} 个核心模块")
    
    if success_count < len(test_imports):
        print("\n建议：")
        print("1. 检查网络连接")
        print("2. 使用国内镜像源：")
        print("   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
        print("3. 查看具体错误信息")

if __name__ == "__main__":
    install_dependencies()
