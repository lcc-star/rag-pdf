import os
import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any, Optional
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    从PDF文件中提取文本内容，按页面分块
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        包含每页文本内容和元数据的字典列表
    """
    try:
        logger.info(f"开始处理PDF文件: {file_path}")
        text_chunks = []
        
        # 打开PDF文件
        with fitz.open(file_path) as doc:
            # 获取文件名作为文档标题
            file_name = os.path.basename(file_path)
            
            # 提取文档属性
            metadata = doc.metadata
            doc_title = metadata.get("title", "") or file_name
            doc_author = metadata.get("author", "未知作者")
            page_count = len(doc)
            
            logger.info(f"PDF '{doc_title}' 共 {page_count} 页，作者: {doc_author}")
            
            # 处理每一页
            for page_num, page in enumerate(doc):
                # 提取页面文本
                text = page.get_text("text")
                
                # 如果页面内容为空，跳过
                if not text.strip():
                    continue
                
                # 创建页面标题
                page_title = f"第 {page_num + 1} 页"
                
                # 页面元数据
                page_metadata = {
                    "source_type": "pdf",
                    "file_name": file_name,
                    "doc_title": doc_title,
                    "doc_author": doc_author,
                    "page_num": page_num + 1,
                    "total_pages": page_count,
                }
                
                # 构建内容块
                content = f"标题: {doc_title}\n页码: {page_num + 1}/{page_count}\n\n{text}"
                
                # 添加到结果列表
                text_chunks.append({
                    "content": content,
                    "metadata": page_metadata
                })
        
        logger.info(f"从PDF提取了 {len(text_chunks)} 页内容")
        return text_chunks
        
    except Exception as e:
        logger.error(f"处理PDF文件 {file_path} 时出错: {str(e)}", exc_info=True)
        return []

def extract_text_with_chunking(file_path: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    从PDF中提取文本，并分割成指定大小的块，便于精确检索
    
    Args:
        file_path: PDF文件路径
        chunk_size: 每个文本块的最大字符数
        overlap: 相邻块之间的重叠字符数
        
    Returns:
        文本块列表
    """
    try:
        # 先提取完整的页面内容
        page_chunks = extract_text_from_pdf(file_path)
        
        # 如果内容不多，直接返回页面级别的块
        if len(page_chunks) <= 5:
            return page_chunks
        
        # 处理较大的PDF，进一步分块
        detailed_chunks = []
        
        for page_chunk in page_chunks:
            text = page_chunk["content"]
            metadata = page_chunk["metadata"]
            
            # 如果文本长度小于块大小，直接添加
            if len(text) <= chunk_size:
                detailed_chunks.append(page_chunk)
                continue
            
            # 分割文本
            start = 0
            chunk_num = 1
            
            while start < len(text):
                # 计算当前块的结束位置
                end = min(start + chunk_size, len(text))
                
                # 如果不是文本的结尾，尽量在一个完整的句子结束位置断开
                if end < len(text):
                    # 寻找适合的断句点
                    break_points = ['.', '!', '?', '\n', '。', '！', '？', '；', ';']
                    best_end = end
                    
                    # 在块大小范围内找最后的断句点
                    for point in break_points:
                        pos = text.rfind(point, start, end)
                        if pos > start and (pos + 1) > best_end - 200:  # 确保找到的位置不会使块太小
                            best_end = pos + 1
                            break
                    
                    end = best_end
                
                # 创建新的块
                new_metadata = metadata.copy()
                new_metadata["chunk_num"] = chunk_num
                new_metadata["sub_chunk"] = True
                
                chunk_content = text[start:end].strip()
                if chunk_content:
                    detailed_chunks.append({
                        "content": chunk_content,
                        "metadata": new_metadata
                    })
                
                # 更新下一个块的起始位置，考虑重叠
                start = max(0, end - overlap)
                chunk_num += 1
        
        logger.info(f"PDF细分为 {len(detailed_chunks)} 个文本块")
        return detailed_chunks
        
    except Exception as e:
        logger.error(f"PDF分块处理失败: {str(e)}", exc_info=True)
        return []