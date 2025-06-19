from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.routes import router

app = FastAPI(title="RAG PPT QA with Deepseek")

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(router)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 重定向根路径到前端页面
@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

# 在服务启动时显示帮助信息
@app.on_event("startup")
async def startup_event():
    from app.config import DEEPSEEK_API_KEY
    
    print("\n" + "="*60)
    print("  PDF 智能问答系统 - RAG-PDF-DeepSeek")
    print("="*60)
    
    if not DEEPSEEK_API_KEY:
        print("\n⚠️  警告: DEEPSEEK_API_KEY 环境变量未设置")
        print("请在终端使用以下命令设置 API 密钥:")
        print("  Windows: set DEEPSEEK_API_KEY=your_api_key")
        print("  Linux/Mac: export DEEPSEEK_API_KEY=your_api_key\n")
    else:
        print("\n✓ API 密钥已配置")
    
    print("\n访问地址: http://127.0.0.1:8000")
    print("="*60 + "\n")