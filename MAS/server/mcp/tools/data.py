"""
数据处理相关的 MCP 工具
"""
import json
import csv
import io
from typing import Dict, Any, List, Optional
import pandas as pd
from pathlib import Path

from ..base import MCPTool, ToolDefinition, ToolParameter, ToolResult


class JsonProcessTool(MCPTool):
    """JSON 数据处理工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="json_process",
            description="Process JSON data with various operations",
            parameters=[
                ToolParameter(
                    name="data",
                    type="string",
                    description="JSON string to process"
                ),
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform",
                    enum=["parse", "format", "query", "transform", "validate"]
                ),
                ToolParameter(
                    name="query_path",
                    type="string",
                    description="JSONPath query (for 'query' operation)",
                    required=False
                ),
                ToolParameter(
                    name="transform_rules",
                    type="object",
                    description="Transformation rules (for 'transform' operation)",
                    required=False
                ),
                ToolParameter(
                    name="indent",
                    type="number",
                    description="Indentation for formatting",
                    required=False,
                    default=2
                )
            ],
            returns="object"
        )
    
    async def execute(self, data: str, operation: str, 
                     query_path: str = None,
                     transform_rules: Dict[str, Any] = None,
                     indent: int = 2) -> ToolResult:
        try:
            # 解析 JSON
            try:
                json_data = json.loads(data)
            except json.JSONDecodeError as e:
                if operation != "validate":
                    return ToolResult(
                        success=False,
                        result=None,
                        error=f"Invalid JSON: {str(e)}"
                    )
                else:
                    # 验证操作返回验证结果
                    return ToolResult(
                        success=True,
                        result={
                            "valid": False,
                            "error": str(e)
                        }
                    )
            
            result = None
            
            if operation == "parse":
                result = json_data
                
            elif operation == "format":
                result = json.dumps(json_data, indent=indent, ensure_ascii=False)
                
            elif operation == "query":
                if not query_path:
                    return ToolResult(
                        success=False,
                        result=None,
                        error="query_path is required for query operation"
                    )
                
                # 简单的 JSONPath 实现
                from jsonpath_ng import parse
                jsonpath_expr = parse(query_path)
                matches = [match.value for match in jsonpath_expr.find(json_data)]
                result = matches
                
            elif operation == "transform":
                if not transform_rules:
                    return ToolResult(
                        success=False,
                        result=None,
                        error="transform_rules is required for transform operation"
                    )
                
                # 简单的转换实现
                result = self._apply_transform(json_data, transform_rules)
                
            elif operation == "validate":
                result = {
                    "valid": True,
                    "data": json_data
                }
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "operation": operation,
                    "input_size": len(data)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def _apply_transform(self, data: Any, rules: Dict[str, Any]) -> Any:
        """应用转换规则"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in rules:
                    rule = rules[key]
                    if isinstance(rule, dict) and "_rename" in rule:
                        new_key = rule["_rename"]
                        result[new_key] = value
                    elif isinstance(rule, dict) and "_transform" in rule:
                        # 递归应用转换
                        result[key] = self._apply_transform(value, rule["_transform"])
                    else:
                        result[key] = value
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._apply_transform(item, rules) for item in data]
        else:
            return data


