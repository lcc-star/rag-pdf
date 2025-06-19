import faiss
import numpy as np
import os
import pickle
import logging
from app.config import INDEX_PATH, META_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, dim):
        self.dim = dim
        self.index = None
        self.text_chunks = []
        
    def add(self, embeddings, texts, file_name=None):
        """添加文本和对应的嵌入到存储"""
        try:
            if self.index is None:
                self.index = faiss.IndexFlatL2(self.dim)
                
            if isinstance(embeddings, list):
                embeddings_np = np.array(embeddings).astype('float32')
            else:
                embeddings_np = embeddings.astype('float32')
        
            # 确保文本块包含必要的元数据
            normalized_texts = []
            for i, text_item in enumerate(texts):
                if isinstance(text_item, dict) and 'content' in text_item:
                    # 确保元数据包含文件名等信息
                    if 'metadata' not in text_item or not text_item['metadata']:
                        text_item['metadata'] = {
                            'chunk_id': i + 1,
                            'file_name': file_name or "未命名文档"
                        }
                    elif 'file_name' not in text_item['metadata'] and file_name:
                        text_item['metadata']['file_name'] = file_name
                    normalized_texts.append(text_item)
                elif isinstance(text_item, str):
                    # 将纯文本转换为包含元数据的字典
                    normalized_texts.append({
                        'content': text_item,
                        'metadata': {
                            'chunk_id': i + 1,
                            'file_name': file_name or "未命名文档"
                        }
                    })
                else:
                    logger.warning(f"跳过不支持的文本格式: {type(text_item)}")
                    continue
                
            self.index.add(embeddings_np)
            self.text_chunks.extend(normalized_texts)
            logger.info(f"添加了 {len(normalized_texts)} 条文本到向量存储")
        except Exception as e:
            logger.error(f"添加向量失败: {str(e)}", exc_info=True)
            raise
            
    def save(self):
        """保存索引和文本块到文件"""
        try:
            if self.index is not None:
                faiss.write_index(self.index, INDEX_PATH)
                with open(META_PATH, 'wb') as f:
                    pickle.dump(self.text_chunks, f)
                logger.info(f"向量存储已保存，包含 {len(self.text_chunks)} 条文本")
            else:
                logger.warning("尝试保存空索引")
        except Exception as e:
            logger.error(f"保存向量存储失败: {str(e)}", exc_info=True)
            raise
            
    def load(self):
        """从文件加载索引和文本块"""
        try:
            if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
                self.index = faiss.read_index(INDEX_PATH)
                with open(META_PATH, 'rb') as f:
                    self.text_chunks = pickle.load(f)
                logger.info(f"向量存储已加载，包含 {len(self.text_chunks)} 条文本")
            else:
                self.index = faiss.IndexFlatL2(self.dim)
                self.text_chunks = []
                logger.info("创建了新的向量存储")
        except Exception as e:
            logger.error(f"加载向量存储失败: {str(e)}", exc_info=True)
            self.index = faiss.IndexFlatL2(self.dim)
            self.text_chunks = []
            
    def search(self, query_embedding, top_k=5, threshold=0.0):  # 将默认阈值降低到0
        """搜索最相似的文本块"""
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("向量存储为空，无法搜索")
                return []
                
            if len(self.text_chunks) == 0:
                logger.warning("文本块列表为空，无法搜索")
                return []
            
            # 确保查询向量格式正确
            if not isinstance(query_embedding, np.ndarray):
                logger.info(f"转换查询向量类型: {type(query_embedding)} -> numpy.ndarray")
                query_embedding = np.array([query_embedding]).astype('float32')
            elif len(query_embedding.shape) == 1:
                # 如果是一维数组，转换为二维
                query_embedding = query_embedding.reshape(1, -1).astype('float32')
            else:
                query_embedding = query_embedding.astype('float32')
            
            logger.info(f"查询向量形状: {query_embedding.shape}")
            
            # 执行搜索
            top_k = min(top_k, len(self.text_chunks))
            D, I = self.index.search(query_embedding, top_k)
            
            logger.info(f"检索结果距离分数: {D[0]}")
            
            # 改进相似度计算公式，确保能够得到有效值
            similarities = []
            for d in D[0]:
                if d > 0:
                    sim = 1.0 / (1.0 + d/2.0)  # 使用倒数关系确保距离越小相似度越高
                else:
                    sim = 1.0
                similarities.append(sim)
                
            logger.info(f"改进的相似度分数: {similarities}")
            
            # 添加相似度分数到结果中
            results = []
            for idx, sim in zip(I[0], similarities):
                if idx >= 0 and idx < len(self.text_chunks):
                    chunk = self.text_chunks[idx]
                    
                    # 深拷贝避免修改原始数据
                    import copy
                    chunk_copy = copy.deepcopy(chunk)
                    
                    # 添加相似度分数
                    if isinstance(chunk_copy, dict):
                        chunk_copy["score"] = float(sim)
                        results.append(chunk_copy)
                    else:
                        results.append({
                            "content": chunk_copy,
                            "score": float(sim),
                            "metadata": {}
                        })
            
            # 按相似度排序
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}", exc_info=True)
            return []
        
    def clear(self):
        """完全清除向量存储中的所有数据"""
        self.collection.delete(
            filter={}  # 空过滤器表示删除所有内容
        )
        logger.info("向量存储已完全清除")
        
    def get_sources_from_texts(self, texts):
        """从检索到的文本中提取来源信息"""
        sources = []
        for text in texts:
            content = text.page_content if hasattr(text, 'page_content') else text.get('content', '')
            metadata = text.metadata if hasattr(text, 'metadata') else text.get('metadata', {})
            
            # 确保元数据是字典类型
            if not isinstance(metadata, dict):
                metadata = {}
            
            # 获取文件名，明确定义默认值
            file_name = metadata.get('file_name')
            if not file_name:
                # 尝试其他可能的元数据字段
                file_name = metadata.get('source') or metadata.get('path')
                
                # 如果仍然没有文件名，记录日志并使用默认值
                if not file_name:
                    logger.warning(f"检索结果缺少文件名信息: {metadata}")
                    file_name = "未知文件"
        
            # 获取页码或幻灯片编号
            page_num = metadata.get('page_num') or metadata.get('slide_num') or ''
            
            # 提取内容前100个字符作为摘要
            summary = content[:100] + ('...' if len(content) > 100 else '')
            
            sources.append({
                'file_name': file_name,
                'page_num': page_num,
                'summary': summary
            })
        
        return sources
