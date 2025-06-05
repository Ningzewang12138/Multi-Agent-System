import logging
from typing import List, Dict, Any, Optional, Tuple
import os
import chardet
from pathlib import Path
import pypdf
from docx import Document
import re
import tiktoken

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """文档处理服务"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化文档处理器
        chunk_size: 文本块大小（字符数）
        chunk_overlap: 文本块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # 支持的文件类型
        self.supported_extensions = {
            '.txt', '.md', '.pdf', '.docx', '.doc',
            '.py', '.js', '.java', '.cpp', '.c', '.html', '.css'
        }
    
    def process_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        处理单个文件，返回文本内容和元数据
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            extension = path.suffix.lower()
            
            if extension not in self.supported_extensions:
                raise ValueError(f"Unsupported file type: {extension}")
            
            # 获取文件元数据
            metadata = {
                "source": str(path),
                "filename": path.name,
                "extension": extension,
                "size": path.stat().st_size,
                "modified_at": path.stat().st_mtime
            }
            
            # 根据文件类型处理
            if extension == '.pdf':
                text = self._process_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                text = self._process_docx(file_path)
            else:
                text = self._process_text_file(file_path)
            
            # 清理文本
            text = self._clean_text(text)
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            raise
    
    def _process_pdf(self, file_path: str) -> str:
        """处理 PDF 文件"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            return text
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            raise
    
    def _process_docx(self, file_path: str) -> str:
        """处理 Word 文档"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Failed to process DOCX: {e}")
            raise
    
    def _process_text_file(self, file_path: str) -> str:
        """处理文本文件"""
        try:
            # 检测文件编码
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
            
            # 读取文件
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
                
        except Exception as e:
            logger.error(f"Failed to process text file: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符但保留基本标点（修正转义字符）
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:，。！？；：、""''（）\\-]', ' ', text)
        # 移除多余的空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        将文本分割成块
        """
        if not text:
            return []
        
        chunks = []
        
        # 首先按段落分割
        paragraphs = text.split('\n\n')
        current_chunk = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = len(self.tokenizer.encode(paragraph))
            
            # 如果段落本身就太长，需要进一步分割
            if paragraph_tokens > self.chunk_size:
                # 如果当前块不为空，先保存
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, len(chunks), metadata))
                    current_chunk = ""
                    current_tokens = 0
                
                # 分割长段落
                sentences = re.split(r'[。！？.!?]+', paragraph)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                        
                    sentence_tokens = len(self.tokenizer.encode(sentence))
                    
                    if current_tokens + sentence_tokens > self.chunk_size:
                        if current_chunk:
                            chunks.append(self._create_chunk(current_chunk, len(chunks), metadata))
                            # 保留重叠部分
                            overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                            current_chunk = overlap_text + " " + sentence
                            current_tokens = len(self.tokenizer.encode(current_chunk))
                    else:
                        current_chunk += (" " if current_chunk else "") + sentence
                        current_tokens += sentence_tokens
            else:
                # 段落不太长，尝试添加到当前块
                if current_tokens + paragraph_tokens > self.chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, len(chunks), metadata))
                        # 保留重叠部分
                        overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                        current_chunk = overlap_text + "\n\n" + paragraph
                        current_tokens = len(self.tokenizer.encode(current_chunk))
                else:
                    current_chunk += ("\n\n" if current_chunk else "") + paragraph
                    current_tokens += paragraph_tokens
        
        # 保存最后一个块
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, len(chunks), metadata))
        
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, text: str, index: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建文本块"""
        chunk_metadata = metadata.copy() if metadata else {}
        chunk_metadata.update({
            "chunk_index": index,
            "chunk_size": len(text),
            "token_count": len(self.tokenizer.encode(text))
        })
        
        return {
            "text": text.strip(),
            "metadata": chunk_metadata
        }
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量"""
        return len(self.tokenizer.encode(text))