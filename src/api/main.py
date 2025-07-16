"""
FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .routes import projects, crawler, ai_processing, system, tge_search
from .middleware.error_handler import add_error_handlers
from .middleware.logging import add_logging_middleware

logger = structlog.get_logger()

def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="Web3 TGE Monitor API",
        description="Web3代币发行事件监控和AI分析API系统",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生产环境中应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加自定义中间件
    add_error_handlers(app)
    add_logging_middleware(app)
    
    # 注册路由
    app.include_router(
        system.router,
        prefix="/api/v1/system",
        tags=["系统管理"]
    )
    
    app.include_router(
        crawler.router,
        prefix="/api/v1/crawler",
        tags=["爬虫管理"]
    )
    
    app.include_router(
        ai_processing.router,
        prefix="/api/v1/ai",
        tags=["AI处理"]
    )
    
    app.include_router(
        projects.router,
        prefix="/api/v1/projects",
        tags=["项目管理"]
    )
    
    app.include_router(
        tge_search.router,
        prefix="/api/v1/search",
        tags=["TGE搜索"]
    )
    
    @app.get("/", include_in_schema=False)
    async def root():
        """根路径"""
        return {
            "message": "Web3 TGE Monitor API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/system/health"
        }
    
    @app.get("/health", include_in_schema=False)
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}
    
    logger.info("FastAPI application created")
    return app

# 创建应用实例
app = create_app()