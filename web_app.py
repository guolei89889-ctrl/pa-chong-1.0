from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import threading
import queue
import time
import random
from datetime import datetime
from pathlib import Path

# 导入修复后的爬虫模块
from fixed_scraper import FixedWebScraper, FixedConfigManager, save_to_csv
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局变量
scraping_status = {
    'is_running': False,
    'progress': 0,
    'total_articles': 0,
    'current_article': 0,
    'bestsellers_found': 0,
    'log_messages': [],
    'error': None
}

# 使用列表存储日志，方便调试
global_logs = []
last_articles = []
last_finished_at = None
current_keywords = []
min_content_length = 200

class WebScraperWithProgress(FixedWebScraper):
    """带进度报告的爬虫类"""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.total_articles = 0
        self.current_article = 0
        
    def fetch_multiple_pages(self, base_url=None, max_pages=None):
        """重写方法以支持进度报告"""
        if base_url is None:
            base_url = self.base_url
        if max_pages is None:
            max_pages = self.max_pages
            
        all_links = []
        for page in range(1, max_pages + 1):
            if not scraping_status['is_running']:
                logger.info("爬虫被用户停止")
                break
                
            if page > 1:
                sep = "&" if "?" in base_url else "?"
                page_url = f"{base_url}{sep}page={page}"
            else:
                page_url = base_url
            self.log_message(f"正在抓取第 {page} 页: {page_url}")
            
            links = self.fetch_article_links(page_url)
            if not links:
                self.log_message(f"第 {page} 页无文章，继续尝试下一页")
                continue
                
            all_links.extend(links)
            self.total_articles = len(all_links)
            scraping_status['total_articles'] = self.total_articles
            
            # 随机延迟
            delay = random.uniform(self.page_delay_min, self.page_delay_max)
            time.sleep(delay)
            
        self.log_message(f"总共获取 {len(all_links)} 篇文章链接")
        return all_links
    
    def parse_article_detail(self, detail_url):
        """重写方法以支持进度报告"""
        self.current_article += 1
        scraping_status['current_article'] = self.current_article
        scraping_status['progress'] = int((self.current_article / max(self.total_articles, 1)) * 100)
        
        self.log_message(f"处理文章 {self.current_article}/{self.total_articles}: {detail_url}")
        
        result = super().parse_article_detail(detail_url)
        if result and result.get("is_bestseller"):
            scraping_status['bestsellers_found'] += 1
            self.log_message(f"发现爆款文章: {result['title']}")
        
        return result
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        scraping_status['log_messages'].append(log_entry)
        global_logs.append(log_entry)
        logger.info(message)

def run_scraper():
    """在后台线程中运行爬虫"""
    global scraping_status
    global last_articles, last_finished_at
    scraper = None
    
    try:
        # 立即记录线程启动
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] 正在初始化爬虫..."
        scraping_status['log_messages'].append(log_entry)
        global_logs.append(log_entry)
        
        scraping_status.update({
            'is_running': True,
            'progress': 0,
            'total_articles': 0,
            'current_article': 0,
            'bestsellers_found': 0,
            # 'log_messages': [], # 保留之前的日志
            'error': None
        })
        
        # 初始化配置管理器
        config_manager = FixedConfigManager()
        
        # 初始化爬虫
        scraper = WebScraperWithProgress(config_manager)
        
        scraper.log_message("开始执行民商法爆款文章爬虫任务")
        
        # 获取文章链接
        article_links = scraper.fetch_multiple_pages()
        
        if not article_links:
            scraper.log_message("未获取到任何文章链接，任务结束")
            return
        
        articles = []
        keywords = list(current_keywords)

        for link in article_links:
            if not scraping_status['is_running']:
                scraper.log_message("爬虫被用户停止")
                break

            article_data = scraper.parse_article_detail(link)
            if not article_data:
                continue

            content = (article_data.get('content') or '').strip()
            if len(content) < min_content_length:
                continue

            if keywords:
                haystack = (article_data.get('title') or '') + "\n" + content
                if not any(k in haystack for k in keywords):
                    continue

            articles.append(article_data)
            
            # 控制请求频率
            delay = random.uniform(scraper.request_delay_min, scraper.request_delay_max)
            time.sleep(delay)
        
        csv_filename = config_manager.get('output.csv_filename', 'minshangfa_bestsellers.csv')
        if save_to_csv(articles, csv_filename, encoding=config_manager.get('output.encoding', 'utf-8-sig')):
            if keywords:
                scraper.log_message(f"任务完成！关键词={keywords}，共输出 {len(articles)} 条含全文结果")
            else:
                scraper.log_message(f"任务完成！共输出 {len(articles)} 条含全文结果")
            scraper.log_message(f"结果已保存到: {csv_filename}")
        else:
            scraper.log_message("保存结果失败")

        last_articles = articles
        last_finished_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
    except Exception as e:
        error_msg = f"爬虫执行出错: {str(e)}"
        scraping_status['error'] = error_msg
        
        # 记录错误到日志队列
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] ❌ {error_msg}"
        scraping_status['log_messages'].append(log_entry)
        global_logs.append(log_entry)
        
        if scraper and hasattr(scraper, 'log_message'):
            scraper.log_message(error_msg)
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        scraping_status['is_running'] = False

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_scraping():
    """开始爬虫任务"""
    if scraping_status['is_running']:
        return jsonify({'error': '爬虫已在运行中'})
    
    keywords = []
    if request.is_json and isinstance(request.json, dict):
        raw = (request.json.get('keywords') or '').strip()
        if raw:
            for part in raw.replace('，', ',').replace('、', ',').split(','):
                part = part.strip()
                if not part:
                    continue
                for token in part.split():
                    token = token.strip()
                    if token:
                        keywords.append(token)

    global current_keywords
    current_keywords = keywords

    print("收到启动请求，正在启动线程...")
    
    # 立即添加一条日志，测试日志系统
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if keywords:
        global_logs.append(f"[{timestamp}] 收到启动指令，关键词={keywords}")
    else:
        global_logs.append(f"[{timestamp}] 收到启动指令，未设置关键词")
    
    # 在新线程中启动爬虫
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    print(f"线程已启动: {thread.name}")
    
    return jsonify({'message': '爬虫任务已启动'})

