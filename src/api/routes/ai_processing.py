"""
AI处理API路由
提供AI分析和处理功能
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks
import structlog

from ..models import (
    ApiResponse, BatchOperationResponse,
    AIProcessRequest, BatchAIProcessRequest, AIAnalysisResponse,
    success_response, error_response
)
from ...ai import ai_processing_manager
from ...database.database import get_db_session
from ...database.crud import TGEProjectCRUD

logger = structlog.get_logger()

# 创建API路由器
router = APIRouter()


@router.post("/process",
            response_model=ApiResponse[AIAnalysisResponse],
            summary="单个AI分析",
            description="对指定项目进行AI分析，包括TGE分析、投资建议和情感分析")
async def process_single_project(
    request: AIProcessRequest
):
    """
    对单个项目进行AI分析
    
    分析流程：
    1. TGE项目信息提取
    2. 投资建议生成
    3. 情感分析（可选）
    4. 结果整合和保存
    
    如果项目已经处理过，除非指定 force_reprocess=true，否则返回现有结果。
    """
    try:
        logger.info("Processing single project", 
                   project_id=request.project_id,
                   include_sentiment=request.include_sentiment,
                   force_reprocess=request.force_reprocess)
        
        # 检查项目是否存在
        session = await get_db_session()
        async with session:
            project = await TGEProjectCRUD.get_by_id(session, request.project_id)
            if not project:
                raise HTTPException(
                    status_code=404,
                    detail=f"项目ID {request.project_id} 不存在"
                )
            
            # 检查是否已处理
            if project.is_processed and not request.force_reprocess:
                # 返回现有的AI分析结果
                analysis_response = _convert_to_analysis_response(project)
                return success_response(
                    data=analysis_response,
                    message="项目已处理，返回现有结果"
                )
        
        # 执行AI分析
        result = await ai_processing_manager.process_single_content(
            project_id=request.project_id,
            include_sentiment=request.include_sentiment
        )
        
        if not result.get('success', False):
            error_msg = result.get('error', 'AI分析失败')
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        
        # 获取更新后的项目数据
        async with get_db_session() as session:
            updated_project = await TGEProjectCRUD.get_by_id(session, request.project_id)
            analysis_response = _convert_to_analysis_response(updated_project)
        
        return success_response(
            data=analysis_response,
            message="AI分析完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process single project", 
                    project_id=request.project_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"AI分析失败: {str(e)}"
        )


@router.post("/batch-process",
            response_model=ApiResponse[BatchOperationResponse],
            summary="批量AI分析",
            description="批量处理未处理的项目，在后台异步执行")
async def batch_process_projects(
    request: BatchAIProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    批量处理未处理的项目
    
    该接口会在后台启动批量处理任务，对所有未处理的项目进行AI分析。
    处理进度可通过 /ai/statistics 接口查询。
    
    参数说明：
    - batch_size: 每批次处理的项目数量
    - max_concurrent: 最大并发处理数
    - include_sentiment: 是否包含情感分析
    """
    try:
        logger.info("Starting batch AI processing", 
                   batch_size=request.batch_size,
                   max_concurrent=request.max_concurrent,
                   include_sentiment=request.include_sentiment)
        
        # 获取未处理项目数量
        async with get_db_session() as session:
            unprocessed_count = await TGEProjectCRUD.count_unprocessed(session)
        
        if unprocessed_count == 0:
            return success_response(
                data=BatchOperationResponse(
                    total_items=0,
                    successful=0,
                    failed=0,
                    processing_time=0.0
                ),
                message="没有需要处理的项目"
            )
        
        # 添加后台任务
        background_tasks.add_task(
            _execute_batch_processing,
            request.batch_size,
            request.max_concurrent,
            request.include_sentiment
        )
        
        return success_response(
            data=BatchOperationResponse(
                total_items=unprocessed_count,
                successful=0,
                failed=0,
                processing_time=0.0
            ),
            message=f"批量处理任务已启动，将处理{unprocessed_count}个项目"
        )
        
    except Exception as e:
        logger.error("Failed to start batch processing", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"启动批量处理失败: {str(e)}"
        )


@router.get("/statistics",
           response_model=ApiResponse[dict],
           summary="获取AI处理统计",
           description="获取AI处理的统计信息，包括处理进度和成功率")
async def get_ai_statistics():
    """
    获取AI处理统计信息
    
    返回信息包括：
    - 总项目数
    - 已处理项目数
    - 未处理项目数
    - 处理进度百分比
    - 最后更新时间
    """
    try:
        logger.debug("Getting AI processing statistics")
        
        # 获取处理统计
        stats = await ai_processing_manager.get_processing_statistics()
        
        return success_response(
            data=stats,
            message="成功获取AI处理统计"
        )
        
    except Exception as e:
        logger.error("Failed to get AI statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取AI统计信息失败"
        )


@router.get("/status",
           response_model=ApiResponse[dict],
           summary="获取AI服务状态",
           description="获取AI处理服务的运行状态和健康信息")
