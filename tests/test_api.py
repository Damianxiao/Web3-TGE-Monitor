"""
FastAPI服务集成测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from contextlib import contextmanager

# 模拟所有的外部依赖
@contextmanager
def mock_database():
    """Mock数据库依赖"""
    with patch('src.database.database.init_database', new_callable=AsyncMock):
        with patch('src.database.database.get_db_session'):
            yield

@contextmanager
def mock_ai_services():
    """MockAI服务"""
    with patch('src.ai.ai_processing_manager'):
        yield

@contextmanager
def mock_crawler_services():
    """Mock爬虫服务"""
    with patch('src.crawler.crawler_manager'):
        yield

@pytest.fixture
def client():
    """FastAPI测试客户端"""
    # 简化mock
    with patch('src.database.database.init_database', new_callable=AsyncMock):
        with patch('src.database.database.get_db_session'):
            # 设置Python路径
            import sys
            sys.path.insert(0, '/home/damian/Web3-TGE-Monitor')
            
            from main import app
            
            with TestClient(app) as test_client:
                yield test_client


class TestAPIBasics:
    """基础API测试"""
    
    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Web3 TGE Monitor API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_openapi_docs(self, client):
        """测试API文档端点"""
        # 测试OpenAPI文档
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # 测试OpenAPI JSON
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
    
    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/api/v1/projects", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestProjectsAPI:
    """项目数据API测试"""
    
    @patch('src.database.crud.TGEProjectCRUD.get_paginated')
    def test_get_projects_list(self, mock_get_paginated, client):
        """测试获取项目列表"""
        # Mock数据
        mock_projects = [
            MagicMock(
                id=1,
                project_name="Test Project",
                token_symbol="TEST",
                project_category="DeFi",
                risk_level="Medium",
                source_platform="xhs",
                investment_rating=4,
                investment_recommendation="关注",
                overall_score=3.5,
                engagement_score=0.7,
                created_at=datetime.utcnow(),
                tge_date="2025-02-01",
                is_processed=True
            )
        ]
        mock_get_paginated.return_value = (mock_projects, 1)
        
        response = client.get("/api/v1/projects?page=1&size=20")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "items" in data["data"]
        assert len(data["data"]["items"]) == 1
        assert data["data"]["total"] == 1
    
    @patch('src.database.crud.TGEProjectCRUD.get_by_id')
    def test_get_project_detail(self, mock_get_by_id, client):
        """测试获取项目详情"""
        # Mock数据
        mock_project = MagicMock(
            id=1,
            project_name="Test Project",
            token_symbol="TEST",
            project_category="DeFi",
            risk_level="Medium",
            tge_date="2025-02-01",
            source_platform="xhs",
            source_url="https://test.com",
            source_username="test_user",
            raw_content="Test content",
            tge_summary="Test summary",
            key_features="feature1,feature2",
            investment_rating=4,
            investment_recommendation="关注",
            investment_reason="Good potential",
            key_advantages="advantage1,advantage2",
            key_risks="risk1,risk2",
            potential_score=4,
            overall_score=3.8,
            sentiment_score=0.3,
            sentiment_label="Positive",
            market_sentiment="Bullish",
            engagement_score=0.7,
            keyword_matches="TGE,DeFi",
            content_hash="test_hash",
            is_processed=True,
            analysis_confidence=0.8,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_get_by_id.return_value = mock_project
        
        response = client.get("/api/v1/projects/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["project_name"] == "Test Project"
    
    def test_get_project_not_found(self, client):
        """测试项目不存在"""
        with patch('src.database.crud.TGEProjectCRUD.get_by_id', return_value=None):
            response = client.get("/api/v1/projects/999")
            assert response.status_code == 404
    
    @patch('src.database.crud.TGEProjectCRUD.search')
    def test_search_projects(self, mock_search, client):
        """测试搜索项目"""
        mock_search.return_value = ([], 0)
        
        response = client.get("/api/v1/projects/search?query=TGE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        mock_search.assert_called_once()
    
    @patch('src.database.crud.TGEProjectCRUD.get_category_stats')
    def test_get_categories(self, mock_get_category_stats, client):
        """测试获取分类统计"""
        mock_get_category_stats.return_value = {
            "DeFi": 10,
            "GameFi": 5,
            "NFT": 3
        }
        
        response = client.get("/api/v1/projects/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["DeFi"] == 10


class TestCrawlerAPI:
    """爬虫API测试"""
    
    @patch('src.crawler.crawler_manager.submit_crawl_task')
    @patch('src.crawler.crawler_manager.get_task_status')
    def test_create_crawl_task(self, mock_get_task_status, mock_submit_task, client):
        """测试创建爬虫任务"""
        # Mock返回数据
        mock_submit_task.return_value = "task_123"
        mock_task = MagicMock(
            task_id="task_123",
            platform=MagicMock(value="xhs"),
            status="pending",
            keywords=["TGE"],
            max_count=50,
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None
        )
        mock_get_task_status.return_value = mock_task
        
        task_request = {
            "platform": "xhs",
            "keywords": ["TGE", "代币发行"],
            "max_count": 50
        }
        
        response = client.post("/api/v1/crawler/tasks", json=task_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "task_123"
        assert data["data"]["platform"] == "xhs"
    
    def test_create_invalid_task(self, client):
        """测试创建无效任务"""
        invalid_request = {
            "platform": "invalid_platform",
            "max_count": -1
        }
        
        response = client.post("/api/v1/crawler/tasks", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    @patch('src.crawler.crawler_manager.get_task_status')
    def test_get_task_status(self, mock_get_task_status, client):
        """测试获取任务状态"""
        mock_task = MagicMock(
            task_id="task_123",
            platform=MagicMock(value="xhs"),
            status="completed",
            keywords=["TGE"],
            max_count=50,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        mock_get_task_status.return_value = mock_task
        
        response = client.get("/api/v1/crawler/tasks/task_123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "task_123"
        assert data["data"]["status"] == "completed"
        assert data["data"]["progress"] == 100


class TestAIProcessingAPI:
    """
