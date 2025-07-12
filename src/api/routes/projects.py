"""
项目数据查询API路由
提供TGE项目的查询、搜索和统计功能
"""
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import structlog

from ..models import (
    ApiResponse, PaginatedResponse, ErrorResponse,
    ProjectSearchRequest, ProjectSummaryResponse, ProjectDetailResponse,
    PaginationParams, ProjectCategory, RiskLevel, PlatformType,
    success_response, error_response, paginated_response
)
from ...database.database import get_db_session
from ...database.crud import TGEProjectCRUD

logger = structlog.get_logger()

# 创建API路由器
router = APIRouter()


@router.get("/",
           response_model=ApiResponse[PaginatedResponse[ProjectSummaryResponse]],
           summary="获取项目列表",
           description="分页获取TGE项目列表，支持多种过滤和排序选项")
async def get_projects(
    # 分页参数
    page: int = Query(1, ge=1, description="页码，从1开始"),
    size: int = Query(20, ge=1, le=100, description="每页数量，最大1，最大100"),
    
    # 过滤参数
    category: Optional[ProjectCategory] = Query(None, description="项目分类过滤"),
    risk_level: Optional[RiskLevel] = Query(None, description="风险等级过滤"),
    platform: Optional[PlatformType] = Query(None, description="来源平台过滤"),
    has_tge_date: Optional[bool] = Query(None, description="是否有TGE日期"),
    is_processed: Optional[bool] = Query(None, description="是否已AI分析"),
    
    # 排序参数
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向（asc/desc）")
):
    """
    获取TGE项目列表
    
    支持的排序字段：
    - created_at: 创建时间
    - project_name: 项目名称
    - investment_rating: 投资评级
    - overall_score: 综合评分
    - engagement_score: 参与度评分
    - tge_date: TGE日期
    """
    try:
        logger.info("Getting projects list", 
                   page=page, size=size, 
                   category=category, risk_level=risk_level,
                   platform=platform, sort_by=sort_by)
        
        async with get_db_session() as session:
            # 构建查询条件
            filters = {}
            if category:
                filters['project_category'] = category.value
            if risk_level:
                filters['risk_level'] = risk_level.value
            if platform:
                filters['source_platform'] = platform.value
            if has_tge_date is not None:
                filters['has_tge_date'] = has_tge_date
            if is_processed is not None:
                filters['is_processed'] = is_processed
            
            # 获取项目列表
            projects, total = await TGEProjectCRUD.get_paginated(
                session=session,
                page=page,
                size=size,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # 转换为响应模型
            project_responses = [
                ProjectSummaryResponse(
                    id=project.id,
                    project_name=project.project_name,
                    token_symbol=project.token_symbol,
                    project_category=project.project_category or ProjectCategory.OTHER,
                    risk_level=project.risk_level,
                    source_platform=project.source_platform,
                    investment_rating=project.investment_rating,
                    investment_recommendation=project.investment_recommendation,
                    overall_score=project.overall_score,
                    engagement_score=project.engagement_score,
                    created_at=project.created_at,
                    tge_date=project.tge_date,
                    is_processed=project.is_processed
                )
                for project in projects
            ]
            
            # 创建分页响应
            paginated_data = paginated_response(
                items=project_responses,
                total=total,
                page=page,
                size=size
            )
            
            return success_response(
                data=paginated_data,
                message=f"成功获取{len(project_responses)}个项目"
            )
            
    except Exception as e:
        logger.error("Failed to get projects list", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取项目列表失败"
        )


@router.get("/{project_id}",
           response_model=ApiResponse[ProjectDetailResponse],
           summary="获取项目详情",
           description="获取指定TGE项目的详细信息，包括AI分析结果")
async def get_project_detail(
    project_id: int = Path(..., ge=1, description="项目ID")
):
    """
    获取项目详细信息
    
    返回项目的完整信息，包括：
    - 基本信息（名称、分类、来源等）
    - 内容信息（原始内容、简介等）
    - AI分析结果（投资建议、情感分析等）
    - 统计信息（参与度、关键词匹配等）
    """
    try:
        logger.info("Getting project detail", project_id=project_id)
        
        async with get_db_session() as session:
            project = await TGEProjectCRUD.get_by_id(session, project_id)
            
            if not project:
                raise HTTPException(
                    status_code=404,
                    detail=f"项目ID {project_id} 不存在"
                )
            
            # 转换为详细响应模型
            project_detail = ProjectDetailResponse(
                # 基本信息
                id=project.id,
                project_name=project.project_name,
                token_symbol=project.token_symbol,
                project_category=project.project_category or ProjectCategory.OTHER,
                risk_level=project.risk_level,
                tge_date=project.tge_date,
                
                # 来源信息
                source_platform=project.source_platform,
                source_url=project.source_url,
                source_username=project.source_username,
                
                # 内容信息
                raw_content=project.raw_content,
                tge_summary=project.tge_summary,
                key_features=project.key_features.split(',') if project.key_features else None,
                
                # AI分析结果
                investment_rating=project.investment_rating,
                investment_recommendation=project.investment_recommendation,
                investment_reason=project.investment_reason,
                key_advantages=project.key_advantages.split(',') if project.key_advantages else None,
                key_risks=project.key_risks.split(',') if project.key_risks else None,
                potential_score=project.potential_score,
                overall_score=project.overall_score,
                
                # 情感分析
                sentiment_score=project.sentiment_score,
                sentiment_label=project.sentiment_label,
                market_sentiment=project.market_sentiment,
                
                # 统计信息
                engagement_score=project.engagement_score,
                keyword_matches=project.keyword_matches,
                
                # 元数据
                content_hash=project.content_hash,
                is_processed=project.is_processed,
                analysis_confidence=project.analysis_confidence,
                created_at=project.created_at,
                updated_at=project.updated_at
            )
            
            return success_response(
                data=project_detail,
                message="成功获取项目详情"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project detail", 
                    project_id=project_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取项目详情失败"
        )


@router.get("/search",
           response_model=ApiResponse[PaginatedResponse[ProjectSummaryResponse]],
           summary="搜索项目",
           description="根据关键词搜索TGE项目，支持在项目名称和内容中搜索")
async def search_projects(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    
    # 分页参数
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    
    # 过滤参数
    category: Optional[ProjectCategory] = Query(None, description="项目分类过滤"),
    risk_level: Optional[RiskLevel] = Query(None, description="风险等级过滤"),
    platform: Optional[PlatformType] = Query(None, description="来源平台过滤")
):
    """
    搜索TGE项目
    
    搜索范围包括：
    - 项目名称
    - 代币符号
    - 原始内容
    - TGE简介
    - 关键特性
    """
    try:
        logger.info("Searching projects", 
                   query=query, page=page, size=size,
                   category=category, platform=platform)
        
        async with get_db_session() as session:
            # 构建过滤条件
            filters = {}
            if category:
                filters['project_category'] = category.value
            if risk_level:
                filters['risk_level'] = risk_level.value
            if platform:
                filters['source_platform'] = platform.value
            
            # 执行搜索
            projects, total = await TGEProjectCRUD.search(
                session=session,
                query=query,
                page=page,
                size=size,
                filters=filters
            )
            
            # 转换为响应模型
            project_responses = [
                ProjectSummaryResponse(
                    id=project.id,
                    project_name=project.project_name,
                    token_symbol=project.token_symbol,
                    project_category=project.project_category or ProjectCategory.OTHER,
                    risk_level=project.risk_level,
                    source_platform=project.source_platform,
                    investment_rating=project.investment_rating,
                    investment_recommendation=project.investment_recommendation,
                    overall_score=project.overall_score,
                    engagement_score=project.engagement_score,
                    created_at=project.created_at,
                    tge_date=project.tge_date,
                    is_processed=project.is_processed
                )
                for project in projects
            ]
            
            # 创建分页响应
            paginated_data = paginated_response(
                items=project_responses,
                total=total,
                page=page,
                size=size
            )
            
            return success_response(
                data=paginated_data,
                message=f"搜索到{total}个相关项目"
            )
            
    except Exception as e:
        logger.error("Failed to search projects", 
                    query=query, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="搜索项目失败"
        )


@router.get("/categories",
           response_model=ApiResponse[Dict[str, int]],
           summary="获取项目分类统计",
           description="获取各个项目分类的数量统计")
async def get_project_categories():
    """
    获取项目分类统计
    
    返回各个分类下的项目数量，便于前端显示统计信息
    """
    try:
        logger.info("Getting project categories statistics")
        
        async with get_db_session() as session:
            category_stats = await TGEProjectCRUD.get_category_stats(session)
            
            return success_response(
                data=category_stats,
                message="成功获取分类统计"
            )
            
    except Exception as e:
        logger.error("Failed to get category statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="获取分类统计失败"
        )