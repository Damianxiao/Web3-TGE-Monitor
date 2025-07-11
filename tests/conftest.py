"""
测试配置文件
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Base
from src.database.database import get_db_session
from src.config.settings import settings

# 测试数据库URL（使用内存数据库）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

# 创建测试会话工厂
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    # 创建表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async with test_session_factory() as session:
        yield session
    
    # 清理表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_tge_project_data():
    """测试TGE项目数据"""
    return {
        "project_name": "Test Token",
        "content_hash": "test_hash_123",
        "raw_content": "Test TGE项目即将发布，代币发行总量1亿枚",
        "source_platform": "xhs",
        "source_url": "https://test.com/123",
        "source_user_id": "test_user_123",
        "source_username": "测试用户"
    }


@pytest.fixture
def test_ai_analysis_data():
    """测试AI分析数据"""
    return {
        "ai_summary": "Test Token项目即将进行TGE，总供应量1亿代币",
        "sentiment": "看涨",
        "recommendation": "关注",
        "risk_level": "中",
        "confidence_score": 0.85,
        "token_name": "Test Token",
        "token_symbol": "TEST",
        "tge_date": "2025年1月15日",
        "project_category": "DeFi"
    }