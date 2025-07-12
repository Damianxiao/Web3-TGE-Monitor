"""
TGE搜索API路由
提供统一的TGE项目搜索、爬取和AI分析功能
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog
import json

from ..models import ApiResponse, success_response, error_response
from ..dependencies import get_db
from ...crawler.crawler_manager import CrawlerManager
from ...crawler.platform_factory import PlatformFactory
from ...crawler.models import Platform
from ...ai.ai_client import AIClient
from ...database.crud import TGEProjectCRUD
from ...database.models import TGEProject
from ...config.settings import settings

logger = structlog.get_logger()

# 创建API路由器
router = APIRouter()


# 请求模型
class TGESearchRequest(BaseModel):
    """TGE搜索请求"""
    keywords: List[str] = Field(..., description="搜索关键词列表", min_items=1, max_items=10)
    max_count: int = Field(20, description="最大爬取数量", ge=1, le=100)
    timeout: int = Field(300, description="超时时间（秒）", ge=30, le=600)
    platforms: List[str] = Field(["xhs"], description="爬取平台列表")


# 响应模型
class TGEAnalysisResult(BaseModel):
    """TGE分析结果"""
    token_name: Optional[str] = Field(None, description="代币名称")
    token_symbol: Optional[str] = Field(None, description="代币符号")
    ai_summary: Optional[str] = Field(None, description="AI分析摘要")
    sentiment: Optional[str] = Field(None, description="市场情绪")
    recommendation: Optional[str] = Field(None, description="投资建议")
    risk_level: Optional[str] = Field(None, description="风险等级")
    confidence_score: Optional[float] = Field(None, description="AI置信度")
    tge_date: Optional[str] = Field(None, description="TGE时间")
    source_platform: str = Field(..., description="来源平台")
    source_count: int = Field(..., description="来源数量")


class TGESearchResponse(BaseModel):
    """TGE搜索响应"""
    analysis_results: List[TGEAnalysisResult] = Field(..., description="分析结果列表")
    search_summary: Dict[str, Any] = Field(..., description="搜索统计摘要")
    execution_time: float = Field(..., description="执行时间（秒）")
    timestamp: datetime = Field(..., description="响应时间戳")
    error_details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息（调试用）")


@router.post("/search",
            response_model=ApiResponse[TGESearchResponse],
            summary="统一TGE搜索分析",
            description="执行关键词搜索、内容爬取和AI分析的一体化流程")
async def search_tge_projects(
    request: TGESearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    统一TGE搜索分析接口
    
    执行完整的工作流程：
    1. 使用关键词爬取相关内容
    2. 对内容进行AI分析
    3. 提取TGE项目信息
    4. 返回专业的投资分析
    """
    start_time = time.time()
    
    try:
        logger.info("Starting TGE search analysis",
                   keywords=request.keywords,
                   max_count=request.max_count,
                   platforms=request.platforms)
        
        # 1. 执行多平台爬取
        all_crawled_content = []
        crawl_stats = {}
        detailed_errors = {}  # 收集详细错误信息
        
        for platform_name in request.platforms:
            try:
                logger.info(f"Starting crawl for platform: {platform_name}")
                
                # 转换平台名称为枚举
                try:
                    platform_enum = Platform(platform_name.lower())
                except ValueError:
                    logger.warning(f"Unknown platform: {platform_name}")
                    crawl_stats[platform_name] = {"status": "unknown_platform", "count": 0}
                    continue
                
                # 创建平台爬虫实例
                platform_crawler = await PlatformFactory.create_platform(platform_enum)
                if not platform_crawler:
                    logger.warning(f"Platform not available: {platform_name}")
                    crawl_stats[platform_name] = {"status": "unavailable", "count": 0}
                    continue
                
                # 检查平台是否可用
                if not await platform_crawler.is_available():
                    logger.warning(f"Platform not available: {platform_name}")
                    crawl_stats[platform_name] = {"status": "unavailable", "count": 0}
                    continue
                
                # 执行爬取
                crawled_content = await platform_crawler.crawl(
                    keywords=request.keywords,
                    max_count=request.max_count
                )
                
                all_crawled_content.extend(crawled_content)
                crawl_stats[platform_name] = {
                    "status": "success", 
                    "count": len(crawled_content)
                }
                
                logger.info(f"Crawl completed for {platform_name}",
                           count=len(crawled_content))
                
            except Exception as e:
                import traceback
                error_info = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "platform": platform_name
                }
                
                # 如果是PlatformError并且包含详细错误信息，提取出来
                if hasattr(e, 'detailed_errors') and e.detailed_errors:
                    error_info["platform_detailed_errors"] = e.detailed_errors

                # 如果是RetryError，尝试获取内部异常详情
                if hasattr(e, 'last_attempt') and hasattr(e.last_attempt, 'exception'):
                    inner_exception = e.last_attempt.exception()
                    error_info.update({
                        "inner_error_type": type(inner_exception).__name__,
                        "inner_error_message": str(inner_exception),
                        "retry_attempts": getattr(e.last_attempt, 'attempt_number', 'unknown')
                    })

                    # 如果内部异常也有详细错误信息
                    if hasattr(inner_exception, 'detailed_errors'):
                        error_info["inner_detailed_errors"] = inner_exception.detailed_errors

                # 为所有异常添加详细错误信息到platform_detailed_errors
                if "platform_detailed_errors" not in error_info:
                    error_info["platform_detailed_errors"] = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "error_context": "Platform crawling failed"
                    }
                
                detailed_errors[platform_name] = error_info
                
                logger.error(f"Crawl failed for platform {platform_name}", 
                           error=str(e), error_type=type(e).__name__)
                crawl_stats[platform_name] = {"status": "error", "count": 0, "error": str(e)}
                continue
        
        # 移除内容检查，让底层异常直接传播
        # if not all_crawled_content:
        #     raise HTTPException(
        #         status_code=404,
        #         detail="未找到相关内容，请尝试其他关键词"
        #     )
        
        # 2. 初始化AI客户端
        ai_config = {
            'api_url': settings.ai_api_base_url,
            'api_key': settings.ai_api_key,
            'model': settings.ai_model,
            'max_tokens': settings.ai_max_tokens,
            'temperature': settings.ai_temperature
        }
        ai_client = AIClient(ai_config)
        
        # 3. 批量AI分析
        logger.info("Starting AI analysis", content_count=len(all_crawled_content))
        
        analysis_results = []
        ai_stats = {"processed": 0, "failed": 0, "tokens_used": 0}
        
        for content in all_crawled_content:
            try:
                # 使用AI客户端分析内容
                ai_result = await ai_client.analyze_content(
                    content=f"{content.title}\n{content.content}",
                    analysis_type="tge_analysis"
                )
                
                if ai_result:
                    # 确保ai_result是字典类型
                    if isinstance(ai_result, str):
                        try:
                            ai_result = json.loads(ai_result)
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse AI result as JSON", result=ai_result)
                            ai_result = {"summary": ai_result}
                    
                    # 保存到数据库
                    from ...utils.deduplication import generate_content_hash
                    
                    tge_project = TGEProject(
                        project_name=content.title or f"TGE项目_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                        content_hash=generate_content_hash(content.content),
                        raw_content=content.raw_content,
                        source_platform=content.platform.value,
                        source_url=content.source_url,
                        source_user_id=content.author_id,
                        source_username=content.author_name,
                        
                        # AI分析结果
                        ai_summary=ai_result.get("summary"),
                        sentiment=ai_result.get("sentiment"),
                        recommendation=ai_result.get("recommendation"),
                        risk_level=ai_result.get("risk_level"),
                        confidence_score=ai_result.get("confidence_score"),
                        
                        # 提取的项目信息
                        token_name=ai_result.get("token_name"),
                        token_symbol=ai_result.get("token_symbol"),
                        tge_date=ai_result.get("tge_date"),
                        
                        # 状态字段
                        is_processed=True,
                        is_valid=True
                    )
                    
                    # 保存到数据库
                    saved_project = await TGEProjectCRUD.create(db, tge_project)
                    
                    # 构建返回结果
                    analysis_result = TGEAnalysisResult(
                        token_name=ai_result.get("token_name"),
                        token_symbol=ai_result.get("token_symbol"),
                        ai_summary=ai_result.get("summary"),
                        sentiment=ai_result.get("sentiment"),
                        recommendation=ai_result.get("recommendation"),
                        risk_level=ai_result.get("risk_level"),
                        confidence_score=ai_result.get("confidence_score"),
                        tge_date=ai_result.get("tge_date"),
                        source_platform=content.platform.value,
                        source_count=1
                    )
                    
                    analysis_results.append(analysis_result)
                    ai_stats["processed"] += 1
                    ai_stats["tokens_used"] += ai_result.get("tokens_used", 0)
                    
                else:
                    ai_stats["failed"] += 1
                    
            except Exception as e:
                logger.error("AI analysis failed for content", 
                           content_id=content.content_id, error=str(e))
                ai_stats["failed"] += 1
                continue
        
        # 4. 生成搜索摘要
        execution_time = time.time() - start_time
        
        search_summary = {
            "keywords": request.keywords,
            "total_crawled": len(all_crawled_content),
            "total_analyzed": ai_stats["processed"],
            "failed_analysis": ai_stats["failed"],
            "tokens_used": ai_stats["tokens_used"],
            "crawl_stats": crawl_stats,
            "platforms_used": request.platforms,
            "execution_time": execution_time
        }
        
        # 5. 构建响应
        response_data = TGESearchResponse(
            analysis_results=analysis_results,
            search_summary=search_summary,
            execution_time=execution_time,
            timestamp=datetime.utcnow(),
            error_details=detailed_errors if detailed_errors else None
        )
        
        # 根据是否有错误调整返回消息
        if detailed_errors:
            message = f"执行完成，但有{len(detailed_errors)}个平台出现错误。分析了{len(analysis_results)}个TGE项目"
            if not analysis_results:
                # 如果没有成功分析任何内容，返回带详细错误信息的成功响应
                response_data = TGESearchResponse(
                    analysis_results=[],
                    search_summary=search_summary,
                    execution_time=execution_time,
                    timestamp=datetime.utcnow(),
                    error_details=detailed_errors
                )
                
                return success_response(
                    data=response_data,
                    message="所有平台都出现错误，未获取到任何内容，详见error_details字段"
                )
        else:
            message = f"成功分析{len(analysis_results)}个TGE项目"
        
        logger.info("TGE search analysis completed",
                   total_results=len(analysis_results),
                   execution_time=execution_time,
                   errors=len(detailed_errors))
        
        return success_response(
            data=response_data,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error("TGE search analysis failed", 
                    error=str(e), execution_time=execution_time)
        raise HTTPException(
            status_code=500,
            detail=f"TGE搜索分析失败: {str(e)}"
        )


@router.get("/recent",
           response_model=ApiResponse[List[TGEAnalysisResult]],
           summary="获取最近分析结果",
           description="获取最近分析的TGE项目结果")
async def get_recent_analysis(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    hours: int = 24
):
    """
    获取最近的TGE分析结果
    """
    try:
        logger.info("Getting recent TGE analysis", limit=limit, hours=hours)
        
        # 计算时间范围
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        # 查询最近的项目
        recent_projects = await TGEProjectCRUD.get_recent_processed(
            db, since=since_time, limit=limit
        )
        
        # 转换为响应格式
        results = []
        for project in recent_projects:
            result = TGEAnalysisResult(
                token_name=project.token_name,
                token_symbol=project.token_symbol,
                ai_summary=project.ai_summary,
                sentiment=project.sentiment,
                recommendation=project.recommendation,
                risk_level=project.risk_level,
                confidence_score=project.confidence_score,
                tge_date=project.tge_date,
                source_platform=project.source_platform,
                source_count=1
            )
            results.append(result)
        
        return success_response(
            data=results,
            message=f"成功获取{len(results)}条最近分析"
        )
        
    except Exception as e:
        logger.error("Failed to get recent analysis", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取最近分析失败: {str(e)}"
        )