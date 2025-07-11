"""
数据库CRUD操作测试
"""
import pytest
from src.database.crud import TGEProjectCRUD, CrawlerLogCRUD, AIProcessLogCRUD


class TestTGEProjectCRUD:
    """TGE项目CRUD测试"""
    
    @pytest.mark.asyncio
    async def test_create_tge_project(self, test_db, test_tge_project_data):
        """测试创建TGE项目"""
        project = await TGEProjectCRUD.create(test_db, test_tge_project_data)
        
        assert project is not None
        assert project.project_name == test_tge_project_data["project_name"]
        assert project.content_hash == test_tge_project_data["content_hash"]
        assert project.is_processed is False
        assert project.is_valid is True
    
    @pytest.mark.asyncio
    async def test_create_duplicate_content_hash(self, test_db, test_tge_project_data):
        """测试重复content_hash的处理"""
        # 创建第一个项目
        project1 = await TGEProjectCRUD.create(test_db, test_tge_project_data)
        assert project1 is not None
        
        # 尝试创建相同content_hash的项目
        project2 = await TGEProjectCRUD.create(test_db, test_tge_project_data)
        assert project2 is None  # 应该返回None，表示重复
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, test_db, test_tge_project_data):
        """测试根据ID获取项目"""
        created_project = await TGEProjectCRUD.create(test_db, test_tge_project_data)
        
        retrieved_project = await TGEProjectCRUD.get_by_id(test_db, created_project.id)
        
        assert retrieved_project is not None
        assert retrieved_project.id == created_project.id
        assert retrieved_project.project_name == created_project.project_name
    
    @pytest.mark.asyncio
    async def test_get_by_content_hash(self, test_db, test_tge_project_data):
        """测试根据content_hash获取项目"""
        created_project = await TGEProjectCRUD.create(test_db, test_tge_project_data)
        
        retrieved_project = await TGEProjectCRUD.get_by_content_hash(
            test_db, test_tge_project_data["content_hash"]
        )
        
        assert retrieved_project is not None
        assert retrieved_project.content_hash == test_tge_project_data["content_hash"]
    
    @pytest.mark.asyncio
    async def test_update_ai_analysis(self, test_db, test_tge_project_data, test_ai_analysis_data):
        """测试更新AI分析结果"""
        # 创建项目
        project = await TGEProjectCRUD.create(test_db, test_tge_project_data)
        
        # 更新AI分析结果
        success = await TGEProjectCRUD.update_ai_analysis(
            test_db, project.id, test_ai_analysis_data
        )
        
        assert success is True
        
        # 验证更新结果
        updated_project = await TGEProjectCRUD.get_by_id(test_db, project.id)
        assert updated_project.ai_summary == test_ai_analysis_data["ai_summary"]
        assert updated_project.sentiment == test_ai_analysis_data["sentiment"]
        assert updated_project.is_processed is True
    
    @pytest.mark.asyncio
    async def test_get_latest(self, test_db):
        """测试获取最新项目"""
        # 创建多个项目
        for i in range(5):
            data = {
                "project_name": f"Test Project {i}",
                "content_hash": f"test_hash_{i}",
                "raw_content": f"Test content {i}",
                "source_platform": "xhs"
            }
            await TGEProjectCRUD.create(test_db, data)
        
        # 获取最新3个项目
        latest_projects = await TGEProjectCRUD.get_latest(test_db, limit=3)
        
        assert len(latest_projects) == 3
        # 验证按时间倒序排列
        for i in range(len(latest_projects) - 1):
            assert latest_projects[i].created_at >= latest_projects[i + 1].created_at
    
    @pytest.mark.asyncio
    async def test_search_by_keywords(self, test_db):
        """测试关键词搜索"""
        # 创建包含不同关键词的项目
        projects_data = [
            {
                "project_name": "DeFi Token",
                "content_hash": "defi_hash",
                "raw_content": "这是一个DeFi项目，即将进行TGE",
                "source_platform": "xhs"
            },
            {
                "project_name": "GameFi Project",
                "content_hash": "gamefi_hash", 
                "raw_content": "GameFi链游项目，代币发行在即",
                "source_platform": "xhs"
            },
            {
                "project_name": "NFT Collection",
                "content_hash": "nft_hash",
                "raw_content": "NFT收藏品项目，无代币发行计划",
                "source_platform": "xhs"
            }
        ]
        
        for data in projects_data:
            await TGEProjectCRUD.create(test_db, data)
        
        # 搜索包含"代币发行"的项目
        results = await TGEProjectCRUD.search_by_keywords(test_db, ["代币发行"])
        assert len(results) == 2  # DeFi和GameFi项目
        
        # 搜索包含"DeFi"的项目
        results = await TGEProjectCRUD.search_by_keywords(test_db, ["DeFi"])
        assert len(results) == 1
        assert results[0].project_name == "DeFi Token"
    
    @pytest.mark.asyncio
    async def test_get_unprocessed(self, test_db, test_tge_project_data):
        """测试获取未处理项目"""
        # 创建已处理和未处理的项目
        await TGEProjectCRUD.create(test_db, test_tge_project_data)
        
        processed_data = test_tge_project_data.copy()
        processed_data["content_hash"] = "processed_hash"
        processed_data["project_name"] = "Processed Project"
        processed_project = await TGEProjectCRUD.create(test_db, processed_data)
        
        # 标记一个为已处理
        await TGEProjectCRUD.update_ai_analysis(test_db, processed_project.id, {"ai_summary": "test"})
        
        # 获取未处理项目
        unprocessed = await TGEProjectCRUD.get_unprocessed(test_db)
        
        assert len(unprocessed) == 1
        assert unprocessed[0].project_name == test_tge_project_data["project_name"]
        assert unprocessed[0].is_processed is False


class TestCrawlerLogCRUD:
    """爬虫日志CRUD测试"""
    
    @pytest.mark.asyncio
    async def test_create_log(self, test_db):
        """测试创建爬虫日志"""
        log_data = {
            "platform": "xhs",
            "keywords": "TGE,代币发行",
            "pages_crawled": 5,
            "items_found": 20,
            "items_processed": 18,
            "items_saved": 15,
            "status": "success",
            "execution_time": 45.5
        }
        
        log = await CrawlerLogCRUD.create_log(test_db, log_data)
        
        assert log is not None
        assert log.platform == "xhs"
        assert log.status == "success"
        assert log.execution_time == 45.5
    
    @pytest.mark.asyncio
    async def test_get_recent_logs(self, test_db):
        """测试获取最近日志"""
        # 创建多个日志
        for i in range(3):
            log_data = {
                "platform": "xhs",
                "status": "success",
                "pages_crawled": i + 1
            }
            await CrawlerLogCRUD.create_log(test_db, log_data)
        
        logs = await CrawlerLogCRUD.get_recent_logs(test_db, limit=2)
        
        assert len(logs) == 2
        # 验证按时间倒序
        assert logs[0].created_at >= logs[1].created_at


class TestAIProcessLogCRUD:
    """AI处理日志CRUD测试"""
    
    @pytest.mark.asyncio
    async def test_create_ai_log(self, test_db):
        """测试创建AI处理日志"""
        log_data = {
            "tge_project_id": 1,
            "input_text": "测试输入文本",
            "output_summary": "测试输出摘要",
            "model_used": "gpt-4o",
            "tokens_used": 150,
            "processing_time": 2.5,
            "status": "success"
        }
        
        log = await AIProcessLogCRUD.create_log(test_db, log_data)
        
        assert log is not None
        assert log.model_used == "gpt-4o"
        assert log.tokens_used == 150
        assert log.status == "success"