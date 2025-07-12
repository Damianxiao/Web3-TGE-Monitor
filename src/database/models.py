"""
数据库模型定义
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Float, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TGEProject(Base):
    """TGE项目数据模型"""
    __tablename__ = "tge_projects"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 项目基本信息
    project_name = Column(String(255), nullable=False, comment="项目名称")
    content_hash = Column(String(64), unique=True, nullable=False, comment="内容hash，用于去重")
    
    # 原始数据
    raw_content = Column(Text, nullable=False, comment="原始爬取内容")
    source_platform = Column(String(50), nullable=False, comment="来源平台")
    source_url = Column(Text, nullable=True, comment="来源URL")
    source_user_id = Column(String(100), nullable=True, comment="发布者ID")
    source_username = Column(String(255), nullable=True, comment="发布者用户名")
    
    # AI处理结果
    ai_summary = Column(Text, nullable=True, comment="AI生成的摘要")
    tge_summary = Column(Text, nullable=True, comment="TGE项目简介")
    key_features = Column(Text, nullable=True, comment="项目关键特性")
    sentiment = Column(String(20), nullable=True, comment="情感分析结果: 看涨/看跌/中性")
    recommendation = Column(String(50), nullable=True, comment="投资建议: 关注/谨慎/回避")
    risk_level = Column(String(20), nullable=True, comment="风险等级: 高/中/低")
    confidence_score = Column(Float, nullable=True, comment="置信度评分 0-1")
    
    # 关键信息提取
    token_name = Column(String(100), nullable=True, comment="代币名称")
    token_symbol = Column(String(20), nullable=True, comment="代币符号")
    tge_date = Column(String(50), nullable=True, comment="TGE时间")
    project_category = Column(String(50), nullable=True, comment="项目类别: DeFi/GameFi/NFT等")
    
    # 统计信息
    engagement_score = Column(Float, nullable=True, comment="用户参与度评分")
    keyword_matches = Column(Text, nullable=True, comment="匹配的关键词，JSON格式")
    
    # 状态字段
    is_processed = Column(Boolean, default=False, nullable=False, comment="是否已处理")
    is_valid = Column(Boolean, default=True, nullable=False, comment="是否有效数据")
    
    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    
    # 索引
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_project_name', 'project_name'),
        Index('idx_source_platform', 'source_platform'),
        Index('idx_sentiment', 'sentiment'),
        Index('idx_is_processed', 'is_processed'),
        Index('idx_tge_date', 'tge_date'),
    )
    
    def __repr__(self):
        return f"<TGEProject(id={self.id}, project_name='{self.project_name}', sentiment='{self.sentiment}')>"


class CrawlerLog(Base):
    """爬虫运行日志"""
    __tablename__ = "crawler_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, comment="爬取平台")
    keywords = Column(Text, nullable=True, comment="使用的关键词")
    pages_crawled = Column(Integer, default=0, comment="爬取页数")
    items_found = Column(Integer, default=0, comment="发现条目数")
    items_processed = Column(Integer, default=0, comment="处理条目数")
    items_saved = Column(Integer, default=0, comment="保存条目数")
    status = Column(String(20), nullable=False, comment="运行状态: success/failed/partial")
    error_message = Column(Text, nullable=True, comment="错误信息")
    execution_time = Column(Float, nullable=True, comment="执行时间(秒)")
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_platform', 'platform'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )


class AIProcessLog(Base):
    """AI处理日志"""
    __tablename__ = "ai_process_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tge_project_id = Column(Integer, nullable=True, comment="关联的TGE项目ID")
    input_text = Column(Text, nullable=False, comment="输入文本")
    output_summary = Column(Text, nullable=True, comment="输出摘要")
    model_used = Column(String(50), nullable=False, comment="使用的AI模型")
    tokens_used = Column(Integer, nullable=True, comment="使用的token数量")
    processing_time = Column(Float, nullable=True, comment="处理时间(秒)")
    status = Column(String(20), nullable=False, comment="处理状态")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_tge_project_id', 'tge_project_id'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )