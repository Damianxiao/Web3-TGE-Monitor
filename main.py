"""
Web3 TGE Monitor - FastAPI主应用
提供REST API接口用于TGE项目监控和分析
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog
import time
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.api.routes import projects, crawler, ai_processing, system
from src.database.database import init_database
from src.api.middleware.logging import LoggingMiddleware
from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.api.models.responses import ErrorResponse

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时初始化数据库连接，关闭时清理资源
    """
    # 启动时执行
    logger.info("Starting Web3 TGE Monitor API", 
               version="1.0.0",
               debug=settings.app_debug)
    
    # 初始化数据库
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    yield
    
    # 关闭时执行
    logger.info("Shutting down Web3 TGE Monitor API")


# 创建FastAPI应用实例
app = FastAPI(
    title="Web3 TGE Monitor API",
    description="""Web3 TGE (Token Generation Events) 监控和分析API
    
    ## 功能特性
    
    * **多平台爬虫**: 支持小红书、抖音等平台的Web3内容爬取
    * **AI智能分析**: 使用AI对TGE项目进行分析和投资建议生成
    * **项目管理**: 完整的TGE项目数据管理和查询
    * **实时监控**: 实时爬虫任务状态监控
    
    ## API版本
    
    当前API版本: v1
    """,
    version="1.0.0",
    contact={
        "name": "Web3 TGE Monitor",
        "url": "https://github.com/your-repo/web3-tge-monitor"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# 添加中间件

# CORS中间件 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React开发服务器
        "http://localhost:8080",  # Vue开发服务器
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"]
)

# 受信任主机中间件
if not settings.app_debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

# 自定义中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)


# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    添加请求处理时间到响应头
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 全局异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    HTTP异常处理器
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=True,
            message=exc.detail,
            status_code=exc.status_code,
            path=str(request.url)
        ).dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    请求验证异常处理器
    """
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=True,
            message="Validation Error",
            status_code=422,
            path=str(request.url),
            details=error_details
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    通用异常处理器
    """
    logger.error("Unhandled exception", 
                error=str(exc),
                path=str(request.url),
                method=request.method)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=True,
            message="Internal Server Error" if not settings.app_debug else str(exc),
            status_code=500,
            path=str(request.url)
        ).dict()
    )


# 根路径
@app.get("/", 
         summary="API根路径",
         description="返回API基本信息和状态")
async def root():
    """
    API根路径，返回基本信息
    """
    return {
        "name": "Web3 TGE Monitor API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_base": "/api/v1"
    }


# 健康检查端点
@app.get("/health", 
         summary="健康检查",
         description="检查API服务健康状态")
async def health_check():
    """
    健康检查端点
    """
    try:
        # 可以添加数据库连接检查等
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "api": "healthy",
                "database": "healthy",  # 实际应该检查数据库连接
                "ai_service": "healthy"  # 实际应该检查AI服务
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# 注册API路由
app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["Projects"]
)

app.include_router(
    crawler.router,
    prefix="/api/v1/crawler",
    tags=["Crawler"]
)

app.include_router(
    ai_processing.router,
    prefix="/api/v1/ai",
    tags=["AI Processing"]
)

app.include_router(
    system.router,
    prefix="/api/v1/system",
    tags=["System"]
)


if __name__ == "__main__":
    import uvicorn
    
    # 开发环境启动配置
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )