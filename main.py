#!/usr/bin/env python3
"""
Web3 TGE Monitor API 主入口文件
启动FastAPI应用服务器
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入应用
from src.api.main import app
from src.database.database import init_database
from src.crawler.platform_factory import auto_register_platforms
import structlog

logger = structlog.get_logger()

async def startup_tasks():
    """应用启动时的初始化任务"""
    try:
        logger.info("Starting Web3 TGE Monitor API...")
        
        # 初始化数据库
        logger.info("Initializing database...")
        await init_database()
        
        # 自动注册平台
        logger.info("Auto-registering platforms...")
        auto_register_platforms()
        
        logger.info("Startup tasks completed successfully")
        
    except Exception as e:
        logger.error("Startup tasks failed", error=str(e))
        raise

# 添加启动事件处理器
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    await startup_tasks()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down Web3 TGE Monitor API...")

if __name__ == "__main__":
    import uvicorn
    
    # 运行启动任务
    asyncio.run(startup_tasks())
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
