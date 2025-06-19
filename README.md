# PDF智能问答系统

基于RAG (Retrieval-Augmented Generation) 技术和DeepSeek大语言模型构建的PDF文档智能问答系统。上传PDF文档，立即获得准确的问答体验。

## 功能特点

- ✅ **PDF文档处理**：支持上传和管理多个PDF文件
- 🔍 **语义搜索**：基于向量数据库的高效语义检索
- 💡 **智能问答**：利用DeepSeek大语言模型提供精准回答
- 📄 **文档引用**：回答中自动包含来源文件名和页码
- 🔄 **多模式问答**：
  - 严格匹配模式：精确查找关键词对应的信息
  - 语义匹配模式：理解问题意图，综合回答相关内容
  - 填空题支持：自动识别并回答填空式问题

## 技术架构

- **前端**：HTML/CSS/JavaScript，响应式设计
- **后端**：FastAPI (Python)
- **向量检索**：FAISS向量数据库
- **文本嵌入**：Sentence Transformers
- **语言模型**：DeepSeek Chat API
- **PDF处理**：PyMuPDF

## 模型文件

由于 GitHub 大小限制，模型文件未包含在仓库中。运行代码时，模型会自动从 Hugging Face 下载，或者您可以手动下载模型文件：

1. 访问 https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
2. 下载模型文件并放在 `models/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/snapshots/86741b4e3f5cb7765a600d3a3d55a0f6a6cb443d/` 目录下

## 使用方法

### 环境配置

1. 克隆项目并安装依赖：

```bash
git clone [项目地址]
cd [项目目录]
pip install -r requirements.txt
```

2. 设置环境变量

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY="你的API密钥"

# Unix/Linux/macOS
export DEEPSEEK_API_KEY=你的API密钥
```

3. 运行应用

```bash
uvicorn app.main:app --reload
```

4. 访问接口文档

```
http://localhost:8000/docs
```

## API接口

- **POST /upload**: 上传PDF文件
- **POST /ask**: 根据上传的PDF内容回答问题

## 示例

```python
import requests

# 上传PDF
with open('sample.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/upload', files=files)
    print(response.json())

# 提问
data = {'question': '这个PDF的主要内容是什么?'}
response = requests.post('http://localhost:8000/ask', data=data)
print(response.json())
```