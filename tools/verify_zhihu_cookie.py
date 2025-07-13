#!/usr/bin/env python3
"""
知乎Cookie有效性验证脚本
Phase 2 真实集成测试 - 步骤1: Cookie和API访问验证

验证Cookie配置是否正确，知乎API是否可正常访问
"""
import asyncio
import sys
import os
import json
from typing import Dict, Any

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from dotenv import load_dotenv
import structlog
import httpx

# 加载环境变量
load_dotenv()

# 配置日志
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class ZhihuCookieValidator:
    """知乎Cookie验证器"""
    
    def __init__(self):
        self.cookie = os.getenv("ZHIHU_COOKIE", "")
        self.base_url = "https://www.zhihu.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        
    async def validate_cookie_format(self) -> bool:
        """验证Cookie格式"""
        logger.info("🔍 验证Cookie格式...")
        
        if not self.cookie:
            logger.error("❌ ZHIHU_COOKIE环境变量未配置")
            return False
        
        # 检查关键Cookie字段
        required_fields = ['d_c0', 'z_c0', 'SESSIONID', '_xsrf']
        missing_fields = []
        
        for field in required_fields:
            if field not in self.cookie:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error("❌ Cookie缺少关键字段", missing_fields=missing_fields)
            return False
        
        logger.info("✅ Cookie格式验证通过", cookie_length=len(self.cookie))
        return True
    
    async def validate_user_api(self) -> Dict[str, Any]:
        """验证用户API访问"""
        logger.info("🔍 验证知乎用户API访问...")
        
        url = f"{self.base_url}/api/v4/me"
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
                
                logger.info("📡 用户API请求完成", 
                          status_code=response.status_code,
                          response_size=len(response.text))
                
                if response.status_code == 200:
                    try:
                        user_data = response.json()
                        if 'id' in user_data:
                            logger.info("✅ 用户API访问成功",
                                      user_id=user_data.get('id', 'unknown'),
                                      name=user_data.get('name', 'unknown'))
                            return {
                                'success': True,
                                'user_data': user_data,
                                'message': 'Cookie有效，用户认证成功'
                            }
                        else:
                            logger.warning("⚠️ API返回数据异常", response=user_data)
                            return {
                                'success': False,
                                'message': 'API返回数据格式异常'
                            }
                    except json.JSONDecodeError:
                        logger.error("❌ API响应JSON解析失败", response_text=response.text[:200])
                        return {
                            'success': False,
                            'message': 'API响应格式错误'
                        }
                elif response.status_code == 401:
                    logger.error("❌ Cookie无效或已过期")
                    return {
                        'success': False,
                        'message': 'Cookie无效或已过期，需要重新获取'
                    }
                elif response.status_code == 403:
                    logger.error("❌ 访问被拒绝，可能需要验证码")
                    return {
                        'success': False,
                        'message': '访问被拒绝，Cookie可能需要验证'
                    }
                else:
                    logger.warning("⚠️ API访问异常", 
                                 status_code=response.status_code,
                                 response_text=response.text[:200])
                    return {
                        'success': False,
                        'message': f'API访问异常，状态码: {response.status_code}'
                    }
                    
        except Exception as e:
            logger.error("❌ 用户API访问失败", error=str(e))
            return {
                'success': False,
                'message': f'网络请求失败: {str(e)}'
            }
    
    async def validate_search_api(self) -> Dict[str, Any]:
        """验证搜索API访问"""
        logger.info("🔍 验证知乎搜索API访问...")
        
        url = f"{self.base_url}/api/v4/search_v3"
        params = {
            "t": "general",
            "q": "Web3",  # 改用英文避免编码问题
            "correction": "1",
            "offset": "0",
            "limit": "5",
            "lc_idx": "1",
            "show_all_topics": "0"
        }
        
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/search?type=content&q=Web3",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "x-requested-with": "fetch"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                logger.info("📡 搜索API请求完成",
                          status_code=response.status_code,
                          response_size=len(response.text))
                
                if response.status_code == 200:
                    try:
                        search_data = response.json()
                        data_items = search_data.get('data', [])
                        
                        if isinstance(data_items, list) and len(data_items) > 0:
                            logger.info("✅ 搜索API访问成功",
                                      result_count=len(data_items),
                                      has_paging=('paging' in search_data))
                            
                            # 分析数据类型
                            content_types = {}
                            for item in data_items[:3]:  # 分析前3条数据
                                item_type = item.get('type', 'unknown')
                                content_types[item_type] = content_types.get(item_type, 0) + 1
                            
                            return {
                                'success': True,
                                'search_data': search_data,
                                'result_count': len(data_items),
                                'content_types': content_types,
                                'message': '搜索API访问成功，数据格式正常'
                            }
                        else:
                            logger.warning("⚠️ 搜索API返回空数据")
                            return {
                                'success': False,
                                'message': '搜索API返回空数据，可能关键词无结果'
                            }
                    except json.JSONDecodeError:
                        logger.error("❌ 搜索API响应JSON解析失败")
                        return {
                            'success': False,
                            'message': '搜索API响应格式错误'
                        }
                else:
                    logger.warning("⚠️ 搜索API访问异常",
                                 status_code=response.status_code,
                                 response_text=response.text[:200])
                    return {
                        'success': False,
                        'message': f'搜索API访问异常，状态码: {response.status_code}'
                    }
                    
        except Exception as e:
            logger.error("❌ 搜索API访问失败", error=str(e))
            return {
                'success': False,
                'message': f'搜索API网络请求失败: {str(e)}'
            }
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """运行完整验证流程"""
        logger.info("🚀 开始知乎Cookie完整验证...")
        
        validation_results = {
            'cookie_format': False,
            'user_api': False,
            'search_api': False,
            'overall_success': False,
            'messages': []
        }
        
        # 1. Cookie格式验证
        format_valid = await self.validate_cookie_format()
        validation_results['cookie_format'] = format_valid
        
        if not format_valid:
            validation_results['messages'].append('Cookie格式验证失败')
            return validation_results
        
        # 2. 用户API验证
        user_result = await self.validate_user_api()
        validation_results['user_api'] = user_result['success']
        validation_results['messages'].append(user_result['message'])
        
        if user_result['success']:
            validation_results['user_data'] = user_result.get('user_data', {})
        
        # 3. 搜索API验证
        search_result = await self.validate_search_api()
        validation_results['search_api'] = search_result['success']
        validation_results['messages'].append(search_result['message'])
        
        if search_result['success']:
            validation_results['search_data'] = {
                'result_count': search_result.get('result_count', 0),
                'content_types': search_result.get('content_types', {})
            }
        
        # 综合判断
        validation_results['overall_success'] = (
            validation_results['cookie_format'] and
            validation_results['user_api'] and
            validation_results['search_api']
        )
        
        return validation_results


