import os
import re

# 项目根目录
project_root = r"D:\Workspace\Python_Workspace\AIagent-dev\MAS\masgui"

# 需要检查的文件扩展名
file_extensions = ['.dart']

# 需要替换的包名
old_package = 'ollama_app'
new_package = 'masgui'

def fix_imports_in_file(file_path):
    """修复单个文件中的导入语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否包含旧包名
        if old_package in content:
            # 替换包名
            new_content = content.replace(f'package:{old_package}/', f'package:{new_package}/')
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"Fixed: {file_path}")
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def main():
    """遍历所有Dart文件并修复导入"""
    fixed_count = 0
    
    # 遍历lib目录
    for root, dirs, files in os.walk(os.path.join(project_root, 'lib')):
        # 跳过build目录
        if 'build' in root:
            continue
            
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                file_path = os.path.join(root, file)
                if fix_imports_in_file(file_path):
                    fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()
