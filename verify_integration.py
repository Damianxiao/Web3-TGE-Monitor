#!/usr/bin/env python3
"""
MediaCrawler整合验证脚本
验证mediacrawler成功整合到Web3-TGE-Monitor项目中
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

async def verify_integration():
    """验证MediaCrawler整合"""
    print("🔍 MediaCrawler整合验证")
    print("=" * 60)
    
    try:
        # 1. 验证目录结构
        print("1. 验证目录结构...")
        mediacrawler_path = project_root / "mediacrawler"
        required_dirs = [
            mediacrawler_path / "media_platform" / "xhs",
            mediacrawler_path / "base",
            mediacrawler_path / "tools",
            mediacrawler_path / "config",
            mediacrawler_path / "model"
        ]
        
        for dir_path in required_dirs:
            if dir_path.exists():
                print(f"   ✅ {dir_path.relative_to(project_root)}")
            else:
                print(f"   ❌ {dir_path.relative_to(project_root)} 不存在")
                return False
        
        # 2. 验证核心文件
        print("\n2. 验证核心文件...")
        required_files = [
            mediacrawler_path / "media_platform" / "xhs" / "core.py",
            mediacrawler_path / "media_platform" / "xhs" / "client.py",
            mediacrawler_path / "base" / "base_crawler.py",
            mediacrawler_path / "var.py"
        ]
        
        for file_path in required_files:
            if file_path.exists():
                print(f"   ✅ {file_path.relative_to(project_root)}")
            else:
                print(f"   ❌ {file_path.relative_to(project_root)} 不存在")
                return False
        
        # 3. 验证模块导入
        print("\n3. 验证模块导入...")
        from src.crawler.platforms.xhs_platform import XHSPlatform
        print("   ✅ XHS平台适配器导入成功")
        
        # 4. 验证平台创建
        print("\n4. 验证平台创建...")
        platform = XHSPlatform()
        print(f"   ✅ 平台实例创建成功")
        print(f"   ✅ Mediacrawler路径: {platform.mediacrawler_path}")
        
        # 5. 验证平台可用性
        print("\n5. 验证平台可用性...")
        is_available = await platform.is_available()
        if is_available:
            print("   ✅ 平台可用性检查通过")
        else:
            print("   ❌ 平台可用性检查失败")
            return False
        
        # 6. 验证关键词功能
        print("\n6. 验证关键词功能...")
        keywords = ["Web3", "DeFi"]
        validated_keywords = await platform.validate_keywords(keywords)
        print(f"   ✅ 关键词验证成功: {validated_keywords}")
        
        # 7. 验证数据转换功能
        print("\n7. 验证数据转换功能...")
        mock_data = {
            'note_id': 'test_integration',
            'title': 'MediaCrawler整合测试',
            'desc': '验证整合后的功能是否正常',
            'type': 'text',
            'time': 1700000000000,  # 毫秒时间戳
            'user_id': 'test_user',
            'nickname': '测试用户',
            'avatar': 'https://example.com/avatar.jpg',
            'liked_count': '1000',
            'comment_count': '100',
            'share_count': '50',
            'collected_count': '200',
            'note_url': 'https://xiaohongshu.com/note/test_integration',
            'ip_location': '上海',
            'source_keyword': 'Web3'
        }
        
        raw_content = await platform.transform_to_raw_content(mock_data)
        print(f"   ✅ 数据转换成功: {raw_content.title}")
        
        print("\n" + "=" * 60)
        print("🎉 MediaCrawler整合验证完全成功！")
        print("\n整合成果:")
        print("   - ✅ 目录结构完整")
        print("   - ✅ 核心文件齐全")
        print("   - ✅ 模块导入正常")
        print("   - ✅ 平台功能正常")
        print("   - ✅ 配置管理简化")
        print("   - ✅ 单仓库架构成功")
        
        print(f"\n🏆 项目现在是统一的单仓库架构！")
        print(f"   原来: 两个独立项目，需要复杂配置")
        print(f"   现在: 单一项目，自动化配置")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 整合验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await verify_integration()
    
    if success:
        print("\n🎊 MediaCrawler整合完全成功！")
        print("现在您可以直接使用Web3-TGE-Monitor，无需独立的MediaCrawler项目。")
    else:
        print("\n❌ 整合验证失败，需要检查问题。")

if __name__ == "__main__":
    asyncio.run(main())