async def main():
    """主函数"""
    logger.info("🎯 Phase 2 知乎Cookie验证开始")
    
    validator = ZhihuCookieValidator()
    results = await validator.run_full_validation()
    
    print("\n" + "="*60)
    print("📊 知乎Cookie验证结果报告")
    print("="*60)
    
    print(f"Cookie格式验证: {'✅ 通过' if results['cookie_format'] else '❌ 失败'}")
    print(f"用户API验证:   {'✅ 通过' if results['user_api'] else '❌ 失败'}")
    print(f"搜索API验证:   {'✅ 通过' if results['search_api'] else '❌ 失败'}")
    print(f"综合验证结果:  {'✅ 通过' if results['overall_success'] else '❌ 失败'}")
    
    print("\n📝 详细信息:")
    for i, message in enumerate(results['messages'], 1):
        print(f"  {i}. {message}")
    
    if results.get('user_data'):
        user_info = results['user_data']
        print(f"\n👤 用户信息:")
        print(f"  用户ID: {user_info.get('id', 'N/A')}")
        print(f"  用户名: {user_info.get('name', 'N/A')}")
        print(f"  头像: {'有' if user_info.get('avatar_url') else '无'}")
    
    if results.get('search_data'):
        search_info = results['search_data']
        print(f"\n🔍 搜索测试结果:")
        print(f"  结果数量: {search_info.get('result_count', 0)}")
        print(f"  内容类型: {search_info.get('content_types', {})}")
    
    print("\n" + "="*60)
    
    if results['overall_success']:
        print("🎉 知乎Cookie验证成功！可以进行下一步集成测试。")
        return 0
    else:
        print("💥 知乎Cookie验证失败！请检查Cookie配置。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)