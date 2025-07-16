"""
爬虫管理API路由
提供爬虫任务的创建、管理和监控功能
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks
import structlog
import asyncio

from ..models import (
    ApiResponse, PaginatedResponse,
    CrawlTaskRequest, CrawlTaskResponse, CrawlResultResponse,
    MultiPlatformCrawlRequest, MultiPlatformCrawlResponse, BatchCrawlStatusResponse,
    TaskStatus, PlatformType,
    success_response, error_response
)
from ...crawler import crawler_manager, Platform
from ...crawler.batch_manager import batch_crawl_manager
from ...crawler.data_service import crawl_data_service
from ...ai import ai_processing_manager

logger = structlog.get_logger()

# 创建API路由器
router = APIRouter()


@router.post("/tasks",
            response_model=ApiResponse[CrawlTaskResponse],
            summary="创建爬虫任务",
            description="创建新的爬虫任务，在后台异步执行")
async def create_crawl_task(
    task_request: CrawlTaskRequest,
    background_tasks: BackgroundTasks
):
    """
    创建爬虫任务
    
    支持的平台：
    - xhs: 小红书
    - douyin: 抖音
    - weibo: 微博
    - bilibili: B站
    
    任务会在后台异步执行，可通过任务ID查询进度。
    """
    try:
        logger.info("Creating crawl task", 
                   platform=task_request.platform,
                   keywords=task_request.keywords,
                   max_count=task_request.max_count)
        
        # 转换平台枚举
        platform_enum = Platform(task_request.platform.value)
        
        # 创建爬虫任务
        task_id = await crawler_manager.submit_crawl_task(
            platform=platform_enum,
            keywords=task_request.keywords,
            max_count=task_request.max_count
        )
        
        # 获取任务状态
        task = await crawler_manager.get_task_status(task_id)
        
        if not task:
            raise HTTPException(
                status_code=500,
                detail="任务创建失败"
            )
        
        # 添加后台任务：执行爬虫并自动触发AI分析
        background_tasks.add_task(
            _execute_crawl_and_ai_processing,
            task_id
        )
        
        # 转换为响应模型
        task_response = CrawlTaskResponse(
            task_id=task.task_id,
            platform=PlatformType(task.platform.value),
            status=TaskStatus(task.status),
            keywords=task.keywords,
            max_count=task.max_count,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            progress=0  # 刚创建时进度为0
        )
        
        return success_response(
            data=task_response,
            message=f"爬虫任务创建成功，任务ID: {task_id}"
        )
        
    except ValueError as e:
        logger.error("Invalid task parameters", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"任务参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to create crawl task", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="创建爬虫任务失败"
        )


@router.get("/tasks/{task_id}",
           response_model=ApiResponse[CrawlTaskResponse],
           summary="获取任务状态",
           description="获取指定爬虫任务的详细状态和进度")
async def get_task_status(
    task_id: str = Path(..., description="任务ID")
):
    """
    获取爬虫任务状态
    
    返回任务的实时状态，包括：
    - 任务进度
    - 执行状态
    - 错误信息（如果有）
    - 完成时间
    """
    try:
        logger.debug("Getting task status", task_id=task_id)
        
        # 获取任务状态
        task = await crawler_manager.get_task_status(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务ID {task_id} 不存在"
            )
        
        # 计算任务进度
        progress = _calculate_task_progress(task)
        
        # 转换为响应模型
        task_response = CrawlTaskResponse(
            task_id=task.task_id,
            platform=PlatformType(task.platform.value),
            status=TaskStatus(task.status),
            keywords=task.keywords,
            max_count=task.max_count,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            progress=progress,
            error_message=getattr(task, 'error_message', None)
        )
        
        return success_response(
            data=task_response,
            message="成功获取任务状态"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status", 
                    task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取任务状态失败"
        )


@router.get("/tasks",
           response_model=ApiResponse[List[CrawlTaskResponse]],
           summary="获取任务列表",
           description="获取所有爬虫任务的列表，支持状态过滤")
async def get_tasks(
    status: Optional[TaskStatus] = Query(None, description="按状态过滤"),
    platform: Optional[PlatformType] = Query(None, description="按平台过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制")
):
    """
    获取爬虫任务列表
    
    支持按以下条件过滤：
    - 任务状态（pending, running, completed, failed, cancelled）
    - 目标平台
    
    返回最近的任务，按创建时间降序排列。
    """
    try:
        logger.info("Getting tasks list", 
                   status=status, platform=platform, limit=limit)
        
        # 获取任务列表
        tasks = await crawler_manager.get_tasks(
            status=status.value if status else None,
            platform=Platform(platform.value) if platform else None,
            limit=limit
        )
        
        # 转换为响应模型列表
        task_responses = []
        for task in tasks:
            progress = _calculate_task_progress(task)
            
            task_response = CrawlTaskResponse(
                task_id=task.task_id,
                platform=PlatformType(task.platform.value),
                status=TaskStatus(task.status),
                keywords=task.keywords,
                max_count=task.max_count,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                progress=progress,
                error_message=getattr(task, 'error_message', None)
            )
            task_responses.append(task_response)
        
        return success_response(
            data=task_responses,
            message=f"成功获取{len(task_responses)}个任务"
        )
        
    except Exception as e:
        logger.error("Failed to get tasks list", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取任务列表失败"
        )


@router.get("/tasks/{task_id}/result",
           response_model=ApiResponse[CrawlResultResponse],
           summary="获取爬虫结果",
           description="获取已完成任务的爬虫结果统计")
async def get_crawl_result(
    task_id: str = Path(..., description="任务ID")
):
    """
    获取爬虫结果
    
    只有已完成的任务才能获取结果。
    返回爬虫的详细统计信息：
    - 总共爬取数量
    - 成功保存数量
    - 重复跳过数量
    - 错误数量
    - 执行时间
    """
    try:
        logger.info("Getting crawl result", task_id=task_id)
        
        # 获取任务状态
        task = await crawler_manager.get_task_status(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务ID {task_id} 不存在"
            )
        
        if task.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"任务尚未完成，当前状态: {task.status}"
            )
        
        # 获取爬虫结果
        result = await crawler_manager.get_task_result(task_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="爬虫结果不存在"
            )
        
        # 转换为响应模型
        result_response = CrawlResultResponse(
            task_id=result.task_id,
            platform=PlatformType(result.platform.value),
            total_count=result.total_count,
            success_count=result.success_count,
            duplicate_count=result.duplicate_count,
            error_count=result.error_count,
            execution_time=result.execution_time,
            keywords_used=result.keywords_used
        )
        
        return success_response(
            data=result_response,
            message="成功获取爬虫结果"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get crawl result", 
                    task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取爬虫结果失败"
        )


@router.delete("/tasks/{task_id}",
              response_model=ApiResponse[dict],
              summary="取消任务",
              description="取消正在执行或等待中的爬虫任务")
async def cancel_task(
    task_id: str = Path(..., description="任务ID")
):
    """
    取消爬虫任务
    
    只能取消正在执行或等待中的任务。
    已完成或已失败的任务不能取消。
    """
    try:
        logger.info("Cancelling task", task_id=task_id)
        
        # 获取任务状态
        task = await crawler_manager.get_task_status(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务ID {task_id} 不存在"
            )
        
        if task.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"任务已经{task.status}，不能取消"
            )
        
        # 取消任务
        success = await crawler_manager.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="取消任务失败"
            )
        
        return success_response(
            data={"task_id": task_id, "status": "cancelled"},
            message=f"任务 {task_id} 已成功取消"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel task", 
                    task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="取消任务失败"
        )


@router.post("/batch",
            response_model=ApiResponse[MultiPlatformCrawlResponse],
            summary="创建多平台批次爬虫任务",
            description="创建多平台爬虫任务，默认爬取所有可用平台并进行AI分析")
async def create_batch_crawl_task(
    task_request: MultiPlatformCrawlRequest,
    background_tasks: BackgroundTasks
):
    """
    创建多平台批次爬虫任务
    
    支持的平台：
    - xhs: 小红书
    - kuaishou: 快手
    - weibo: 微博
    - zhihu: 知乎
    - douyin: 抖音
    - bilibili: B站
    - tieba: 百度贴吧
    
    特性：
    - 默认爬取所有可用平台
    - 自动AI分析和总结
    - 并行执行提高效率
    """
    try:
        logger.info("Creating batch crawl task", 
                   platforms=task_request.platforms,
                   keywords=task_request.keywords,
                   max_count_per_platform=task_request.max_count_per_platform,
                   enable_ai_analysis=task_request.enable_ai_analysis)
        
        # 转换平台枚举
        platforms = None
        if task_request.platforms:
            platforms = [Platform(p.value) for p in task_request.platforms]
        
        # 创建批次爬虫任务
        batch_id = await batch_crawl_manager.create_batch_crawl(
            platforms=platforms,
            keywords=task_request.keywords,
            max_count_per_platform=task_request.max_count_per_platform,
            enable_ai_analysis=task_request.enable_ai_analysis
        )
        
        # 获取批次状态
        batch_status = await batch_crawl_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=500,
                detail="批次任务创建失败"
            )
        
        # 添加后台任务：执行批次爬虫
        background_tasks.add_task(
            _execute_batch_crawl,
            batch_id
        )
        
        # 转换为响应模型
        batch_response = MultiPlatformCrawlResponse(
            batch_id=batch_status['batch_id'],
            platforms=[PlatformType(p.value) for p in batch_status['platforms']],
            task_ids=batch_status['task_ids'],
            total_tasks=batch_status['total_tasks'],
            keywords=batch_status['keywords'] or [],
            max_count_per_platform=batch_status['max_count_per_platform'],
            enable_ai_analysis=batch_status['enable_ai_analysis'],
            created_at=batch_status['created_at'],
            overall_status=batch_status['overall_status']
        )
        
        return success_response(
            data=batch_response,
            message=f"批次爬虫任务创建成功，批次ID: {batch_id}"
        )
        
    except ValueError as e:
        logger.error("Invalid batch task parameters", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"任务参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to create batch crawl task", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="创建批次爬虫任务失败"
        )


@router.get("/batch/{batch_id}",
           response_model=ApiResponse[BatchCrawlStatusResponse],
           summary="获取批次任务状态",
           description="获取多平台批次爬虫任务的详细状态和进度")
async def get_batch_status(
    batch_id: str = Path(..., description="批次ID")
):
    """
    获取批次爬虫任务状态
    
    返回批次的实时状态，包括：
    - 各平台任务进度
    - 整体执行状态
    - AI分析状态
    - 内容统计信息
    """
    try:
        logger.debug("Getting batch status", batch_id=batch_id)
        
        # 获取批次状态
        batch_status = await batch_crawl_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=404,
                detail=f"批次ID {batch_id} 不存在"
            )
        
        # 转换为响应模型
        status_response = BatchCrawlStatusResponse(
            batch_id=batch_status['batch_id'],
            overall_status=batch_status['overall_status'],
            total_tasks=batch_status['total_tasks'],
            completed_tasks=batch_status['completed_tasks'],
            failed_tasks=batch_status['failed_tasks'],
            overall_progress=batch_status['overall_progress'],
            platform_status=batch_status['platform_status'],
            ai_analysis_status=batch_status.get('ai_analysis_status'),
            total_content_found=batch_status['total_content_found'],
            ai_summary=batch_status.get('ai_summary')
        )
        
        return success_response(
            data=status_response,
            message="成功获取批次任务状态"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get batch status", 
                    batch_id=batch_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取批次任务状态失败"
        )


@router.get("/batch",
           response_model=ApiResponse[List[BatchCrawlStatusResponse]],
           summary="获取批次任务列表",
           description="获取所有批次爬虫任务的列表")
async def get_batch_list(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制")
):
    """
    获取批次爬虫任务列表
    
    返回最近的批次任务，按创建时间降序排列。
    """
    try:
        logger.info("Getting batch list", limit=limit)
        
        # 获取批次列表
        batches = await batch_crawl_manager.list_batches(limit=limit)
        
        # 转换为响应模型列表
        batch_responses = []
        for batch in batches:
            # 计算整体进度
            batch_status = await batch_crawl_manager.get_batch_status(batch['batch_id'])
            
            batch_response = BatchCrawlStatusResponse(
                batch_id=batch['batch_id'],
                overall_status=batch['overall_status'],
                total_tasks=batch['total_tasks'],
                completed_tasks=batch['completed_tasks'],
                failed_tasks=batch['failed_tasks'],
                overall_progress=batch_status['overall_progress'] if batch_status else 0,
                platform_status=batch['platform_status'],
                ai_analysis_status=batch.get('ai_analysis_status'),
                total_content_found=batch['total_content_found'],
                ai_summary=batch.get('ai_summary')
            )
            batch_responses.append(batch_response)
        
        return success_response(
            data=batch_responses,
            message=f"成功获取{len(batch_responses)}个批次任务"
        )
        
    except Exception as e:
        logger.error("Failed to get batch list", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取批次任务列表失败"
        )


# 辅助函数

async def _execute_batch_crawl(batch_id: str):
    """
    在后台执行批次爬虫任务
    """
    try:
        logger.info("Starting background batch crawl", batch_id=batch_id)
        
        # 执行批次爬虫任务
        result = await batch_crawl_manager.execute_batch(batch_id)
        
        logger.info("Background batch crawl completed", 
                   batch_id=batch_id,
                   overall_status=result['overall_status'],
                   total_content=result['total_content_found'])
        
    except Exception as e:
        logger.error("Background batch crawl failed", 
                    batch_id=batch_id, error=str(e))


async def _execute_crawl_and_ai_processing(task_id: str):
    """
    在后台执行爬虫任务并自动触发AI分析
    """
    try:
        logger.info("Starting background crawl and AI processing", task_id=task_id)
        
        # 执行爬虫任务
        result = await crawler_manager.execute_task(task_id)
        
        if result and result.success_count > 0:
            logger.info("Crawl completed, starting AI processing", 
                       task_id=task_id,
                       success_count=result.success_count)
            
            # 等待一下让数据库操作完成
            await asyncio.sleep(2)
            
            # 自动触发AI分析
            await ai_processing_manager.process_unprocessed_contents(
                batch_size=min(result.success_count, 10),
                max_concurrent=2
            )
            
            logger.info("Background processing completed", task_id=task_id)
        else:
            logger.warning("Crawl completed but no data to process", 
                          task_id=task_id)
            
    except Exception as e:
        logger.error("Background processing failed", 
                    task_id=task_id, error=str(e))


def _calculate_task_progress(task) -> int:
    """
    计算任务进度百分比
    """
    if task.status == "pending":
        return 0
    elif task.status == "running":
        # 简单的进度估算，实际应该根据具体爬虫进度计算
        return 50
    elif task.status in ["completed", "failed", "cancelled"]:
        return 100
    else:
        return 0