"""
文件系统相关的 MCP 工具
"""
import os
import json
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
import mimetypes
import datetime

from ..base import MCPTool, ToolDefinition, ToolParameter, ToolResult


class FileReadTool(MCPTool):
    """读取文件内容"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read"
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8)",
                    required=False,
                    default="utf-8"
                )
            ],
            returns="string"
        )
    
    async def execute(self, path: str, encoding: str = "utf-8") -> ToolResult:
        try:
            file_path = Path(path)
            
            # 安全检查
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"File not found: {path}"
                )
            
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Path is not a file: {path}"
                )
            
            # 读取文件
            async with aiofiles.open(file_path, mode='r', encoding=encoding) as f:
                content = await f.read()
            
            return ToolResult(
                success=True,
                result=content,
                metadata={
                    "file_size": file_path.stat().st_size,
                    "mime_type": mimetypes.guess_type(path)[0]
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class FileWriteTool(MCPTool):
    """写入文件内容"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write content to a file",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to write"
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file"
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8)",
                    required=False,
                    default="utf-8"
                ),
                ToolParameter(
                    name="append",
                    type="boolean",
                    description="Append to file instead of overwriting",
                    required=False,
                    default=False
                )
            ],
            returns="string"
        )
    
    async def execute(self, path: str, content: str, 
                     encoding: str = "utf-8", append: bool = False) -> ToolResult:
        try:
            file_path = Path(path)
            
            # 创建父目录（如果不存在）
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'a' if append else 'w'
            async with aiofiles.open(file_path, mode=mode, encoding=encoding) as f:
                await f.write(content)
            
            return ToolResult(
                success=True,
                result=f"Successfully wrote to {path}",
                metadata={
                    "file_size": file_path.stat().st_size,
                    "mode": "append" if append else "overwrite"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class ListDirectoryTool(MCPTool):
    """列出目录内容"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_directory",
            description="List contents of a directory",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the directory"
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="List recursively",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="include_hidden",
                    type="boolean",
                    description="Include hidden files",
                    required=False,
                    default=False
                )
            ],
            returns="array"
        )
    
    async def execute(self, path: str, recursive: bool = False, 
                     include_hidden: bool = False) -> ToolResult:
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Directory not found: {path}"
                )
            
            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Path is not a directory: {path}"
                )
            
            items = []
            
            if recursive:
                for item in dir_path.rglob("*"):
                    if not include_hidden and item.name.startswith('.'):
                        continue
                    items.append(self._get_file_info(item, dir_path))
            else:
                for item in dir_path.iterdir():
                    if not include_hidden and item.name.startswith('.'):
                        continue
                    items.append(self._get_file_info(item, dir_path))
            
            return ToolResult(
                success=True,
                result=items,
                metadata={
                    "total_items": len(items),
                    "path": str(dir_path.absolute())
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def _get_file_info(self, path: Path, base_path: Path) -> Dict[str, Any]:
        """获取文件信息"""
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path.relative_to(base_path)),
            "absolute_path": str(path.absolute()),
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size if path.is_file() else None,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mime_type": mimetypes.guess_type(str(path))[0] if path.is_file() else None
        }


class CreateDirectoryTool(MCPTool):
    """创建目录"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_directory",
            description="Create a new directory",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path of the directory to create"
                ),
                ToolParameter(
                    name="parents",
                    type="boolean",
                    description="Create parent directories if needed",
                    required=False,
                    default=True
                )
            ],
            returns="string"
        )
    
    async def execute(self, path: str, parents: bool = True) -> ToolResult:
        try:
            dir_path = Path(path)
            
            if dir_path.exists():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Path already exists: {path}"
                )
            
            dir_path.mkdir(parents=parents, exist_ok=False)
            
            return ToolResult(
                success=True,
                result=f"Directory created: {path}",
                metadata={
                    "absolute_path": str(dir_path.absolute())
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class DeleteFileTool(MCPTool):
    """删除文件或目录"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="delete_file",
            description="Delete a file or directory",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to delete"
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Delete directories recursively",
                    required=False,
                    default=False
                )
            ],
            returns="string"
        )
    
    async def execute(self, path: str, recursive: bool = False) -> ToolResult:
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Path not found: {path}"
                )
            
            if file_path.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    file_path.rmdir()
            else:
                file_path.unlink()
            
            return ToolResult(
                success=True,
                result=f"Successfully deleted: {path}",
                metadata={
                    "type": "directory" if file_path.is_dir() else "file"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


def register_file_tools(registry):
    """注册文件系统工具"""
    registry.register(FileReadTool(), category="filesystem")
    registry.register(FileWriteTool(), category="filesystem")
    registry.register(ListDirectoryTool(), category="filesystem")
    registry.register(CreateDirectoryTool(), category="filesystem")
    registry.register(DeleteFileTool(), category="filesystem")
