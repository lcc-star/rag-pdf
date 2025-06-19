import os
import requests
import json
import logging
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_answer(question, retrieved_chunks, question_type=None):
    try:
        # 检查API密钥是否已设置
        if not DEEPSEEK_API_KEY:
            return "错误: DeepSeek API密钥未设置。请在终端使用以下命令设置密钥:\n\n```\nset DEEPSEEK_API_KEY=your_api_key\n```\n\n然后重启服务。"
            
        # 检查检索结果
        if not retrieved_chunks:
            logger.warning("未检索到相关内容")
            return "抱歉，我在上传的文档中没有找到与您问题相关的内容。请尝试换一种方式提问，或上传包含相关信息的文件。"
        
        logger.info(f"检索到{len(retrieved_chunks)}个文本块")
        
        # 自动判断是否为填空题形式
        is_fill_blank = "_____" in question or "____" in question or "__" in question
        
        # 构造上下文和来源信息
        contexts = []
        sources = []
        
        for i, chunk in enumerate(retrieved_chunks):
            # 处理不同格式的检索结果
            if isinstance(chunk, dict) and 'content' in chunk:
                content = chunk['content']
                metadata = chunk.get('metadata', {})
                score = chunk.get('score', None)  # 获取相似度分数
            elif isinstance(chunk, str):
                content = chunk
                metadata = {}
                score = None
            else:
                logger.warning(f"跳过无效格式的检索结果: {type(chunk)}")
                continue
            
            # 提取源文件信息
            source_type = metadata.get('source_type', '')
            file_name = metadata.get('file_name', '未知文件')
            
            if not source_type and file_name:
                ext = os.path.splitext(file_name)[1].lower()
                source_type = 'pdf' if ext == '.pdf' else 'ppt'
                
            # 获取页码/幻灯片编号
            if source_type == 'pdf':
                page_num = metadata.get('page_num', i+1)
                reference_id = f"[{file_name}第{page_num}页]"
            else:
                slide_num = metadata.get('slide_num', i+1)
                reference_id = f"[{file_name}第{slide_num}页]"
            
            # 添加到上下文，包含相似度分数（如果有）
            if score is not None:
                score_info = f"(相关度: {score:.2f})"
                context_entry = f"{reference_id} {score_info}\n{content}"
            else:
                context_entry = f"{reference_id}\n{content}"
                
            contexts.append(context_entry)
            
            # 构造来源信息（简化格式：文件名+页码）
            if source_type == 'pdf':
                source_info = f"{reference_id}: PDF文件 \"{file_name}\" 第{page_num}页"
            else:
                source_info = f"{reference_id}: PPT文件 \"{file_name}\" 第{slide_num}页"
                
            sources.append(source_info)
        
        if not contexts:
            return "抱歉，提取检索内容时出现问题。请稍后再试。"
            
        context_text = "\n\n".join(contexts)
        sources_text = "\n".join(sources)
        
        # 构造针对不同类型问题的提示词
        if is_fill_blank:
            prompt = f"""你是专业的问答助手，需要根据提供的文档内容，回答用户的填空题问题。

请严格遵循以下规则：
1. 填空题必须使用文档中的原文作为答案，不能编造或推测
2. 必须指出答案来自哪个文档的哪一页，格式为[文件名第X页]
3. 严格依照文档原文，不要改变原文的任何内容
4. 如果文档中无法找到答案，直接说"在文档中找不到答案"
5. 回答格式必须是：答案是"xxx"，来自[文件名第X页]

文档内容：
{context_text}

文档来源信息：
{sources_text}

填空题问题：{question}

请填写答案并标注来源："""
        elif question_type == "strict":
            prompt = f"""你是严格匹配型问答助手。你需要根据文档内容，准确找到与问题关键词完全匹配的内容。

严格遵循以下规则：
1. 只使用与问题关键词严格匹配的文档段落回答
2. 直接引用原文回答问题，不要添加自己的解释
3. 必须在回答中标注信息来源，使用格式[文件名第X页]
4. 如果找不到与关键词严格匹配的内容，请说"文档中没有找到与关键词完全匹配的内容"
5. 在回答结束后，添加"来源："部分

文档内容：
{context_text}

文档来源信息：
{sources_text}

用户问题：{question}

请提供严格匹配的回答："""
        else:  # 默认语义匹配
            prompt = f"""你是语义匹配型问答助手。你需要理解问题的实际含义，找出语义相关的文档内容回答。

请严格遵循以下规则：
1. 理解问题的真正意图，寻找语义相关的内容，不仅限于关键词匹配
2. 提供完整而准确的答案，可以综合多个相关段落
3. 必须在回答中标注信息来源，使用格式[文件名第X页]
4. 如果多个文档段落支持你的回答，需要标注所有来源
5. 不要编造不在文档中的信息
6. 在回答结束后，添加"来源："部分，列出所有引用

文档内容：
{context_text}

文档来源信息：
{sources_text}

用户问题：{question}

请提供语义匹配的回答："""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个专业、准确的文档问答助手。你只基于给定的文档内容回答问题，并总是标注信息来源。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,  # 降低温度，增加确定性
            "max_tokens": 800
        }
        
        logger.info("发送API请求到Deepseek")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"API返回错误: {response.status_code}, {response.text[:200]}")
            return f"调用AI服务时出错，状态码: {response.status_code}"
        
        result = response.json()
        logger.info("成功获取API响应")
        
        return result["choices"][0]["message"]["content"]
        
    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return "抱歉，AI响应超时。请稍后再试。"
    except requests.exceptions.RequestException as e:
        logger.error(f"请求错误: {str(e)}")
        return "抱歉，连接AI服务时出现网络问题。请检查您的网络连接。"
    except KeyError as e:
        logger.error(f"解析API响应时出错: {str(e)}")
        return "抱歉，处理AI响应时出现错误。"
    except Exception as e:
        logger.error(f"未预期的错误: {str(e)}", exc_info=True)
        return "抱歉，处理您的问题时出现错误。请稍后再试。"
