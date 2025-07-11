"""
Web3关键词配置
"""
from typing import List, Dict

# 核心关键词
CORE_KEYWORDS: List[str] = [
    "TGE",
    "代币发行", 
    "空投",
    "IDO",
    "新币上线",
    "DeFi",
    "Web3项目",
    "撸毛",
    "开启测试网",
    "速撸"
]

# 扩展关键词
EXTENDED_KEYWORDS: List[str] = [
    "代币经济",
    "白名单",
    "公募",
    "私募",
    "预售",
    "IEO",
    "ICO",
    "GameFi",
    "NFT项目",
    "Layer2",
    "跨链",
    "挖矿",
    "质押",
    "流动性挖矿",
    "DEX",
    "CEX上币",
    "主网上线",
    "测试网",
    "空投猎手",
    "薅羊毛",
    "币圈",
    "链游",
    "元宇宙",
    "DAO"
]

# 风险关键词（用于风险评估）
RISK_KEYWORDS: List[str] = [
    "风险",
    "谨慎",
    "DYOR",
    "NFA",
    "骗局",
    "跑路",
    "归零",
    "暴跌",
    "亏损",
    "高风险"
]

# 积极关键词（用于情感分析）
POSITIVE_KEYWORDS: List[str] = [
    "看涨",
    "利好",
    "暴涨",
    "百倍币",
    "潜力",
    "机会",
    "推荐",
    "值得关注",
    "强势",
    "突破"
]

# 消极关键词
NEGATIVE_KEYWORDS: List[str] = [
    "看跌",
    "利空",
    "下跌",
    "套牢",
    "亏损",
    "谨慎",
    "回避",
    "风险高",
    "不推荐"
]

# 关键词权重配置
KEYWORD_WEIGHTS: Dict[str, float] = {
    "TGE": 1.0,
    "代币发行": 1.0,
    "空投": 0.9,
    "IDO": 0.9,
    "新币上线": 0.8,
    "DeFi": 0.7,
    "Web3项目": 0.6,
    "撸毛": 0.8,
    "开启测试网": 0.7,
    "速撸": 0.8
}

def get_all_keywords() -> List[str]:
    """获取所有关键词"""
    return CORE_KEYWORDS + EXTENDED_KEYWORDS

def get_weighted_keywords() -> Dict[str, float]:
    """获取带权重的关键词"""
    return KEYWORD_WEIGHTS

def is_risk_keyword(text: str) -> bool:
    """检查是否包含风险关键词"""
    return any(keyword in text for keyword in RISK_KEYWORDS)

def get_sentiment_score(text: str) -> float:
    """
    计算文本情感得分
    返回值：-1.0 到 1.0，负数表示负面，正数表示正面
    """
    positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text)
    negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text)
    
    total_count = positive_count + negative_count
    if total_count == 0:
        return 0.0
    
    return (positive_count - negative_count) / total_count