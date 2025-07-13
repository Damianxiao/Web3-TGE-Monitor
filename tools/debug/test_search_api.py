#!/usr/bin/env python3
"""
直接测试小红书搜索API
"""
import asyncio
import json
import httpx
import os
from pathlib import Path

async def test_search_api():
    """直接测试搜索API"""
    
    print("🔍 直接测试小红书搜索API")
    print("="*50)
    
    # 从配置文件读取Cookie
    project_root = Path(__file__).parent
    config_path = project_root / "mediacrawler" / "config" / "base_config.py"
    
    # 读取Cookie
    cookies_str = ""
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # 提取COOKIES值
        for line in content.split('\n'):
            if line.strip().startswith('COOKIES = '):
                # 提取引号内的内容
                start = line.find('"') + 1
                end = line.rfind('"')
                cookies_str = line[start:end]
                break
    
    print(f"📝 Cookie长度: {len(cookies_str)}")
    
    # 构建请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.xiaohongshu.com',
        'Referer': 'https://www.xiaohongshu.com/',
        'Cookie': cookies_str,
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
    }
    
    # 测试数据
    test_data = {
        "keyword": "美食",
        "page": 1,
        "page_size": 5,
        "search_id": "2F21KWVJ6B5QUCH351MPD",
        "sort": "general",
        "note_type": 0,
    }
    
    print(f"📡 测试搜索API...")
    print(f"   - 关键词: {test_data['keyword']}")
    print(f"   - 页面大小: {test_data['page_size']}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 发送POST请求
            response = await client.post(
                "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
                headers=headers,
                json=test_data
            )
            
            print(f"📊 响应状态: {response.status_code}")
            print(f"📊 响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📊 响应数据:")
                    print(f"   - 类型: {type(result)}")
                    print(f"   - 键: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                    
                    if isinstance(result, dict):
                        if 'items' in result:
                            items = result['items']
                            print(f"   - items数量: {len(items) if items else 0}")
                            if items:
                                print(f"   - 第一个item: {json.dumps(items[0], indent=2, ensure_ascii=False)[:300]}...")
                        else:
                            print(f"   - 完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"   - 原始响应: {response.text[:500]}...")
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"   - 响应内容: {response.text[:500]}...")
                
        except Exception as e:
            print(f"❌ 请求异常: {type(e).__name__}: {e}")
    
    # 测试不同的关键词
    test_keywords = ["小红书", "旅行", "go"]
    
    for keyword in test_keywords:
        print(f"\n" + "-"*30)
        print(f"🔍 测试关键词: {keyword}")
        
        test_data_copy = test_data.copy()
        test_data_copy["keyword"] = keyword
        test_data_copy["search_id"] = f"TEST_{keyword.upper()}_ID"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
                    headers=headers,
                    json=test_data_copy
                )
                
                print(f"   - 状态码: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if isinstance(result, dict) and 'items' in result:
                            items_count = len(result['items']) if result['items'] else 0
                            print(f"   - 结果数量: {items_count}")
                        else:
                            print(f"   - 响应: {result}")
                    except:
                        print(f"   - 原始响应: {response.text[:100]}...")
                else:
                    print(f"   - 错误: {response.text[:100]}...")
                    
            except Exception as e:
                print(f"   - 异常: {type(e).__name__}: {e}")
        
        await asyncio.sleep(1)  # 避免请求过快

if __name__ == "__main__":
    print("🔬 小红书搜索API直接测试工具")
    asyncio.run(test_search_api())