async def get_ai_status():
    """
    获取AI服务状态
    
    返回信息包括：
    - AI服务状态
    - API连接状态
    - 最后健康检查时间
    - 服务版本信息
    """
    try:
        logger.debug("Getting AI service status")
        
        # 检查AI服务状态
        status_info = {
            "service_status": "running",
            "api_connected": True,
            "last_check": "2025-07-12T20:06:00Z",
            "model": "gpt-4o-mini",
            "api_url": "https://api.gpt.ge/v1/chat/completions",
            "version": "1.0.0"
        }
        
        # 可以在这里添加实际的AI服务健康检查
        try:
            # 简单的AI服务可用性检查
            from ...ai import ai_client
            if ai_client and hasattr(ai_client, 'api_url'):
                status_info["api_connected"] = True
                status_info["api_url"] = ai_client.api_url
            else:
                status_info["api_connected"] = False
                status_info["service_status"] = "disconnected"
        except Exception:
            status_info["api_connected"] = False
            status_info["service_status"] = "error"
        
        return success_response(
            data=status_info,
            message="成功获取AI服务状态"
        )
        
    except Exception as e:
        logger.error("Failed to get AI status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取AI服务状态失败"
        )


@router.get("/unprocessed",
           response_model=ApiResponse[List[dict]],
           summary="获取未处理项目",
           description="获取等待AI分析的项目列表")
async def get_unprocessed_projects(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制")
):
    """
    获取等待AI分析的项目列表
    
    返回最近创建的未处理项目，便于管理员查看处理队列。
    """
    try:
        logger.info("Getting unprocessed projects", limit=limit)
        
        # 获取未处理项目
        from ...crawler.data_service import crawl_data_service
        unprocessed_projects = await crawl_data_service.get_unprocessed_contents(limit)
        
        return success_response(
            data=unprocessed_projects,
            message=f"成功获取{len(unprocessed_projects)}个未处理项目"
        )
        
    except Exception as e:
        logger.error("Failed to get unprocessed projects", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取未处理项目失败"
        )


@router.post("/reprocess/{project_id}",
            response_model=ApiResponse[AIAnalysisResponse],
            summary="重新分析项目",
            description="强制重新对指定项目进行AI分析")
async def reprocess_project(
    project_id: int = Path(..., ge=1, description="项目ID"),
    include_sentiment: bool = Query(True, description="是否包含情感分析")
):
    """
    重新分析项目
    
    强制重新对指定项目进行AI分析，即使该项目已经处理过。
    适用于：
    - AI模型更新后重新分析
    - 修复错误的分析结果
    - 测试新的分析参数
    """
    try:
        logger.info("Reprocessing project", 
                   project_id=project_id,
                   include_sentiment=include_sentiment)
        
        # 执行重新分析
        result = await ai_processing_manager.process_single_content(
            project_id=project_id,
            include_sentiment=include_sentiment
        )
        
        if not result.get('success', False):
            error_msg = result.get('error', 'AI重新分析失败')
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        
        # 获取更新后的项目数据
        async with get_db_session() as session:
            updated_project = await TGEProjectCRUD.get_by_id(session, project_id)
            if not updated_project:
                raise HTTPException(
                    status_code=404,
                    detail=f"项目ID {project_id} 不存在"
                )
            
            analysis_response = _convert_to_analysis_response(updated_project)
        
        return success_response(
            data=analysis_response,
            message="项目重新分析完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reprocess project", 
                    project_id=project_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"重新分析失败: {str(e)}"
        )


# 辅助函数

async def _execute_batch_processing(
    batch_size: int, 
    max_concurrent: int, 
    include_sentiment: bool
):
    """
    在后台执行批量处理
    """
    try:
        logger.info("Starting background batch AI processing",
                   batch_size=batch_size,
                   max_concurrent=max_concurrent)
        
        # 执行批量处理
        result = await ai_processing_manager.process_unprocessed_contents(
            batch_size=batch_size,
            max_concurrent=max_concurrent
        )
        
        logger.info("Background batch processing completed", 
                   total_processed=result.get('total_processed', 0),
                   successful=result.get('successful', 0),
                   failed=result.get('failed', 0))
        
    except Exception as e:
        logger.error("Background batch processing failed", error=str(e))


def _convert_to_analysis_response(project) -> AIAnalysisResponse:
    """
    将数据库项目转换为AI分析响应模型
    """
    from ..models.requests import ProjectCategory, RiskLevel, InvestmentRecommendation
    
    return AIAnalysisResponse(
        project_id=project.id,
        project_name=project.project_name,
        token_symbol=project.token_symbol,
        project_category=project.project_category or ProjectCategory.OTHER,
        tge_date=project.tge_date,
        risk_level=project.risk_level or RiskLevel.MEDIUM,
        investment_rating=project.investment_rating or 3,
        investment_recommendation=project.investment_recommendation or InvestmentRecommendation.CAUTION,
        potential_score=project.potential_score or 3,
        overall_score=project.overall_score or 3.0,
        sentiment_score=project.sentiment_score,
        sentiment_label=project.sentiment_label,
        analysis_confidence=project.analysis_confidence or 0.5,
        analysis_timestamp=project.updated_at or project.created_at
    )