class CsvProcessTool(MCPTool):
    """CSV 数据处理工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="csv_process",
            description="Process CSV data with various operations",
            parameters=[
                ToolParameter(
                    name="data",
                    type="string",
                    description="CSV string to process"
                ),
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform",
                    enum=["parse", "filter", "aggregate", "transform", "to_json"]
                ),
                ToolParameter(
                    name="delimiter",
                    type="string",
                    description="CSV delimiter",
                    required=False,
                    default=","
                ),
                ToolParameter(
                    name="filter_column",
                    type="string",
                    description="Column name for filtering",
                    required=False
                ),
                ToolParameter(
                    name="filter_value",
                    type="string",
                    description="Value to filter by",
                    required=False
                ),
                ToolParameter(
                    name="aggregate_column",
                    type="string",
                    description="Column to aggregate",
                    required=False
                ),
                ToolParameter(
                    name="aggregate_function",
                    type="string",
                    description="Aggregation function",
                    required=False,
                    enum=["sum", "mean", "count", "min", "max"]
                )
            ],
            returns="object"
        )
    
    async def execute(self, data: str, operation: str,
                     delimiter: str = ",",
                     filter_column: str = None,
                     filter_value: str = None,
                     aggregate_column: str = None,
                     aggregate_function: str = None) -> ToolResult:
        try:
            # 读取 CSV 数据
            df = pd.read_csv(io.StringIO(data), delimiter=delimiter)
            
            result = None
            
            if operation == "parse":
                # 转换为字典列表
                result = df.to_dict(orient='records')
                
            elif operation == "filter":
                if not filter_column or filter_value is None:
                    return ToolResult(
                        success=False,
                        result=None,
                        error="filter_column and filter_value are required for filter operation"
                    )
                
                # 过滤数据
                filtered_df = df[df[filter_column] == filter_value]
                result = filtered_df.to_dict(orient='records')
                
            elif operation == "aggregate":
                if not aggregate_column or not aggregate_function:
                    return ToolResult(
                        success=False,
                        result=None,
                        error="aggregate_column and aggregate_function are required for aggregate operation"
                    )
                
                # 聚合操作
                if aggregate_function == "sum":
                    result = df[aggregate_column].sum()
                elif aggregate_function == "mean":
                    result = df[aggregate_column].mean()
                elif aggregate_function == "count":
                    result = len(df)
                elif aggregate_function == "min":
                    result = df[aggregate_column].min()
                elif aggregate_function == "max":
                    result = df[aggregate_column].max()
                
            elif operation == "transform":
                # 返回描述性统计
                result = {
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.to_dict(),
                    "summary": df.describe().to_dict()
                }
                
            elif operation == "to_json":
                result = df.to_json(orient='records', force_ascii=False)
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "operation": operation,
                    "rows": len(df),
                    "columns": len(df.columns)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class TextAnalysisTool(MCPTool):
    """文本分析工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="text_analysis",
            description="Analyze text with various operations",
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to analyze"
                ),
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Analysis operation",
                    enum=["word_count", "char_count", "line_count", "frequency", "summary"]
                ),
                ToolParameter(
                    name="top_n",
                    type="number",
                    description="Number of top items to return (for frequency analysis)",
                    required=False,
                    default=10
                )
            ],
            returns="object"
        )
    
    async def execute(self, text: str, operation: str, top_n: int = 10) -> ToolResult:
        try:
            result = None
            
            if operation == "word_count":
                words = text.split()
                result = {
                    "total_words": len(words),
                    "unique_words": len(set(words))
                }
                
            elif operation == "char_count":
                result = {
                    "total_chars": len(text),
                    "chars_no_spaces": len(text.replace(" ", "")),
                    "spaces": text.count(" ")
                }
                
            elif operation == "line_count":
                lines = text.split('\n')
                result = {
                    "total_lines": len(lines),
                    "non_empty_lines": len([line for line in lines if line.strip()])
                }
                
            elif operation == "frequency":
                from collections import Counter
                words = text.lower().split()
                word_freq = Counter(words)
                result = {
                    "top_words": dict(word_freq.most_common(top_n)),
                    "total_unique": len(word_freq)
                }
                
            elif operation == "summary":
                words = text.split()
                result = {
                    "length": len(text),
                    "words": len(words),
                    "lines": len(text.split('\n')),
                    "paragraphs": len([p for p in text.split('\n\n') if p.strip()]),
                    "average_word_length": sum(len(word) for word in words) / len(words) if words else 0
                }
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "operation": operation,
                    "text_length": len(text)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


class DataConversionTool(MCPTool):
    """数据格式转换工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="data_convert",
            description="Convert data between different formats",
            parameters=[
                ToolParameter(
                    name="data",
                    type="string",
                    description="Data to convert"
                ),
                ToolParameter(
                    name="from_format",
                    type="string",
                    description="Source format",
                    enum=["json", "csv", "xml", "yaml"]
                ),
                ToolParameter(
                    name="to_format",
                    type="string",
                    description="Target format",
                    enum=["json", "csv", "xml", "yaml"]
                ),
                ToolParameter(
                    name="options",
                    type="object",
                    description="Conversion options",
                    required=False,
                    default={}
                )
            ],
            returns="string"
        )
    
    async def execute(self, data: str, from_format: str, to_format: str,
                     options: Dict[str, Any] = None) -> ToolResult:
        try:
            options = options or {}
            
            # 首先将数据解析为通用格式
            parsed_data = None
            
            if from_format == "json":
                parsed_data = json.loads(data)
            elif from_format == "csv":
                df = pd.read_csv(io.StringIO(data))
                parsed_data = df.to_dict(orient='records')
            elif from_format == "yaml":
                import yaml
                parsed_data = yaml.safe_load(data)
            elif from_format == "xml":
                # 简单的 XML 处理
                return ToolResult(
                    success=False,
                    result=None,
                    error="XML format not fully implemented yet"
                )
            
            # 转换为目标格式
            result = None
            
            if to_format == "json":
                indent = options.get("indent", 2)
                result = json.dumps(parsed_data, indent=indent, ensure_ascii=False)
            elif to_format == "csv":
                df = pd.DataFrame(parsed_data)
                result = df.to_csv(index=False)
            elif to_format == "yaml":
                import yaml
                result = yaml.dump(parsed_data, allow_unicode=True, default_flow_style=False)
            elif to_format == "xml":
                return ToolResult(
                    success=False,
                    result=None,
                    error="XML format not fully implemented yet"
                )
            
            # 如果需要，保存到工作空间
            output_file = None
            if options.get("save_to_Codespace"):
                filename = options.get("filename", f"converted.{to_format}")
                output_file = {
                    "name": filename,
                    "content": result
                }
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "from_format": from_format,
                    "to_format": to_format,
                    "output_size": len(result),
                    "output_file": output_file
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


def register_data_tools(registry):
    """注册数据处理工具"""
    registry.register(JsonProcessTool(), category="data")
    registry.register(CsvProcessTool(), category="data")
    registry.register(TextAnalysisTool(), category="data")
    registry.register(DataConversionTool(), category="data")
