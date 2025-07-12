"""
小红书平台适配器
将MediaCrawler的XHS数据转换为统一格式
"""
import json
import sys
import os
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog

from ..base_platform import AbstractPlatform, PlatformError, PlatformUnavailableError
from ..models import RawContent, Platform, ContentType

logger = structlog.get_logger()


class XHSPlatform(AbstractPlatform):
    """小红书平台实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.mediacrawler_path = config.get('mediacrawler_path', '../MediaCrawler')
        self.python_path = self._find_python_path()
    
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.XHS
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        try:
            # 检查MediaCrawler路径是否存在
            mc_path = Path(self.mediacrawler_path)
            if not mc_path.exists():
                self.logger.error("MediaCrawler path not found", path=str(mc_path))
                return False
            
            # 检查main.py是否存在
            main_py = mc_path / "main.py"
            if not main_py.exists():
                self.logger.error("MediaCrawler main.py not found", path=str(main_py))
                return False
            
            self.logger.info("XHS platform available")
            return True
            
        except Exception as e:
            self.logger.error("XHS platform availability check failed", error=str(e))
            return False
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取小红书内容
        
        Args:
            keywords: 搜索关键词列表
            max_count: 最大爬取数量
            **kwargs: 其他参数
            
        Returns:
            爬取到的内容列表
        """
        # 验证关键词
        validated_keywords = await self.validate_keywords(keywords)
        
        # 执行爬取
        raw_data = await self._execute_mediacrawler(validated_keywords, max_count)
        
        # 转换数据格式
        raw_contents = []
        for item in raw_data:
            try:
                content = await self.transform_to_raw_content(item)
                raw_contents.append(content)
            except Exception as e:
                self.logger.warning("Failed to transform content", 
                                  content_id=item.get('note_id', 'unknown'),
                                  error=str(e))
        
        # 过滤内容
        filtered_contents = await self.filter_content(raw_contents)
        
        self.logger.info("XHS crawl completed",
                        keywords=validated_keywords,
                        raw_count=len(raw_data),
                        transformed_count=len(raw_contents),
                        filtered_count=len(filtered_contents))
        
        return filtered_contents
    
    async def _execute_mediacrawler(self, keywords: List[str], max_count: int) -> List[Dict[str, Any]]:
        """
        执行MediaCrawler爬取
        
        Args:
            keywords: 关键词列表
            max_count: 最大数量
            
        Returns:
            原始数据列表
        """
        try:
            # 构建命令
            keywords_str = ",".join(keywords)
            
            cmd = [
                self.python_path, "main.py",
                "--platform", "xhs",
                "--lt", "cookie",  # 使用cookie登录
                "--type", "search",
                "--keywords", keywords_str,
                "--save_data_option", "json"
            ]
            
            self.logger.info("Executing MediaCrawler", 
                           cmd_preview=f"{self.python_path} main.py --platform xhs ...",
                           keywords=keywords)
            
            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=self.mediacrawler_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                env=dict(os.environ, PYTHONPATH=self.mediacrawler_path)
            )
            
            if result.returncode != 0:
                error_msg = f"MediaCrawler execution failed: {result.stderr}"
                self.logger.error("MediaCrawler failed", 
                                error=error_msg,
                                stdout=result.stdout)
                raise PlatformError("xhs", error_msg)
            
            # 读取生成的数据文件
            return await self._read_crawl_results()
            
        except subprocess.TimeoutExpired:
            raise PlatformError("xhs", "MediaCrawler execution timeout")
        except Exception as e:
            raise PlatformError("xhs", f"Failed to execute MediaCrawler: {str(e)}")
    
    async def _read_crawl_results(self) -> List[Dict[str, Any]]:
        """读取爬取结果文件"""
        try:
            # 查找最新的数据文件
            data_dir = Path(self.mediacrawler_path) / "data" / "xhs" / "json"
            
            if not data_dir.exists():
                self.logger.warning("XHS data directory not found", path=str(data_dir))
                return []
            
            # 找到最新的content文件
            content_files = list(data_dir.glob("search_contents_*.json"))
            if not content_files:
                self.logger.warning("No content files found", search_path=str(data_dir))
                return []
            
            # 选择最新的文件
            latest_file = max(content_files, key=lambda f: f.stat().st_mtime)
            
            self.logger.info("Reading crawl results", file_path=str(latest_file))
            
            # 读取JSON数据
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return data
            else:
                self.logger.warning("Unexpected data format", data_type=type(data))
                return []
                
        except Exception as e:
            self.logger.error("Failed to read crawl results", error=str(e))
            return []
    
    async def transform_to_raw_content(self, xhs_data: Dict[str, Any]) -> RawContent:
        """
        将XHS数据转换为统一格式
        
        Args:
            xhs_data: XHS原始数据
            
        Returns:
            标准化的RawContent
        """
        try:
            # 提取基础信息
            note_id = xhs_data.get('note_id', '')
            title = xhs_data.get('title', '')
            desc = xhs_data.get('desc', '')
            content_type = xhs_data.get('type', 'text')
            
            # 组合内容
            full_content = f"{title}\n{desc}".strip()
            
            # 处理时间戳
            publish_time = self._parse_timestamp(xhs_data.get('time'))
            last_update_time = self._parse_timestamp(xhs_data.get('last_update_time'))
            
            # 处理媒体URL
            image_urls = []
            video_urls = []
            
            if content_type == "video" and xhs_data.get('video_url'):
                video_urls.append(xhs_data['video_url'])
            
            if xhs_data.get('image_list'):
                # image_list可能是字符串或列表
                img_list = xhs_data['image_list']
                if isinstance(img_list, str):
                    image_urls.append(img_list)
                elif isinstance(img_list, list):
                    image_urls.extend(img_list)
            
            # 处理标签
            tags = []
            if xhs_data.get('tag_list'):
                tag_str = xhs_data['tag_list']
                if isinstance(tag_str, str):
                    tags = [tag.strip() for tag in tag_str.split(',') if tag.strip()]
                elif isinstance(tag_str, list):
                    tags = tag_str
            
            # 创建RawContent对象
            raw_content = RawContent(
                platform=Platform.XHS,
                content_id=note_id,
                content_type=ContentType.VIDEO if content_type == "video" else ContentType.TEXT,
                title=title,
                content=desc,
                raw_content=json.dumps(xhs_data, ensure_ascii=False),
                author_id=xhs_data.get('user_id', ''),
                author_name=xhs_data.get('nickname', ''),
                author_avatar=xhs_data.get('avatar', ''),
                publish_time=publish_time,
                crawl_time=datetime.utcnow(),
                last_update_time=last_update_time,
                like_count=self._parse_count(xhs_data.get('liked_count')),
                comment_count=self._parse_count(xhs_data.get('comment_count')),
                share_count=self._parse_count(xhs_data.get('share_count')),
                collect_count=self._parse_count(xhs_data.get('collected_count')),
                image_urls=image_urls,
                video_urls=video_urls,
                tags=tags,
                source_url=xhs_data.get('note_url', ''),
                ip_location=xhs_data.get('ip_location', ''),
                platform_metadata={
                    'xsec_token': xhs_data.get('xsec_token', ''),
                    'last_modify_ts': xhs_data.get('last_modify_ts'),
                    'source_keyword': xhs_data.get('source_keyword', '')
                },
                source_keywords=[xhs_data.get('source_keyword', '')] if xhs_data.get('source_keyword') else []
            )
            
            return raw_content
            
        except Exception as e:
            raise PlatformError("xhs", f"Failed to transform XHS data: {str(e)}")
    
    def _parse_timestamp(self, timestamp_value: Any) -> Optional[datetime]:
        """解析时间戳"""
        if not timestamp_value:
            return None
        
        try:
            if isinstance(timestamp_value, (int, float)):
                # 毫秒时间戳
                if timestamp_value > 10**12:
                    return datetime.fromtimestamp(timestamp_value / 1000)
                # 秒时间戳
                else:
                    return datetime.fromtimestamp(timestamp_value)
            return None
        except Exception:
            return None
    
    def _parse_count(self, count_value: Any) -> int:
        """解析数量字段"""
        if not count_value:
            return 0
        
        try:
            if isinstance(count_value, int):
                return count_value
            
            if isinstance(count_value, str):
                # 处理中文数字：1.2万 -> 12000
                if '万' in count_value:
                    return int(float(count_value.replace('万', '')) * 10000)
                elif '千' in count_value:
                    return int(float(count_value.replace('千', '')) * 1000)
                elif count_value.isdigit():
                    return int(count_value)
            
            return 0
        except Exception:
            return 0
    
    def _find_python_path(self) -> str:
        """查找Python路径"""
        # 首先尝试使用UV（如果MediaCrawler使用UV）
        mc_path = Path(self.mediacrawler_path)
        uv_venv = mc_path / ".venv" / "bin" / "python"
        
        if uv_venv.exists():
            return str(uv_venv)
        
        # 然后尝试普通虚拟环境
        venv_python = mc_path / "venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
        
        # 最后使用系统Python
        return sys.executable