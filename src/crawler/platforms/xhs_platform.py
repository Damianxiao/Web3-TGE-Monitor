"""
小红书平台适配器 - 整合版
直接使用项目内部的mediacrawler模块
"""
import json
import sys
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog

from ..base_platform import AbstractPlatform, PlatformError, PlatformUnavailableError
from ..models import RawContent, Platform, ContentType

logger = structlog.get_logger()


class XHSPlatform(AbstractPlatform):
    """小红书平台实现 - 整合版"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 设置mediacrawler路径为项目内部路径
        project_root = Path(__file__).parent.parent.parent.parent
        self.mediacrawler_path = str(project_root / "mediacrawler")
        self._xhs_client = None
        
        # 确保mediacrawler在Python路径中
        self._ensure_mediacrawler_in_path()
        
    def _ensure_mediacrawler_in_path(self):
        """确保mediacrawler路径在Python路径中"""
        if self.mediacrawler_path not in sys.path:
            sys.path.insert(0, self.mediacrawler_path)
            self.logger.info("Added mediacrawler to Python path", path=self.mediacrawler_path)
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.XHS
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        original_cwd = os.getcwd()
        try:
            # 验证mediacrawler目录结构
            mediacrawler_path = Path(self.mediacrawler_path)
            required_files = [
                mediacrawler_path / "media_platform" / "xhs" / "core.py",
                mediacrawler_path / "media_platform" / "xhs" / "client.py",
                mediacrawler_path / "base" / "base_crawler.py"
            ]
            
            for required_file in required_files:
                if not required_file.exists():
                    self.logger.error("Required file not found", file=str(required_file))
                    return False
            
            # 切换到mediacrawler目录以确保相对路径正确
            os.chdir(self.mediacrawler_path)
            
            # 尝试导入mediacrawler的XHS模块
            from media_platform.xhs import client as xhs_client
            from media_platform.xhs import core as xhs_core
            
            self.logger.info("XHS platform modules imported successfully")
            return True
            
        except Exception as e:
            self.logger.error("XHS platform not available", error=str(e))
            return False
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _get_xhs_client(self):
        """获取XHS爬虫实例（延迟初始化）"""
        if self._xhs_client is None:
            try:
                # 导入MediaCrawler的XHS核心爬虫
                from media_platform.xhs.core import XiaoHongShuCrawler
                
                # 创建爬虫实例
                self._xhs_client = XiaoHongShuCrawler()
                
                self.logger.info("XHS crawler initialized")
                
            except Exception as e:
                self.logger.error("Failed to initialize XHS crawler", error=str(e))
                raise PlatformError("xhs", f"Failed to initialize XHS crawler: {str(e)}")
        
        return self._xhs_client
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取小红书内容 - 新的共享库实现
        
        Args:
            keywords: 搜索关键词列表
            max_count: 最大爬取数量
            **kwargs: 其他参数
            
        Returns:
            爬取到的内容列表
        """
        try:
            # 验证关键词
            validated_keywords = await self.validate_keywords(keywords)
            
            self.logger.info("Starting XHS crawl with shared library",
                           keywords=validated_keywords,
                           max_count=max_count)
            
            # 获取XHS爬虫
            crawler = await self._get_xhs_client()
            
            # 执行搜索爬取
            raw_data = await self._search_notes_with_client(crawler, validated_keywords, max_count)
            
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
            
        except Exception as e:
            self.logger.error("XHS crawl failed", error=str(e))
            raise PlatformError("xhs", f"Crawl failed: {str(e)}")
    
    async def _search_notes_with_client(
        self, 
        crawler, 
        keywords: List[str], 
        max_count: int
    ) -> List[Dict[str, Any]]:
        """
        使用XHS爬虫搜索笔记
        
        Args:
            crawler: XHS爬虫实例
            keywords: 关键词列表
            max_count: 最大数量
            
        Returns:
            原始数据列表
        """
        try:
            # 首先需要启动爬虫（创建浏览器实例等）
            await crawler.start()
            
            all_notes = []
            
            # 获取初始化后的客户端
            client = crawler.xhs_client
            
            for keyword in keywords:
                self.logger.info("Searching for keyword", keyword=keyword)
                
                try:
                    # 直接调用客户端的搜索API
                    from media_platform.xhs.field import SearchSortType
                    from media_platform.xhs.help import get_search_id
                    
                    # 搜索笔记
                    notes_res = await client.get_note_by_keyword(
                        keyword=keyword,
                        search_id=get_search_id(),
                        page=1,
                        page_size=min(20, max_count),  # XHS每页最多20条
                        sort=SearchSortType.GENERAL
                    )
                    
                    if not notes_res or not notes_res.get("items"):
                        self.logger.warning("No notes found for keyword", keyword=keyword)
                        continue
                    
                    # 获取笔记详情
                    for post_item in notes_res.get("items", []):
                        if post_item.get("model_type") in ("rec_query", "hot_query"):
                            continue
                            
                        try:
                            note_detail = await client.get_note_by_id(
                                note_id=post_item.get("id"),
                                xsec_source=post_item.get("xsec_source"),
                                xsec_token=post_item.get("xsec_token")
                            )
                            
                            if note_detail:
                                # 添加来源关键词
                                note_detail['source_keyword'] = keyword
                                all_notes.append(note_detail)
                                
                                self.logger.debug("Found note", 
                                                note_id=post_item.get("id"),
                                                keyword=keyword)
                                
                        except Exception as e:
                            self.logger.warning("Failed to get note detail", 
                                              note_id=post_item.get("id"),
                                              error=str(e))
                            continue
                    
                    self.logger.info("Found notes for keyword", 
                                   keyword=keyword, 
                                   count=len([n for n in all_notes if n.get('source_keyword') == keyword]))
                
                except Exception as e:
                    self.logger.error("Failed to search keyword", 
                                    keyword=keyword, 
                                    error=str(e))
                    continue
                
                # 控制总数
                if len(all_notes) >= max_count:
                    break
            
            # 截取到指定数量
            result = all_notes[:max_count]
            
            self.logger.info("Search completed", 
                           total_found=len(all_notes), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("Search notes failed", error=str(e))
            raise PlatformError("xhs", f"Search failed: {str(e)}")
        finally:
            # 确保关闭浏览器和清理资源
            try:
                if hasattr(crawler, 'close'):
                    await crawler.close()
                # 重置客户端实例以避免状态残留
                self._xhs_client = None
            except Exception as e:
                self.logger.warning("Failed to close crawler", error=str(e))
    
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