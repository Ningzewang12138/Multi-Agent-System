"""
MCP工具调用交互式演示
"""
import asyncio
import aiohttp
import json
from datetime import datetime


class MASToolDemo:
    """MAS工具调用演示客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List directory contents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "Delete a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                }
            }
        ]
    
    async def chat(self, message: str, use_tools: bool = True) -> None:
        """发送聊天消息并显示结果"""
        
        payload = {
            "messages": [{"role": "user", "content": message}],
            "tools": self.tools if use_tools else [],
            "tool_choice": "auto" if use_tools else "none",
            "stream": False
        }
        
        if self.session_id:
            payload["session_id"] = self.session_id
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat/completions",
                json=payload,
                headers={"X-Device-ID": "demo-client"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    # 保存session_id
                    if not self.session_id and 'session_id' in result:
                        self.session_id = result['session_id']
                    
                    # 显示工具执行信息
                    if 'tool_execution' in result:
                        print(f"\n🔧 工具执行成功!")
                        print(f"   使用的工具: {', '.join(result['tool_execution']['tools_called'])}")
                        if not self.session_id:
                            print(f"   会话ID: {result['tool_execution']['session_id']}")
                    
                    # 显示响应
                    if 'choices' in result:
                        content = result['choices'][0]['message']['content']
                        print(f"\n💬 助手: {content}")
                    
                else:
                    print(f"\n❌ 错误: {resp.status}")
                    error_text = await resp.text()
                    print(f"   详情: {error_text}")
    
    async def run_demo(self):
        """运行演示流程"""
        print("=== MAS MCP工具调用演示 ===")
        print("这个演示展示了如何使用自然语言来操作文件。")
        print()
        
        demos = [
            ("1️⃣ 创建文件", "Create a file named notes.txt with content 'My first note using MCP tools!'"),
            ("2️⃣ 列出文件", "List all files in the current directory"),
            ("3️⃣ 读取文件", "Read the file notes.txt"),
            ("4️⃣ 创建JSON文件", "Create data.json with content '{\"user\": \"demo\", \"timestamp\": \"" + datetime.now().isoformat() + "\"}'"),
            ("5️⃣ 再次列出文件", "Show me what files we have now"),
        ]
        
        for title, command in demos:
            print(f"\n{title}")
            print(f"📝 用户: {command}")
            await self.chat(command)
            await asyncio.sleep(1)  # 短暂延迟
        
        print("\n✅ 演示完成！")
        print(f"\n💡 提示: 所有文件都保存在会话工作空间中:")
        if self.session_id:
            print(f"   会话ID: {self.session_id}")
    
    async def interactive_mode(self):
        """交互式模式"""
        print("\n=== MAS工具调用交互模式 ===")
        print("支持的命令示例:")
        print("  - Create a file named X with content Y")
        print("  - List all files")
        print("  - Read file X")
        print("  - Delete file X")
        print("  - 输入 'quit' 退出")
        print("  - 输入 'demo' 运行演示")
        print("  - 输入 'reset' 开始新会话")
        print()
        
        while True:
            try:
                user_input = input("\n📝 您: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 再见!")
                    break
                elif user_input.lower() == 'demo':
                    await self.run_demo()
                elif user_input.lower() == 'reset':
                    self.session_id = None
                    print("🔄 已重置会话")
                elif user_input:
                    await self.chat(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 再见!")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")


async def main():
    """主函数"""
    demo = MASToolDemo()
    
    print("欢迎使用 MAS MCP 工具调用系统！")
    print()
    print("选择模式:")
    print("1. 运行演示 (demo)")
    print("2. 交互模式 (interactive)")
    print()
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        await demo.run_demo()
    else:
        await demo.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
