"""
WSL环境下的二维码登录适配器
为WSL环境提供专门的二维码显示和登录支持
"""
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()


class WSLQRCodeAdapter:
    """WSL环境二维码适配器"""
    
    def __init__(self):
        self.is_wsl = self._detect_wsl_environment()
        self.desktop_path = self._get_windows_desktop_path() if self.is_wsl else None
        
    def _detect_wsl_environment(self) -> bool:
        """检测是否在WSL环境中运行"""
        try:
            # 检查 /proc/version 文件中是否包含 WSL 或 Microsoft
            if os.path.exists('/proc/version'):
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    if 'microsoft' in version_info or 'wsl' in version_info:
                        return True
            
            # 检查环境变量
            wsl_distro = os.environ.get('WSL_DISTRO_NAME')
            if wsl_distro:
                return True
                
            # 检查是否在Linux上但有Windows文件系统挂载
            if platform.system() == 'Linux' and os.path.exists('/mnt/c'):
                return True
                
            return False
        except Exception:
            return False
    
    def _get_windows_desktop_path(self) -> Optional[str]:
        """获取Windows桌面路径"""
        if not self.is_wsl:
            return None
            
        try:
            # 尝试从环境变量获取用户名
            username = os.environ.get('USER', os.environ.get('USERNAME', ''))
            if username:
                user_desktop = f'/mnt/c/Users/{username}/Desktop'
                if os.path.exists(user_desktop):
                    return user_desktop
            
            # 查找第一个可用的用户桌面
            users_dir = '/mnt/c/Users'
            if os.path.exists(users_dir):
                for user_folder in os.listdir(users_dir):
                    desktop_path = os.path.join(users_dir, user_folder, 'Desktop')
                    if os.path.exists(desktop_path) and user_folder not in ['Public', 'Default', 'All Users']:
                        return desktop_path
            
            # 使用Public桌面作为最后选择
            public_desktop = '/mnt/c/Users/Public/Desktop'
            if os.path.exists(public_desktop):
                return public_desktop
                
            return None
        except Exception as e:
            logger.error("获取Windows桌面路径失败", error=str(e))
            return None
    
    def save_qrcode_to_desktop(self, image, filename: str = 'xhs_qrcode.png') -> Optional[str]:
        """保存二维码到Windows桌面"""
        if not self.is_wsl or not self.desktop_path:
            return None
            
        try:
            qr_file_path = os.path.join(self.desktop_path, filename)
            image.save(qr_file_path)
            logger.info(f"二维码已保存到Windows桌面: {qr_file_path}")
            return qr_file_path
        except Exception as e:
            logger.error(f"保存二维码到桌面失败: {e}")
            return None
    
    def save_qrcode_to_temp(self, image, filename: str = 'xhs_qrcode.png') -> str:
        """保存二维码到临时目录"""
        try:
            temp_dir = tempfile.gettempdir()
            qr_file_path = os.path.join(temp_dir, filename)
            image.save(qr_file_path)
            logger.info(f"二维码备份保存到: {qr_file_path}")
            return qr_file_path
        except Exception as e:
            logger.error(f"保存二维码到临时目录失败: {e}")
            return ""
    
    def show_wsl_instructions(self, desktop_path: Optional[str] = None, temp_path: Optional[str] = None):
        """显示WSL环境下的操作指引"""
        print("\n" + "="*60)
        print("🔍 WSL环境检测到 - 二维码登录指引")
        print("="*60)
        
        if desktop_path:
            print(f"✅ 二维码已保存到Windows桌面:")
            print(f"   📁 {desktop_path}")
            print("   👆 请在Windows文件管理器中打开上述文件")
        
        if temp_path:
            print(f"\n📋 备份位置:")
            print(f"   📁 {temp_path}")
        
        print("\n📱 扫码步骤:")
        print("   1. 在Windows中打开保存的二维码图片")
        print("   2. 使用小红书APP扫描二维码")
        print("   3. 完成登录后等待程序继续运行")
        
        print("\n⏰ 等待扫码中... (120秒超时)")
        print("="*60)
    
    def show_ascii_frame(self):
        """显示ASCII艺术边框提示"""
        print("""
        ┌────────────────────────────────────────────────────┐
        │                                                    │
        │  🔐 小红书扫码登录 - WSL环境适配                     │
        │                                                    │
        │  📂 二维码文件已生成，请按以下步骤操作：              │
        │                                                    │
        │  1️⃣  打开Windows文件管理器                          │
        │  2️⃣  找到桌面上的 xhs_qrcode.png 文件               │
        │  3️⃣  双击打开图片                                   │
        │  4️⃣  使用小红书APP扫描二维码                        │
        │                                                    │
        │  ⚠️  如果桌面没有文件，请查看程序输出的备份路径       │
        │                                                    │
        └────────────────────────────────────────────────────┘
        """)
    
    def handle_qrcode_display(self, image) -> None:
        """处理WSL环境下的二维码显示"""
        if not self.is_wsl:
            # 非WSL环境，使用默认显示方式
            try:
                image.show()
            except Exception as e:
                logger.error(f"显示二维码失败: {e}")
            return
        
        # WSL环境处理
        desktop_path = self.save_qrcode_to_desktop(image)
        temp_path = self.save_qrcode_to_temp(image)
        
        # 显示ASCII指引
        self.show_ascii_frame()
        
        # 显示详细指引
        self.show_wsl_instructions(desktop_path, temp_path)
        
        # 额外的终端提示
        self._show_terminal_reminder()
    
    def _show_terminal_reminder(self):
        """显示终端提醒信息"""
        print("\n💡 提示:")
        print("   - 如果无法打开图片，请检查Windows默认图片查看器")
        print("   - 确保小红书APP已安装并可以扫码")
        print("   - 扫码后请保持程序运行，等待登录完成")
        
    def cleanup_qrcode_files(self, filename: str = 'xhs_qrcode.png'):
        """清理生成的二维码文件"""
        try:
            # 清理桌面文件
            if self.desktop_path:
                desktop_file = os.path.join(self.desktop_path, filename)
                if os.path.exists(desktop_file):
                    os.remove(desktop_file)
                    logger.info("已清理桌面二维码文件")
            
            # 清理临时文件
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, filename)
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info("已清理临时二维码文件")
                
        except Exception as e:
            logger.warning(f"清理二维码文件时出错: {e}")


# 全局适配器实例
wsl_qrcode_adapter = WSLQRCodeAdapter()