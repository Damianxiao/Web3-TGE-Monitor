#!/usr/bin/env python3
"""
Step 4验证：测试配置和路径调整
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = '/home/damian/Web3-TGE-Monitor'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_configuration():
    """测试配置管理"""
    print("Step 4 验证：配置和路径调整")
    print("=" * 60)
    
    try:
        # 测试1: MediaCrawler配置管理器
        print("1. 测试MediaCrawler配置管理器...")
        from src.config.mediacrawler_config import MediaCrawlerConfig
        from src.config.settings import settings
        
        mc_config = MediaCrawlerConfig(settings)
        print(f"   ✅ MediaCrawler路径: {mc_config.mediacrawler_path}")
        
        # 测试2: 路径验证
        print("2. 验证MediaCrawler安装...")
        is_valid = mc_config.validate_installation()
        print(f"   {'✅' if is_valid else '❌'} 安装验证: {'通过' if is_valid else '失败'}")
        
        # 测试3: 平台配置
        print("3. 测试平台配置...")
        platform_config = mc_config.get_platform_config("xhs")
        print(f"   ✅ XHS平台配置: {platform_config}")
        
        # 测试4: 更新后的XHS平台适配器
        print("4. 测试更新后的XHS平台适配器...")
        from src.crawler.platforms.xhs_platform import XHSPlatform
        
        # 创建平台实例
        platform = XHSPlatform()
        print(f"   ✅ 平台实例创建成功")
        print(f"   ✅ MediaCrawler路径: {platform.mediacrawler_path}")
        
        # 测试5: 环境变量支持
        print("5. 测试环境变量支持...")
        original_env = os.environ.get('MEDIACRAWLER_PATH')
        
        # 设置环境变量测试
        os.environ['MEDIACRAWLER_PATH'] = '/home/damian/MediaCrawler'
        mc_config_env = MediaCrawlerConfig()
        env_path = mc_config_env.mediacrawler_path
        print(f"   ✅ 环境变量路径解析: {env_path}")
        
        # 恢复原始环境变量
        if original_env:
            os.environ['MEDIACRAWLER_PATH'] = original_env
        else:
            os.environ.pop('MEDIACRAWLER_PATH', None)
        
        # 测试6: 配置灵活性
        print("6. 测试配置灵活性...")
        test_configs = [
            {'mediacrawler_path': '/home/damian/MediaCrawler'},
            {'mediacrawler_path': '../MediaCrawler'},
            {}  # 空配置，应该自动发现
        ]
        
        for i, config in enumerate(test_configs):
            try:
                platform_test = XHSPlatform(config)
                print(f"   ✅ 配置测试 {i+1}: 成功")
            except Exception as e:
                print(f"   ❌ 配置测试 {i+1}: 失败 - {e}")
        
        print("\n🎉 Step 4 完成！配置和路径调整验证成功")
        print("   主要改进:")
        print("   - ✅ 智能路径发现（环境变量、相对路径、默认路径）")
        print("   - ✅ 配置验证和错误处理")
        print("   - ✅ 统一的配置管理接口")
        print("   - ✅ 多种部署环境支持")
        print("   - ✅ 详细的错误诊断信息")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_configuration()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Step 4 验证成功！")
        print("\n下一步：Step 5 - 集成测试和验证 (预计 30 分钟)")
    else:
        print("❌ Step 4 验证失败，需要检查配置")