@app.route('/api/stop', methods=['POST'])
def stop_scraping():
    """停止爬虫任务"""
    if not scraping_status['is_running']:
        return jsonify({'error': '爬虫未在运行'})
    
    scraping_status['is_running'] = False
    return jsonify({'message': '爬虫任务已停止'})

@app.route('/api/status')
def get_status():
    """获取爬虫状态"""
    return jsonify(scraping_status)

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """获取或更新配置"""
    config_file = 'config.json'
    
    if request.method == 'GET':
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return jsonify(config_data)
        except Exception as e:
            return jsonify({'error': f'读取配置失败: {str(e)}'})
    
    else:  # POST
        try:
            new_config = request.json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            return jsonify({'message': '配置已更新'})
        except Exception as e:
            return jsonify({'error': f'保存配置失败: {str(e)}'})

@app.route('/api/download')
def download_results():
    """下载结果文件"""
    try:
        config_manager = FixedConfigManager()
        csv_file = config_manager.get('output.csv_filename', 'minshangfa_bestsellers.csv')
        if os.path.exists(csv_file):
            return send_file(csv_file, as_attachment=True)
        return jsonify({'error': '结果文件不存在'})
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'})

@app.route('/api/preview')
def preview_results():
    limit = request.args.get('limit', 20, type=int)
    if limit <= 0:
        limit = 20
    if limit > 200:
        limit = 200

    def to_preview_item(item):
        content = (item.get('content') or '')
        preview = content[:300] + ("..." if len(content) > 300 else "")
        return {
            'title': item.get('title', ''),
            'publish_time': item.get('publish_time', ''),
            'summary': item.get('summary', ''),
            'detail_url': item.get('detail_url', ''),
            'status_code': item.get('status_code', None),
            'error': item.get('error', None),
            'content_length': len(content),
            'content_preview': preview
        }

    if last_articles:
        return jsonify({
            'items': [to_preview_item(x) for x in last_articles[:limit]],
            'total': len(last_articles),
            'finished_at': last_finished_at
        })

    try:
        config_manager = FixedConfigManager()
        csv_file = config_manager.get('output.csv_filename', 'minshangfa_bestsellers.csv')
        if not os.path.exists(csv_file):
            return jsonify({'items': [], 'total': 0, 'finished_at': None})

        import csv
        items = []
        with open(csv_file, 'r', encoding=config_manager.get('output.encoding', 'utf-8-sig'), newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                content = row.get('content', '') or ''
                items.append({
                    'title': row.get('title', ''),
                    'publish_time': row.get('publish_time', ''),
                    'summary': row.get('summary', ''),
                    'detail_url': row.get('detail_url', ''),
                    'status_code': row.get('status_code', ''),
                    'error': row.get('error', ''),
                    'content_length': len(content),
                    'content_preview': (content[:300] + ('...' if len(content) > 300 else ''))
                })
                if len(items) >= limit:
                    break

        return jsonify({'items': items, 'total': None, 'finished_at': None})
    except Exception as e:
        return jsonify({'error': f'预览失败: {str(e)}', 'items': []})

@app.route('/api/logs')
def get_logs():
    """获取日志消息"""
    # 获取参数中的 last_index，实现增量获取
    last_index = request.args.get('last_index', 0, type=int)
    
    current_logs = global_logs[last_index:]
    
    # 打印调试信息
    if current_logs:
        print(f"返回日志: {len(current_logs)} 条, 起始索引: {last_index}")
        
    return jsonify({
        'logs': current_logs,
        'next_index': len(global_logs)
    })

if __name__ == '__main__':
    print("启动民商法爆款文章爬虫Web界面...")
    print("访问 http://localhost:5000 查看界面")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
