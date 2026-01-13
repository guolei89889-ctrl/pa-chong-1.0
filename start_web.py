#!/usr/bin/env python3
"""
民商法爆款文章爬虫 Web 界面启动脚本
"""

import os
import sys
import webbrowser
import time
import threading
from pathlib import Path

def check_dependencies():
    """检查依赖包"""
    try:
        import flask
        import requests
        import bs4
        print("✅ 依赖包检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("正在安装依赖包...")
        os.system("pip install -r requirements.txt")
        return check_dependencies()

def setup_environment():
    """设置运行环境"""
    # 确保必要的文件存在
    files_to_check = ['config.json', 'web_app.py', 'configurable_scraper.py']
    for file in files_to_check:
        if not os.path.exists(file):
            print(f"❌ 缺少必要文件: {file}")
            return False
    
    # 创建必要的目录
    directories = ['templates', 'logs', 'data']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ 环境设置完成")
    return True

def start_web_server():
    """启动Web服务器"""
    try:
        from web_app import app
        
        print("🚀 正在启动Web服务器...")
        print("📍 访问地址: http://localhost:5000")
        print("📝 日志文件: scraper.log")
        print("📊 结果文件: minshangfa_bestsellers.csv")
        print("=" * 50)
        
        # 在新线程中打开浏览器
        def open_browser():
            time.sleep(2)  # 等待服务器启动
            webbrowser.open('http://localhost:5000')
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # 启动Flask应用
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,  # 生产环境关闭debug
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ 启动Web服务器失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    print("=" * 50)
    print("🕷️ 民商法爆款文章爬虫 Web 界面")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 设置环境
    if not setup_environment():
        sys.exit(1)
    
    # 启动Web服务器
    start_web_server()

if __name__ == '__main__':
    main()