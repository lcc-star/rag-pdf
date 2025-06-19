import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从环境变量中获取DeepSeek API密钥
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# DeepSeek API URL
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 存储路径配置
PDF_STORAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pdf")

# 向量维度
VECTOR_DIM = 384

# 向量存储路径
INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index", "vector.faiss")
META_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index", "meta.pkl")

# 检查API密钥是否设置
if not DEEPSEEK_API_KEY:
    logger.warning("⚠️ DEEPSEEK_API_KEY 环境变量未设置。请使用 'set DEEPSEEK_API_KEY=your_key' 设置密钥。")
else:
    # 显示部分掩码的API密钥，增加安全性
    masked_key = DEEPSEEK_API_KEY[:4] + '*' * (len(DEEPSEEK_API_KEY) - 8) + DEEPSEEK_API_KEY[-4:] if len(DEEPSEEK_API_KEY) > 8 else "****"
    logger.info(f"✓ 已加载DeepSeek API密钥: {masked_key}")

# 确保目录存在
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)