"""
简化的微博平台真实测试脚本
直接测试环境配置和基本功能
"""
import os
import sys
import asyncio

# 设置正确的导入路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, 'src')

# 将src路径添加到系统路径的最前面
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 设置PYTHONPATH环境变量
os.environ['PYTHONPATH'] = src_path + ':' + os.environ.get('PYTHONPATH', '')

def test_environment_setup():
    """测试环境配置"""
    print("=== 微博平台环境配置验证 ===")
    
    # 检查环境变量
    weibo_cookie = os.getenv("WEIBO_COOKIE", "")
    weibo_search_type = os.getenv("WEIBO_SEARCH_TYPE", "综合")
    weibo_max_pages = os.getenv("WEIBO_MAX_PAGES", "10")
    weibo_rate_limit = os.getenv("WEIBO_RATE_LIMIT", "60")
    weibo_enabled = os.getenv("WEIBO_ENABLED", "true")
    mediacrawler_path = os.getenv("MEDIACRAWLER_PATH", "./mediacrawler")
    
    print(f"WEIBO_COOKIE: {'✅ 已配置 (长度: {len(weibo_cookie)})' if weibo_cookie else '❌ 未配置'}")
    print(f"WEIBO_SEARCH_TYPE: {weibo_search_type}")
    print(f"WEIBO_MAX_PAGES: {weibo_max_pages}")
    print(f"WEIBO_RATE_LIMIT: {weibo_rate_limit}")
    print(f"WEIBO_ENABLED: {weibo_enabled}")
    print(f"MEDIACRAWLER_PATH: {mediacrawler_path}")
    
    # 检查MediaCrawler路径
    mediacrawler_exists = os.path.exists(mediacrawler_path)
    print(f"MediaCrawler目录: {'✅ 存在' if mediacrawler_exists else '❌ 不存在'}")
    
    if mediacrawler_exists:
        weibo_client_path = os.path.join(mediacrawler_path, "media_platform", "weibo", "client.py")
        weibo_field_path = os.path.join(mediacrawler_path, "media_platform", "weibo", "field.py")
        print(f"微博客户端文件: {'✅ 存在' if os.path.exists(weibo_client_path) else '❌ 不存在'}")
        print(f"微博字段文件: {'✅ 存在' if os.path.exists(weibo_field_path) else '❌ 不存在'}")
    
    # 检查httpx依赖
    try:
        import httpx
        print(f"httpx库: ✅ 已安装 (版本: {httpx.__version__})")
    except ImportError:
        print("httpx库: ❌ 未安装")
    
    return weibo_cookie, mediacrawler_exists

def test_weibo_platform_import():
    """测试WeiboPlatform导入"""
    print("\n=== WeiboPlatform导入测试 ===")
    
    try:
        # 尝试导入WeiboPlatform
        import sys
        import os
        
        # 确保src路径在系统路径中
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        src_path = os.path.join(project_root, 'src')
        
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        from crawler.platforms.weibo_platform import WeiboPlatform
        print("✅ WeiboPlatform导入成功")
        
        # 创建实例
        platform = WeiboPlatform()
        print("✅ WeiboPlatform实例创建成功")
        
        # 检查平台名称
        platform_name = platform.get_platform_name()
        print(f"✅ 平台名称: {platform_name.value}")
        
        return platform
        
    except Exception as e:
        print(f"❌ WeiboPlatform导入失败: {str(e)}")
        print(f"当前Python路径: {sys.path[:3]}...")
        return None

async def test_basic_functionality(platform, has_cookie):
    """测试基本功能"""
    print("\n=== 基本功能测试 ===")
    
    if not platform:
        print("❌ 无平台实例，跳过功能测试")
        return
    
    # 测试可用性检查
    print("测试平台可用性...")
    try:
        is_available = await platform.is_available()
        print(f"平台可用性: {'✅ 可用' if is_available else '❌ 不可用 (可能Cookie未配置或已过期)'}")
        
        if not has_cookie:
            print("⚠️  WEIBO_COOKIE未配置，跳过真实爬取测试")
            return
        
        if not is_available:
            print("⚠️  平台不可用，跳过爬取测试")
            return
        
    except Exception as e:
        print(f"❌ 可用性检查失败: {str(e)}")
        return
    
    # 测试简单搜索
    print("\n测试简单搜索功能...")
    try:
        results = await platform.crawl(
            keywords=["测试"],
            max_count=2
        )
        
        print(f"✅ 搜索成功，获得 {len(results)} 条结果")
        
        if results:
            first = results[0]
            print(f"  第一条内容预览: {first.content[:100]}...")
            print(f"  作者: {first.author_name}")
            print(f"  互动: 👍{first.like_count} 💬{first.comment_count} 🔄{first.share_count}")
        
    except Exception as e:
        print(f"❌ 搜索测试失败: {str(e)}")

async def main():
    """主测试函数"""
    print("开始微博平台真实爬取环境测试\n")
    
    # 1. 环境配置测试
    weibo_cookie, mediacrawler_exists = test_environment_setup()
    
    # 2. 导入测试
    platform = test_weibo_platform_import()
    
    # 3. 基本功能测试
    await test_basic_functionality(platform, bool(weibo_cookie))
    
    print("\n=== 测试总结 ===")
    if weibo_cookie:
        print("✅ Cookie已配置，可以进行真实爬取测试")
    else:
        print("⚠️  Cookie未配置，需要获取微博Cookie")
        print("获取Cookie步骤:")
        print("1. 在浏览器中登录 https://m.weibo.cn")
        print("2. 打开开发者工具 -> Network")
        print("3. 刷新页面，找到请求头中的Cookie")
        print("4. 将Cookie添加到.env文件的WEIBO_COOKIE配置中")
    
    if mediacrawler_exists:
        print("✅ MediaCrawler环境正常")
    else:
        print("⚠️  MediaCrawler路径需要检查")
    
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(main())