from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.pdf_loader import extract_text_with_chunking  # 新增PDF处理
from app.embedder import embed_texts
from app.vector_store import VectorStore
from app.rag_engine import generate_answer
from app.config import VECTOR_DIM, PDF_STORAGE_PATH, INDEX_PATH, META_PATH  # 添加索引和元数据路径
import os
import logging
import requests
import numpy as np
import shutil
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()

# 创建向量存储
vs = VectorStore(dim=VECTOR_DIM)

# 确保PDF存储路径存在
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """上传并处理PDF文件"""
    try:
        # 检查文件类型
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只接受PDF文件格式")
            
        # 保存文件
        file_path = os.path.join(PDF_STORAGE_PATH, file.filename)
        file_exists = os.path.exists(file_path)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # 根据文件是否存在返回不同消息
        operation = "更新" if file_exists else "上传"
        logger.info(f"成功保存PDF文件: {file.filename}")
            
        # 处理文件内容
        try:
            # 提取文本
            chunks = extract_text_with_chunking(file_path)
            
            if not chunks:
                logger.warning(f"从PDF中没有提取到文本内容: {file.filename}")
                return {
                    "message": f"文件已{operation}，但未能提取到内容", 
                    "file": file.filename
                }
                
            logger.info(f"从PDF中提取了 {len(chunks)} 个文本块")
                
            # 生成嵌入向量
            embeddings = embed_texts([chunk["content"] for chunk in chunks])
            
            # 如果文件已存在，需要更新索引
            vs.load()
            if file_exists:
                # 过滤掉与当前文件相关的内容
                if vs.text_chunks:
                    vs.text_chunks = [chunk for chunk in vs.text_chunks 
                                     if not (isinstance(chunk, dict) and 
                                            chunk.get('metadata', {}).get('file_name') == file.filename)]
                    
                # 重建索引
                vs.index = None
                vs.load()  # 创建新索引
            
            # 添加新的索引
            vs.add(embeddings, chunks)
            vs.save()
            
            return {
                "message": f"成功{operation}并索引PDF文件", 
                "file": file.filename,
                "chunks": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"处理PDF内容时出错: {str(e)}", exc_info=True)
            return {
                "message": f"文件已{operation}，但处理内容失败", 
                "file": file.filename,
                "error": str(e)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")

@router.get("/list-files")
async def list_files():
    """获取所有已上传的PDF文件"""
    try:
        files = []
        
        if os.path.exists(PDF_STORAGE_PATH):
            for filename in os.listdir(PDF_STORAGE_PATH):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(PDF_STORAGE_PATH, filename)
                    file_stats = os.stat(file_path)
                    
                    files.append({
                        "name": filename,
                        "size": file_stats.st_size,
                        "modified": file_stats.st_mtime,
                        "type": "pdf"
                    })
                    
        return files
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """删除指定的PDF文件"""
    try:
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只能删除PDF文件")
            
        file_path = os.path.join(PDF_STORAGE_PATH, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
            
        # 删除文件
        os.remove(file_path)
        logger.info(f"已删除PDF文件: {filename}")
        
        # 更新索引（移除相关内容）
        vs.load()
        if vs.text_chunks:
            original_count = len(vs.text_chunks)
            vs.text_chunks = [chunk for chunk in vs.text_chunks 
                             if not (isinstance(chunk, dict) and 
                                    chunk.get('metadata', {}).get('file_name') == filename)]
                                    
            if len(vs.text_chunks) < original_count:
                # 有内容被移除，需要重建索引
                vs.index = None
                vs.load()  # 创建新索引
                
                # 重新添加其他文档的内容
                if vs.text_chunks:
                    embeddings = embed_texts([chunk["content"] for chunk in vs.text_chunks])
                    vs.add(embeddings, vs.text_chunks)
                
                vs.save()
                logger.info(f"已从索引中移除文件相关内容: {filename}")
        
        return {"message": f"成功删除文件及其索引: {filename}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@router.post("/rebuild-index")
async def rebuild_index():
    """重新构建所有PDF文件的索引"""
    try:
        # 检查文件夹是否存在
        if not os.path.exists(PDF_STORAGE_PATH):
            return {"message": "没有PDF文件夹，无需重建索引"}
        
        # 获取所有PDF文件
        pdf_files = [f for f in os.listdir(PDF_STORAGE_PATH) if f.endswith('.pdf')]
        
        if not pdf_files:
            return {"message": "没有找到PDF文件，无需重建索引"}
        
        # 清空现有索引
        vs.index = None
        vs.text_chunks = []
        
        # 创建新索引
        vs.load()
        
        total_chunks = 0
        processed_files = []
        
        # 处理每个PDF文件
        for filename in pdf_files:
            try:
                file_path = os.path.join(PDF_STORAGE_PATH, filename)
                
                # 提取文本
                chunks = extract_text_with_chunking(file_path)
                if chunks:
                    # 生成嵌入
                    embeddings = embed_texts([chunk["content"] for chunk in chunks])
                    
                    # 添加到索引
                    vs.add(embeddings, chunks)
                    
                    total_chunks += len(chunks)
                    processed_files.append({
                        "name": filename,
                        "chunks": len(chunks)
                    })
                    
                    logger.info(f"已处理文件 {filename}，提取了 {len(chunks)} 个文本块")
            except Exception as e:
                logger.error(f"处理文件 {filename} 时出错: {str(e)}", exc_info=True)
        
        # 保存索引
        if total_chunks > 0:
            vs.save()
            
        return {
            "message": f"索引重建完成，处理了 {len(processed_files)} 个PDF文件，共 {total_chunks} 个文本块",
            "processed_files": processed_files
        }
    except Exception as e:
        logger.error(f"重建索引失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")

@router.post("/ask")
async def ask_question(question: str = Form(...), question_type: Optional[str] = Form(None)):
    """处理用户问题并生成回答"""
    if not question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
        
    try:
        logger.info(f"收到问题: {question}, 类型: {question_type or '未指定'}")
        
        # 检查问题类型
        if question_type not in (None, "strict", "semantic"):
            question_type = None  # 默认为语义匹配
            
        # 自动判断是否为填空题
        if "_____" in question or "____" in question or "__" in question:
            logger.info("检测到填空题格式")
        
        # 检查向量存储是否有数据
        vs.load()
        if vs.index is None or vs.index.ntotal == 0:
            return {"answer": "请先上传PDF文件，然后再提问。"}
            
        # 生成问题的嵌入向量
        try:
            q_embedding = embed_texts([question])
            
            # 正确地检查嵌入向量
            if q_embedding is None or not isinstance(q_embedding, (list, np.ndarray)) or (isinstance(q_embedding, (list, np.ndarray)) and len(q_embedding) == 0):
                raise ValueError("无法生成问题的嵌入向量")
                
            # 确保我们得到第一个向量
            if isinstance(q_embedding, list):
                q_embedding = q_embedding[0]
                
            logger.info(f"成功生成问题嵌入向量，形状: {q_embedding.shape if hasattr(q_embedding, 'shape') else '未知'}")
                
        except Exception as e:
            logger.error(f"嵌入向量生成失败: {str(e)}", exc_info=True)
            return {"answer": "处理您的问题时出现错误。请稍后再试。"}
        
        # 检索相关内容
        try:
            # 对于严格匹配，增加检索数量
            top_k = 10 if question_type == "strict" else 5
            relevant = vs.search(q_embedding, top_k=top_k)
            logger.info(f"检索到 {len(relevant)} 个相关片段")
        except Exception as e:
            logger.error(f"检索失败: {str(e)}", exc_info=True)
            return {"answer": "检索PDF内容时出现错误。请稍后再试。"}
        
        # 生成回答
        try:
            answer = generate_answer(question, relevant, question_type)
            return {"answer": answer}
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}", exc_info=True)
            return {"answer": "生成回答时出现错误。请稍后再试。"}
            
    except Exception as e:
        logger.error(f"处理问题失败: {str(e)}", exc_info=True)
        return {"answer": "处理您的问题时出现错误。请稍后再试。"}

@router.get("/preview/{filename}")
async def preview_file(filename: str):
    """获取PDF文件内容预览"""
    try:
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只能预览PDF文件")
            
        file_path = os.path.join(PDF_STORAGE_PATH, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
            
        # 提取内容预览
        chunks = extract_text_with_chunking(file_path)
        preview = [chunk["content"][:200] + "..." for chunk in chunks[:5]]
        
        return {
            "filename": filename,
            "total_pages": len(chunks),
            "preview": preview
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预览失败: {str(e)}")

@router.get("/debug/status")
async def debug_status():
    """返回系统状态信息，用于调试"""
    try:
        vs.load()
        return {
            "pdf_path": PDF_STORAGE_PATH,
            "pdf_exists": os.path.exists(PDF_STORAGE_PATH),
            "pdf_files": [f for f in os.listdir(PDF_STORAGE_PATH) if f.endswith('.pdf')] if os.path.exists(PDF_STORAGE_PATH) else [],
            "index_path": INDEX_PATH,
            "index_exists": os.path.exists(INDEX_PATH),
            "meta_path": META_PATH,
            "meta_exists": os.path.exists(META_PATH),
            "has_index": vs.index is not None,
            "index_size": vs.index.ntotal if vs.index is not None else 0,
            "chunks_count": len(vs.text_chunks) if vs.text_chunks else 0
        }
    except Exception as e:
        return {"error": str(e)}