AI处理API测试
    """
    
    @patch('src.ai.ai_processing_manager.get_processing_statistics')
    def test_get_ai_statistics(self, mock_get_stats, client):
        """测试获取AI统计"""
        mock_get_stats.return_value = {
            "total_projects": 100,
            "processed_projects": 80,
            "unprocessed_projects": 20,
            "processing_rate": 80.0,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        response = client.get("/api/v1/ai/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_projects"] == 100
        assert data["data"]["processing_rate"] == 80.0
    
    @patch('src.ai.ai_processing_manager.process_single_content')
    @patch('src.database.crud.TGEProjectCRUD.get_by_id')
    def test_process_single_project(self, mock_get_by_id, mock_process, client):
        """测试单个AI分析"""
        # Mock项目数据
        mock_project = MagicMock(id=1, is_processed=False)
        mock_get_by_id.return_value = mock_project
        
        # MockAI处理结果
        mock_process.return_value = {"success": True, "analysis": {}}
        
        # Mock更新后的项目
        updated_project = MagicMock(
            id=1,
            project_name="Test Project",
            token_symbol="TEST",
            project_category="DeFi",
            tge_date="2025-02-01",
            risk_level="Medium",
            investment_rating=4,
            investment_recommendation="关注",
            potential_score=4,
            overall_score=3.8,
            sentiment_score=0.3,
            sentiment_label="Positive",
            analysis_confidence=0.8,
            updated_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        mock_get_by_id.return_value = updated_project
        
        request_data = {
            "project_id": 1,
            "include_sentiment": True,
            "force_reprocess": False
        }
        
        response = client.post("/api/v1/ai/process", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["project_id"] == 1


class TestSystemAPI:
    """系统API测试"""
    
    @patch('src.database.crud.TGEProjectCRUD.count_all')
    @patch('src.database.crud.TGEProjectCRUD.count_processed')
    @patch('src.database.crud.TGEProjectCRUD.count_recent')
    @patch('src.database.crud.TGEProjectCRUD.get_platform_stats')
    @patch('src.database.crud.TGEProjectCRUD.get_category_stats')
    def test_get_system_stats(self, mock_category_stats, mock_platform_stats, 
                             mock_count_recent, mock_count_processed, mock_count_all, client):
        """测试获取系统统计"""
        # Mock数据
        mock_count_all.return_value = 100
        mock_count_processed.return_value = 80
        mock_count_recent.return_value = 10
        mock_platform_stats.return_value = {"xhs": 50, "douyin": 30}
        mock_category_stats.return_value = {"DeFi": 40, "GameFi": 20}
        
        response = client.get("/api/v1/system/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_projects"] == 100
        assert data["data"]["processed_projects"] == 80
        assert data["data"]["unprocessed_projects"] == 20
    
    def test_get_system_config(self, client):
        """测试获取系统配置"""
        response = client.get("/api/v1/system/config")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "app" in data["data"]
        assert "database" in data["data"]
        assert "ai" in data["data"]
        # 检查敏感信息是否被隐藏
        assert data["data"]["database"]["password"] == "***"
        assert data["data"]["ai"]["api_key"] == "***"
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_percent')
    def test_get_system_metrics(self, mock_cpu, mock_disk, mock_memory, client):
        """测试获取系统指标"""
        # Mock系统指标
        mock_memory.return_value = MagicMock(total=8000000000, used=4000000000, percent=50.0)
        mock_disk.return_value = MagicMock(total=100000000000, used=50000000000, percent=50.0)
        mock_cpu.return_value = 25.0
        
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "cpu" in data["data"]
        assert "memory" in data["data"]
        assert "disk" in data["data"]


class TestErrorHandling:
    """错误处理测试"""
    
    def test_404_error(self, client):
        """测试404错误"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_validation_error(self, client):
        """测试参数验证错误"""
        # 无效的爬虫任务请求
        invalid_request = {
            "platform": "invalid",
            "max_count": -1
        }
        
        response = client.post("/api/v1/crawler/tasks", json=invalid_request)
        assert response.status_code == 422
        
        data = response.json()
        assert data["error"] is True
        assert "details" in data
    
    def test_method_not_allowed(self, client):
        """测试不允许的HTTP方法"""
        response = client.post("/api/v1/projects/1")  # 使用POST而不GET
        assert response.status_code == 405


# 集成测试
@pytest.mark.asyncio
async def test_full_workflow_integration():
    """集成测试：完整工作流程"""
    # 这里可以添加更复杂的集成测试
    # 例如：创建爬虫任务 -> 执行爬虫 -> AI分析 -> 查询结果
    pass


if __name__ == "__main__":
    # 运行测试
    pytest.main(["-v", __file__])