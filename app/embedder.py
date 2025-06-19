import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 指定模型下载路径
model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
os.makedirs(model_dir, exist_ok=True)

# 使用本地路径加载模型
model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
model_path = os.path.join(model_dir, model_name)

# 检查模型是否已下载
if os.path.exists(model_path):
    model = SentenceTransformer(model_path)
else:
    # 首次下载时保存到本地路径
    model = SentenceTransformer(model_name, cache_folder=model_dir)

def embed_texts(texts):
    """
    将文本列表转换为嵌入向量
    
    Args:
        texts: 文本列表
    
    Returns:
        numpy数组形式的嵌入向量
    """
    try:
        if not texts:
            logger.warning("接收到空的文本列表")
            return np.array([])
            
        logger.info(f"对 {len(texts)} 条文本进行嵌入")
        embeddings = model.encode(texts, show_progress_bar=True)
        
        if len(embeddings) == 0:
            logger.warning("嵌入生成为空")
        else:
            logger.info(f"嵌入向量形状: {embeddings.shape}")
            
        return embeddings
    except Exception as e:
        logger.error(f"嵌入文本时出错: {str(e)}", exc_info=True)
        raise
