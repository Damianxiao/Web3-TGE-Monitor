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


@router.post("/batch/sync",
            response_model=ApiResponse[BatchCrawlStatusResponse],
            summary="同步批次爬虫任务",
            description="创建多平台批次爬虫任务并同步等待完成，返回最终聚合结果")
async def create_batch_crawl_sync(
    task_request: MultiPlatformCrawlRequest
):
    """
    同步批次爬虫任务
    
    与 /batch 端点不同，此端点会：
    1. 创建批次任务
    2. 同步等待任务完成
    3. 返回最终聚合结果
    
    适用于需要立即获取结果的场景，无需轮询状态。
    注意：此端点响应时间较长，建议设置较高的超时时间。
    """
    try:
        logger.info("Creating synchronous batch crawl task", 
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
        
        logger.info("Batch created, executing synchronously", batch_id=batch_id)
        
        # 同步执行批次爬虫任务
        execution_result = await batch_crawl_manager.execute_batch(batch_id)
        
        if not execution_result:
            raise HTTPException(
                status_code=500,
                detail="批次任务执行失败"
            )
        
        # 获取最终状态
        final_status = await batch_crawl_manager.get_batch_status(batch_id)
        
        if not final_status:
            raise HTTPException(
                status_code=500,
                detail="无法获取批次任务最终状态"
            )
        
        # 转换为响应模型
        batch_response = BatchCrawlStatusResponse(
            batch_id=final_status['batch_id'],
            overall_status=final_status['overall_status'],
            total_tasks=final_status['total_tasks'],
            completed_tasks=final_status['completed_tasks'],
            failed_tasks=final_status['failed_tasks'],
            overall_progress=final_status['overall_progress'],
            platform_status=final_status['platform_status'],
            ai_analysis_status=final_status.get('ai_analysis_status'),
            total_content_found=final_status['total_content_found'],
            ai_summary=final_status.get('ai_summary')
        )
        
        logger.info("Synchronous batch crawl completed", 
                   batch_id=batch_id,
                   overall_status=final_status['overall_status'],
                   total_content=final_status['total_content_found'])
        
        return success_response(
            data=batch_response,
            message=f"同步批次爬虫任务完成，批次ID: {batch_id}"
        )
        
    except ValueError as e:
        logger.error("Invalid sync batch task parameters", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"任务参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to create sync batch crawl task", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="创建同步批次爬虫任务失败"
        )


@router.get("/batch/{batch_id}/results",
           response_model=ApiResponse[dict],
           summary="获取批次聚合结果",
           description="获取批次任务的详细聚合结果，包括各平台数据和AI分析汇总")
async def get_batch_results(
    batch_id: str = Path(..., description="批次ID"),
    include_raw_data: bool = Query(False, description="是否包含原始数据"),
    limit_per_platform: int = Query(50, ge=1, le=200, description="每个平台返回的结果数量限制")
):
    """
    获取批次聚合结果
    
    提供批次任务的完整聚合视图，包括：
    - 批次总体状态
    - 各平台详细结果
    - AI分析汇总
    - 关键项目推荐
    - 统计数据
    
    参数说明：
    - include_raw_data: 是否包含原始爬虫数据，默认false以减少响应大小
    - limit_per_platform: 每个平台返回的结果数量限制
    """
    try:
        logger.info("Getting batch results", 
                   batch_id=batch_id,
                   include_raw_data=include_raw_data,
                   limit_per_platform=limit_per_platform)
        
        # 获取批次状态
        batch_status = await batch_crawl_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=404,
                detail=f"批次ID {batch_id} 不存在"
            )
        
        # 获取批次任务详细结果
        batch_results = {}
        platform_results = {}
        
        # 遍历各平台任务获取结果
        for platform, task_id in batch_status.get('task_ids', {}).items():
            try:
                # 获取单个任务的结果
                task_result = await crawler_manager.get_task_result(task_id)
                
                if task_result:
                    platform_results[platform] = {
                        "task_id": task_id,
                        "platform": platform,
                        "total_count": task_result.total_count,
                        "success_count": task_result.success_count,
                        "duplicate_count": task_result.duplicate_count,
                        "error_count": task_result.error_count,
                        "execution_time": task_result.execution_time,
                        "keywords_used": task_result.keywords_used
                    }
                    
                    # 如果需要原始数据，获取项目数据
                    if include_raw_data:
                        # 获取该平台的项目数据
                        platform_projects = await crawl_data_service.get_batch_platform_projects(
                            batch_id, platform, limit_per_platform
                        )
                        platform_results[platform]["projects"] = platform_projects
                        
            except Exception as e:
                logger.warning(f"Failed to get results for platform {platform}", 
                             task_id=task_id, error=str(e))
                platform_results[platform] = {
                    "task_id": task_id,
                    "platform": platform,
                    "error": str(e)
                }
        
        # 聚合统计数据
        total_stats = {
            "total_count": sum(r.get("total_count", 0) for r in platform_results.values() if "total_count" in r),
            "success_count": sum(r.get("success_count", 0) for r in platform_results.values() if "success_count" in r),
            "duplicate_count": sum(r.get("duplicate_count", 0) for r in platform_results.values() if "duplicate_count" in r),
            "error_count": sum(r.get("error_count", 0) for r in platform_results.values() if "error_count" in r),
            "platforms_count": len(platform_results),
            "successful_platforms": len([r for r in platform_results.values() if r.get("success_count", 0) > 0])
        }
        
        # 构建响应数据
        results_data = {
            "batch_id": batch_id,
            "batch_status": batch_status,
            "platform_results": platform_results,
            "aggregated_stats": total_stats,
            "include_raw_data": include_raw_data,
            "limit_per_platform": limit_per_platform
        }
        
        # 如果启用了AI分析，获取AI分析汇总
        if batch_status.get('enable_ai_analysis', False):
            try:
                ai_summary = await _get_batch_ai_summary(batch_id)
                results_data["ai_analysis_summary"] = ai_summary
            except Exception as e:
                logger.warning("Failed to get AI analysis summary", 
                             batch_id=batch_id, error=str(e))
                results_data["ai_analysis_summary"] = {"error": str(e)}
        
        return success_response(
            data=results_data,
            message=f"成功获取批次 {batch_id} 的聚合结果"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get batch results", 
                    batch_id=batch_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取批次结果失败"
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


async def _get_batch_ai_summary(batch_id: str) -> dict:
    """
    获取批次AI分析汇总
    """
    try:
        # 获取批次相关的AI分析数据
        session = await get_db_session()
        async with session:
            from ...database.crud import TGEProjectCRUD
            
            # 获取批次相关的项目数据
            batch_projects = await TGEProjectCRUD.get_batch_projects(session, batch_id)
            
            if not batch_projects:
                return {"message": "没有找到相关项目数据"}
            
            # 统计AI分析结果
            processed_projects = [p for p in batch_projects if p.is_processed]
            
            if not processed_projects:
                return {"message": "没有已处理的项目数据"}
            
            # 汇总统计
            summary = {
                "total_projects": len(batch_projects),
                "processed_projects": len(processed_projects),
                "processing_rate": len(processed_projects) / len(batch_projects) * 100,
                "investment_recommendations": {},
                "risk_levels": {},
                "categories": {},
                "sentiment_analysis": {
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0
                },
                "top_projects": [],
                "average_scores": {
                    "potential_score": 0,
                    "overall_score": 0,
                    "engagement_score": 0
                }
            }
            
            # 统计投资建议
            for project in processed_projects:
                if project.investment_recommendation:
                    recommendation = project.investment_recommendation
                    summary["investment_recommendations"][recommendation] = \
                        summary["investment_recommendations"].get(recommendation, 0) + 1
                
                # 统计风险等级
                if project.risk_level:
                    risk_level = project.risk_level
                    summary["risk_levels"][risk_level] = \
                        summary["risk_levels"].get(risk_level, 0) + 1
                
                # 统计项目分类
                if project.project_category:
                    category = project.project_category
                    summary["categories"][category] = \
                        summary["categories"].get(category, 0) + 1
                
                # 统计情感分析
                if project.sentiment_label:
                    sentiment = project.sentiment_label.lower()
                    if sentiment in ["positive", "bullish", "看涨"]:
                        summary["sentiment_analysis"]["positive"] += 1
                    elif sentiment in ["negative", "bearish", "看跌"]:
                        summary["sentiment_analysis"]["negative"] += 1
                    else:
                        summary["sentiment_analysis"]["neutral"] += 1
            
            # 计算平均分数
            if processed_projects:
                summary["average_scores"]["potential_score"] = \
                    sum(p.potential_score or 0 for p in processed_projects) / len(processed_projects)
                summary["average_scores"]["overall_score"] = \
                    sum(p.overall_score or 0 for p in processed_projects) / len(processed_projects)
                summary["average_scores"]["engagement_score"] = \
                    sum(p.engagement_score or 0 for p in processed_projects) / len(processed_projects)
            
            # 获取高分项目
            top_projects = sorted(
                processed_projects,
                key=lambda p: p.overall_score or 0,
                reverse=True
            )[:5]
            
            summary["top_projects"] = [
                {
                    "id": p.id,
                    "project_name": p.project_name,
                    "token_symbol": p.token_symbol,
                    "overall_score": p.overall_score,
                    "investment_recommendation": p.investment_recommendation,
                    "risk_level": p.risk_level
                }
                for p in top_projects
            ]
            
            return summary
            
    except Exception as e:
        logger.error("Failed to get batch AI summary", 
                    batch_id=batch_id, error=str(e))
        return {"error": str(e)}