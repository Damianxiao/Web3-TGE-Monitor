#!/usr/bin/env python3
"""
QR码实时监控脚本
用于WSL环境下监控QR码文件变化并实时更新到Windows桌面
"""

import os
import time
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class QRCodeHandler(FileSystemEventHandler):
    def __init__(self, desktop_path):
        self.desktop_path = desktop_path
        self.last_update = 0
        
    def on_modified(self, event):
        if not event.is_directory and 'xhs_qrcode.png' in event.src_path:
            # 防止重复触发
            current_time = time.time()
            if current_time - self.last_update < 1:
                return
            self.last_update = current_time
            
            try:
                # 复制到Windows桌面
                shutil.copy2(event.src_path, self.desktop_path)
                print(f"QR码已更新到桌面: {self.desktop_path}")
                
                # 显示QR码文件信息
                stat = os.stat(event.src_path)
                print(f"文件大小: {stat.st_size} bytes")
                print(f"修改时间: {time.ctime(stat.st_mtime)}")
                print("请立即扫描新的QR码!")
                
            except Exception as e:
                print(f"复制QR码失败: {e}")

def main():
    # 设置路径
    watch_dir = "/home/damian/Web3-TGE-Monitor/mediacrawler"
    desktop_path = "/mnt/c/Users/19461/Desktop/xhs_qrcode.png"
    
    print("QR码监控服务启动...")
    print(f"监控目录: {watch_dir}")
    print(f"桌面路径: {desktop_path}")
    print("等待QR码更新...")
    
    # 创建事件处理器和观察器
    event_handler = QRCodeHandler(desktop_path)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=False)
    
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n监控服务已停止")
    
    observer.join()

if __name__ == "__main__":
    main()