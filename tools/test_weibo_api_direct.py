"""
直接测试微博API连接
不依赖项目内部模块，直接使用httpx测试微博搜索API
"""
import asyncio
import httpx
import json
import os

async def test_weibo_api_direct():
    """直接测试微博搜索API"""
    print("=== 直接微博API测试 ===")
    
    # 检查Cookie配置
    weibo_cookie = os.getenv("WEIBO_COOKIE", "")
    
    if not weibo_cookie:
        print("❌ WEIBO_COOKIE未配置")
        print("\n如何获取微博Cookie:")
        print("1. 使用浏览器打开 https://m.weibo.cn")
        print("2. 登录您的微博账号")
        print("3. 打开浏览器开发者工具 (F12)")
        print("4. 转到 Network (网络) 标签")
        print("5. 刷新页面")
        print("6. 找到任意请求，查看 Request Headers")
        print("7. 复制 Cookie 的完整值")
        print("8. 将Cookie添加到 .env 文件:")
        print('   WEIBO_COOKIE="你复制的完整Cookie值"')
        return False
    
    print(f"✅ WEIBO_COOKIE已配置 (长度: {len(weibo_cookie)} 字符)")
    
    # 测试搜索API
    print("\n测试微博搜索API连接...")
    
    try:
        # 微博搜索API参数
        search_keyword = "测试"
        search_type = "1"  # 综合搜索
        containerid = f"100103type={search_type}&q={search_keyword}"
        
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {
            "containerid": containerid,
            "page_type": "searchall",
            "page": 1,
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
            "Cookie": weibo_cookie,
            "Origin": "https://m.weibo.cn",
            "Referer": "https://m.weibo.cn",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        print(f"请求URL: {url}")
        print(f"搜索关键词: {search_keyword}")
        print(f"请求参数: {params}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # 分析响应结构
                    print(f"✅ API响应成功")
                    print(f"响应包含 'ok' 字段: {'ok' in result}")
                    print(f"响应包含 'data' 字段: {'data' in result}")
                    
                    if 'data' in result:
                        data = result['data']
                        print(f"data包含 'cards' 字段: {'cards' in data}")
                        
                        if 'cards' in data:
                            cards = data['cards']
                            print(f"cards数组长度: {len(cards)}")
                            
                            # 查找微博内容卡片
                            content_cards = []
                            for card in cards:
                                if card.get('card_type') == 9:  # 微博内容卡片
                                    content_cards.append(card)
                            
                            print(f"找到微博内容卡片: {len(content_cards)}个")
                            
                            if content_cards:
                                # 分析第一个内容卡片
                                first_card = content_cards[0]
                                mblog = first_card.get('mblog', {})
                                
                                if mblog:
                                    print(f"\n第一条微博信息:")
                                    print(f"  ID: {mblog.get('id', 'N/A')}")
                                    print(f"  内容: {mblog.get('text', 'N/A')[:100]}...")
                                    print(f"  作者: {mblog.get('user', {}).get('screen_name', 'N/A')}")
                                    print(f"  发布时间: {mblog.get('created_at', 'N/A')}")
                                    print(f"  点赞数: {mblog.get('attitudes_count', 0)}")
                                    print(f"  评论数: {mblog.get('comments_count', 0)}")
                                    print(f"  转发数: {mblog.get('reposts_count', 0)}")
                                    
                                    print("✅ 微博搜索API测试成功，数据结构正常")
                                    return True
                            else:
                                print("⚠️  API响应正常，但未找到微博内容卡片")
                                print("可能原因：关键词无结果或需要登录")
                        else:
                            print("❌ 响应data中无cards字段")
                    else:
                        print("❌ 响应中无data字段")
                        
                    # 如果有错误信息，显示出来
                    if 'msg' in result:
                        print(f"API消息: {result['msg']}")
                    
                except json.JSONDecodeError:
                    print("❌ 响应不是有效的JSON格式")
                    print(f"响应内容前200字符: {response.text[:200]}")
                    
            elif response.status_code == 403:
                print("❌ 403 Forbidden - Cookie可能已过期或无效")
                print("请重新获取微博Cookie")
                
            elif response.status_code == 302:
                print("❌ 302 重定向 - 可能需要登录验证")
                print("请检查Cookie是否包含完整的登录信息")
                
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
            
            return False
            
    except httpx.TimeoutException:
        print("❌ 请求超时，网络连接可能有问题")
        return False
    except Exception as e:
        print(f"❌ API测试失败: {str(e)}")
        return False

async def test_different_search_types():
    """测试不同搜索类型"""
    print("\n=== 测试不同搜索类型 ===")
    
    weibo_cookie = os.getenv("WEIBO_COOKIE", "")
    if not weibo_cookie:
        print("跳过：WEIBO_COOKIE未配置")
        return
    
    search_types = {
        "综合": "1",
        "实时": "61", 
        "热门": "60",
        "视频": "64"
    }
    
    search_keyword = "区块链"
    
    for type_name, type_value in search_types.items():
        print(f"\n测试 {type_name} 搜索...")
        
        try:
            containerid = f"100103type={type_value}&q={search_keyword}"
            url = "https://m.weibo.cn/api/container/getIndex"
            params = {
                "containerid": containerid,
                "page_type": "searchall",
                "page": 1,
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
                "Cookie": weibo_cookie,
                "Origin": "https://m.weibo.cn", 
                "Referer": "https://m.weibo.cn",
                "Accept": "application/json, text/plain, */*",
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    data = result.get('data', {})
                    cards = data.get('cards', [])
                    
                    content_count = sum(1 for card in cards if card.get('card_type') == 9)
                    print(f"  {type_name}: ✅ 成功，找到 {content_count} 条内容")
                else:
                    print(f"  {type_name}: ❌ 失败，状态码 {response.status_code}")
                    
        except Exception as e:
            print(f"  {type_name}: ❌ 异常 {str(e)}")

async def main():
    """主测试函数"""
    print("开始微博API直接连接测试\n")
    
    # 基本API测试
    api_success = await test_weibo_api_direct()
    
    if api_success:
        # 如果基本测试成功，测试不同搜索类型
        await test_different_search_types()
    
    print("\n=== 测试总结 ===")
    
    weibo_cookie = os.getenv("WEIBO_COOKIE", "")
    if not weibo_cookie:
        print("❌ 需要配置WEIBO_COOKIE才能进行真实测试")
        print("\n快速配置步骤:")
        print("1. 打开浏览器访问 https://m.weibo.cn")
        print("2. 登录微博账号")
        print("3. 按F12打开开发者工具")
        print("4. 切换到Network标签")
        print("5. 刷新页面")
        print("6. 点击任意请求，在Request Headers中找到Cookie")
        print("7. 复制Cookie值到.env文件:")
        print('   WEIBO_COOKIE="你的Cookie值"')
    elif api_success:
        print("✅ 微博API连接测试成功")
        print("✅ 环境已就绪，可以进行真实爬取测试")
    else:
        print("❌ 微博API连接失败，请检查Cookie是否有效")
    
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(main())