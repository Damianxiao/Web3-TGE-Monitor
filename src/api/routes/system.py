"""
系统管理API路由
提供系统状态、统计和配置管理功能
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
import structlog
import psutil
import sys

from ..models import (
    ApiResponse, HealthCheckResponse, SystemStatsResponse,
    success_response, error_response
)
from ...database.database import get_db_session
from ...database.crud import TGEProjectCRUD, CrawlerLogCRUD
from ...config.settings import settings

logger = structlog.get_logger()

# 创建API路由器
router = APIRouter()

# 系统启动时间
START_TIME = time.time()


@router.get("/health",
           response_model=ApiResponse[HealthCheckResponse],
           summary="系统健康检查",
           description="检查系统各组件的健康状态")
async def health_check():
    """
    系统健康检查
    
    检查项目：
    - API服务状态
    - 数据库连接
    - AI服务连接
    - 系统资源使用情况
    """
    try:
        logger.debug("Performing health check")
        
        health_status = {
            "api": "healthy",
            "database": "unknown",
            "ai_service": "unknown",
            "memory": "unknown",
            "disk": "unknown"
        }
        
        overall_status = "healthy"
        
        # 检查数据库连接
        try:
            async with get_db_session() as session:
                # 简单的数据库查询测试
                await TGEProjectCRUD.count_all(session)
                health_status["database"] = "healthy"
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            health_status["database"] = "unhealthy"
            overall_status = "degraded"
        
        # 检查AI服务
        try:
            from ...ai import ai_client
            # 这里可以添加一个轻量AI服务检查
            if ai_client and hasattr(ai_client, 'api_url'):
                health_status["ai_service"] = "healthy"
            else:
                health_status["ai_service"] = "not_configured"
        except Exception as e:
            logger.error("AI service health check failed", error=str(e))
            health_status["ai_service"] = "unhealthy"
            overall_status = "degraded"
        
        # 检查系统资源
        try:
            # 内存使用率
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                health_status["memory"] = "critical"
                overall_status = "degraded"
            elif memory_percent > 80:
                health_status["memory"] = "warning"
            else:
                health_status["memory"] = "healthy"
            
            # 磁盘使用率
            disk_percent = psutil.disk_usage('/').percent
            if disk_percent > 90:
                health_status["disk"] = "critical"
                overall_status = "degraded"
            elif disk_percent > 80:
                health_status["disk"] = "warning"
            else:
                health_status["disk"] = "healthy"
                
        except Exception as e:
            logger.warning("System resource check failed", error=str(e))
            health_status["memory"] = "unknown"
            health_status["disk"] = "unknown"
        
        # 计算运行时间
        uptime = time.time() - START_TIME
        
        health_response = HealthCheckResponse(
            status=overall_status,
            timestamp=time.time(),
            services=health_status,
            version="1.0.0",
            uptime=uptime
        )
        
        return success_response(
            data=health_response,
            message=f"系统状态: {overall_status}"
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return error_response(
            message="健康检查失败",
            status_code=503
        )


@router.get("/stats",
           response_model=ApiResponse[SystemStatsResponse],
           summary="系统统计信息",
           description="获取系统的综合统计信息")
async def get_system_stats():
    """
    获取系统统计信息
    
    包括：
    - 项目数量统计
    - 平台分布统计
    - 分类分布统计
    - 时间统计
    - 系统信息
    """
    try:
        logger.info("Getting system statistics")
        
        async with get_db_session() as session:
            # 项目数量统计
            total_projects = await TGEProjectCRUD.count_all(session)
            processed_projects = await TGEProjectCRUD.count_processed(session)
            unprocessed_projects = total_projects - processed_projects
            
            # 平台统计
            platform_stats = await TGEProjectCRUD.get_platform_stats(session)
            
            # 分类统计
            category_stats = await TGEProjectCRUD.get_category_stats(session)
            
            # 时间统计
            now = datetime.utcnow()
            recent_24h = await TGEProjectCRUD.count_recent(
                session, 
                since=now - timedelta(hours=24)
            )
            recent_7d = await TGEProjectCRUD.count_recent(
                session, 
                since=now - timedelta(days=7)
            )
        
        # 计算运行时间
        uptime = time.time() - START_TIME
        
        stats_response = SystemStatsResponse(
            total_projects=total_projects,
            processed_projects=processed_projects,
            unprocessed_projects=unprocessed_projects,
            platform_stats=platform_stats,
            category_stats=category_stats,
            recent_24h=recent_24h,
            recent_7d=recent_7d,
            api_version="1.0.0",
            uptime=uptime,
            last_updated=datetime.utcnow()
        )
        
        return success_response(
            data=stats_response,
            message="成功获取系统统计"
        )
        
    except Exception as e:
        logger.error("Failed to get system statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取系统统计失败"
        )


@router.get("/config",
           response_model=ApiResponse[Dict[str, Any]],
           summary="获取系统配置",
           description="获取当前系统的配置信息（隐藏敏感信息）")
async def get_system_config():
    """
    获取系统配置信息
    
    返回非敏感的配置信息，用于调试和监控。
    敏感信息（如密码、API Key）会被隐藏。
    """
    try:
        logger.debug("Getting system configuration")
        
        # 构建配置信息（隐藏敏感数据）
        config_info = {
            # 应用配置
            "app": {
                "host": settings.app_host,
                "port": settings.app_port,
                "debug": settings.app_debug,
                "log_level": settings.log_level
            },
            
            # 数据库配置（隐藏密码）
            "database": {
                "host": settings.mysql_host,
                "port": settings.mysql_port,
                "user": settings.mysql_user,
                "database": settings.mysql_db,
                "password": "***"
            },
            
            # AI配置（隐藏API Key）
            "ai": {
                "api_base_url": settings.ai_api_base_url,
                "model": settings.ai_model,
                "max_tokens": settings.ai_max_tokens,
                "temperature": settings.ai_temperature,
                "api_key": "***" if settings.ai_api_key else None
            },
            
            # 爬虫配置
            "crawler": {
                "mediacrawler_path": settings.mediacrawler_path,
                "max_pages": settings.crawler_max_pages,
                "delay_seconds": settings.crawler_delay_seconds,
                "data_retention_days": settings.data_retention_days
            },
            
            # Web3关键词
            "keywords": {
                "web3_keywords": settings.web3_keywords[:5] if settings.web3_keywords else [],  # 只显示前5个
                "total_count": len(settings.web3_keywords) if settings.web3_keywords else 0
            },
            
            # 系统信息
            "system": {
                "python_version": sys.version,
                "platform": sys.platform,
                "api_version": "1.0.0",
                "uptime": time.time() - START_TIME
            }
        }
        
        return success_response(
            data=config_info,
            message="成功获取系统配置"
        )
        
    except Exception as e:
        logger.error("Failed to get system config", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取系统配置失败"
        )


@router.get("/logs",
           response_model=ApiResponse[List[Dict[str, Any]]],
           summary="获取系统日志",
           description="获取爬虫执行日志和AI处理日志")
async def get_system_logs(
    log_type: Optional[str] = Query(None, description="日志类型（crawler/ai）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）")
):
    """
    获取系统日志
    
    支持的日志类型：
    - crawler: 爬虫执行日志
    - ai: AI处理日志
    - 不指定: 返回所有类型
    """
    try:
        logger.info("Getting system logs", 
                   log_type=log_type, limit=limit, hours=hours)
        
        # 计算时间范围
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        logs = []
        
        async with get_db_session() as session:
            # 获取爬虫日志
            if log_type is None or log_type == "crawler":
                crawler_logs = await CrawlerLogCRUD.get_recent_logs(
                    session, 
                    since=since_time, 
                    limit=limit // 2 if log_type is None else limit
                )
                
                for log in crawler_logs:
                    logs.append({
                        "type": "crawler",
                        "id": log.id,
                        "platform": log.platform,
                        "keywords": log.keywords,
                        "items_found": log.items_found,
                        "items_saved": log.items_saved,
                        "status": log.status,
                        "error_message": log.error_message,
                        "execution_time": log.execution_time,
                        "created_at": log.created_at
                    })
            
            # 获取AI处理日志
            if log_type is None or log_type == "ai":
                # 这里可以添加AI日志查询
                # ai_logs = await AIProcessLogCRUD.get_recent_logs(...)
                pass
        
        # 按时间排序
        logs.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        # 限制返回数量
        logs = logs[:limit]
        
        return success_response(
            data=logs,
            message=f"成功获取{len(logs)}条日志记录"
        )
        
    except Exception as e:
        logger.error("Failed to get system logs", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取系统日志失败"
        )


@router.get("/metrics",
           response_model=ApiResponse[Dict[str, Any]],
           summary="获取系统指标",
           description="获取系统运行指标和性能数据")
async def get_system_metrics():
    """
    获取系统运行指标
    
    包括：
    - CPU使用率
    - 内存使用率
    - 磁盘使用率
    - 网络连接数
    - 进程信息
    """
    try:
        logger.debug("Getting system metrics")
        
        # 获取系统指标
        metrics = {
            # CPU信息
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            },
            
            # 内存信息
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "usage_percent": psutil.virtual_memory().percent
            },
            
            # 磁盘信息
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "usage_percent": psutil.disk_usage('/').percent
            },
            
            # 网络信息
            "network": {
                "connections": len(psutil.net_connections()),
                "io_counters": dict(psutil.net_io_counters()._asdict())
            },
            
            # 进程信息
            "process": {
                "pid": psutil.Process().pid,
                "memory_info": dict(psutil.Process().memory_info()._asdict()),
                "cpu_percent": psutil.Process().cpu_percent(),
                "create_time": psutil.Process().create_time(),
                "num_threads": psutil.Process().num_threads()
            },
            
            # 时间信息
            "uptime": time.time() - START_TIME,
            "timestamp": time.time()
        }
        
        return success_response(
            data=metrics,
            message="成功获取系统指标"
        )
        
    except Exception as e:
        logger.error("Failed to get system metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取系统指标失败"
        )