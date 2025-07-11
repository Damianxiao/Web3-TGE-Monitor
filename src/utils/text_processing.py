"""
文本处理工具模块
"""
import re
import jieba
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class TextProcessor:
    """文本处理器"""
    
    def __init__(self):
        # 预编译正则表达式
        self._url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self._emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        self._mention_pattern = re.compile(r'@[\u4e00-\u9fa5\w]+')
        self._hashtag_pattern = re.compile(r'#[\u4e00-\u9fa5\w]+')
        
        # TGE相关信息提取模式
        self._tge_patterns = {
            'tge_date': [
                r'(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(\d{1,2}月\d{1,2}日)',
                r'(\d{4}-\d{1,2}-\d{1,2})',
                r'(20\d{2}/\d{1,2}/\d{1,2})'
            ],
            'token_symbol': [
                r'\$([A-Z]{2,10})',
                r'([A-Z]{2,10})代币',
                r'([A-Z]{2,10})\s*Token'
            ],
            'amount': [
                r'(\d+(?:\.\d+)?[万亿千百十]?[枚个]?)',
                r'总供应量.*?(\d+(?:\.\d+)?[万亿千百十]?)',
                r'发行.*?(\d+(?:\.\d+)?[万亿千百十]?)'
            ]
        }
    
    def clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除URL
        text = self._url_pattern.sub('', text)
        
        # 移除emoji（可选）
        # text = self._emoji_pattern.sub('', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除首尾空格
        text = text.strip()
        
        return text
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 文本内容
            top_k: 返回前k个关键词
            
        Returns:
            关键词列表
        """
        if not text:
            return []
        
        # 使用jieba进行分词
        words = jieba.cut(text)
        
        # 过滤停用词和短词
        filtered_words = [
            word.strip() for word in words 
            if len(word.strip()) > 1 and word.strip() not in ['的', '了', '在', '是', '有', '和', '与', '或']
        ]
        
        # 统计词频
        word_count = {}
        for word in filtered_words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # 按频率排序并返回前k个
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, count in sorted_words[:top_k]]
    
    def extract_tge_info(self, text: str) -> Dict[str, Any]:
        """
        提取TGE相关信息
        
        Args:
            text: 文本内容
            
        Returns:
            提取的信息字典
        """
        info = {
            'tge_date': None,
            'token_symbol': None,
            'amounts': [],
            'project_name': None
        }
        
        if not text:
            return info
        
        # 提取TGE时间
        for pattern in self._tge_patterns['tge_date']:
            match = re.search(pattern, text)
            if match:
                info['tge_date'] = match.group(1)
                break
        
        # 提取代币符号
        for pattern in self._tge_patterns['token_symbol']:
            match = re.search(pattern, text)
            if match:
                info['token_symbol'] = match.group(1)
                break
        
        # 提取数量信息
        for pattern in self._tge_patterns['amount']:
            matches = re.findall(pattern, text)
            info['amounts'].extend(matches)
        
        # 简单的项目名称提取
        project_patterns = [
            r'([A-Za-z\u4e00-\u9fa5]+)(?:项目|协议|网络|平台)',
            r'([A-Z][a-z]+[A-Z][a-z]+)',  # CamelCase
        ]
        
        for pattern in project_patterns:
            match = re.search(pattern, text)
            if match:
                info['project_name'] = match.group(1)
                break
        
        return info
    
    def extract_mentions_and_hashtags(self, text: str) -> Dict[str, List[str]]:
        """
        提取提及用户和话题标签
        
        Args:
            text: 文本内容
            
        Returns:
            包含mentions和hashtags的字典
        """
        if not text:
            return {'mentions': [], 'hashtags': []}
        
        mentions = [match.group() for match in self._mention_pattern.finditer(text)]
        hashtags = [match.group() for match in self._hashtag_pattern.finditer(text)]
        
        return {
            'mentions': mentions,
            'hashtags': hashtags
        }
    
    def calculate_readability_score(self, text: str) -> float:
        """
        计算文本可读性评分（简化版）
        
        Args:
            text: 文本内容
            
        Returns:
            可读性评分 (0-1)
        """
        if not text:
            return 0.0
        
        # 简单的可读性指标
        sentences = len(re.split(r'[。！？.!?]', text))
        words = len(list(jieba.cut(text)))
        
        if sentences == 0 or words == 0:
            return 0.0
        
        avg_words_per_sentence = words / sentences
        
        # 理想的句子长度是10-20个词
        if 10 <= avg_words_per_sentence <= 20:
            score = 1.0
        elif avg_words_per_sentence < 10:
            score = avg_words_per_sentence / 10
        else:
            score = max(0.1, 20 / avg_words_per_sentence)
        
        return min(1.0, score)
    
    def extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """
        提取联系方式信息
        
        Args:
            text: 文本内容
            
        Returns:
            包含各种联系方式的字典
        """
        if not text:
            return {'telegram': [], 'discord': [], 'twitter': [], 'websites': []}
        
        contact_patterns = {
            'telegram': [r't\.me/[\w]+', r'telegram.*?@[\w]+'],
            'discord': [r'discord\.gg/[\w]+', r'discord\.com/invite/[\w]+'],
            'twitter': [r'twitter\.com/[\w]+', r'@[\w]+'],
            'websites': [r'https?://[\w\.-]+\.[\w]+']
        }
        
        results = {}
        for contact_type, patterns in contact_patterns.items():
            matches = []
            for pattern in patterns:
                matches.extend(re.findall(pattern, text, re.IGNORECASE))
            results[contact_type] = list(set(matches))  # 去重
        
        return results


# 全局文本处理器实例
text_processor = TextProcessor()


def process_raw_content(content: str, extract_info: bool = True) -> Dict[str, Any]:
    """
    处理原始内容
    
    Args:
        content: 原始内容
        extract_info: 是否提取详细信息
        
    Returns:
        处理结果字典
    """
    result = {
        'cleaned_text': text_processor.clean_text(content),
        'keywords': text_processor.extract_keywords(content),
        'readability_score': text_processor.calculate_readability_score(content)
    }
    
    if extract_info:
        result.update({
            'tge_info': text_processor.extract_tge_info(content),
            'social_info': text_processor.extract_mentions_and_hashtags(content),
            'contact_info': text_processor.extract_contact_info(content)
        })
    
    return result