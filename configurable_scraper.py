import requests
from bs4 import BeautifulSoup
import time
import csv
import logging
import json
from typing import List, Dict, Optional
import random
from urllib.parse import urljoin, urlparse
from pathlib import Path


class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {self.config_file}")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "target_platform": {
                "base_url": "https://example-law-platform.com/civil-commercial",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                "selectors": {
                    "article_links": "a.article-link",
                    "title": "h1.article-title",
                    "author": ".author-name",
                    "publish_time": ".publish-date",
                    "read_count": ".read-count",
                    "like_count": ".like-count",
                    "collect_count": ".collect-count",
                    "summary": ".article-summary"
                }
            },
            "scraping": {
                "max_pages": 3,
                "max_retries": 3,
                "retry_delay": 2,
                "request_timeout": 10,
                "request_delay_min": 0.5,
                "request_delay_max": 2.0,
                "page_delay_min": 1.0,
                "page_delay_max": 3.0
            },
            "bestseller_criteria": {
                "min_read_count": 10000,
                "min_interaction_count": 1000
            },
            "output": {
                "csv_filename": "minshangfa_bestsellers.csv",
                "encoding": "utf-8-sig",
                "log_filename": "scraper.log"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def get(self, key_path: str, default=None):
        """获取配置项，支持点号分隔的路径"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


class WebScraper:
    """网络爬虫类"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.session = requests.Session()
        
        # 设置请求头
        headers = self.config.get('target_platform.headers', {})
        self.session.headers.update(headers)
        
        # 获取配置参数
        self.base_url = self.config.get('target_platform.base_url')
        self.selectors = self.config.get('target_platform.selectors', {})
        self.max_retries = self.config.get('scraping.max_retries', 3)
        self.retry_delay = self.config.get('scraping.retry_delay', 2)
        self.request_timeout = self.config.get('scraping.request_timeout', 10)
        self.request_delay_min = self.config.get('scraping.request_delay_min', 0.5)
        self.request_delay_max = self.config.get('scraping.request_delay_max', 2.0)
        self.page_delay_min = self.config.get('scraping.page_delay_min', 1.0)
        self.page_delay_max = self.config.get('scraping.page_delay_max', 3.0)
        self.max_pages = self.config.get('scraping.max_pages', 3)
        
        # 爆款标准
        self.min_read_count = self.config.get('bestseller_criteria.min_read_count', 10000)
        self.min_interaction_count = self.config.get('bestseller_criteria.min_interaction_count', 1000)
        
    def setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config.get('logging.level', 'INFO'))
        log_format = self.config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = self.config.get('output.log_filename', 'scraper.log')
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def make_request(self, url: str, timeout: int = None) -> Optional[requests.Response]:
        """发送HTTP请求，包含重试机制"""
        if timeout is None:
            timeout = self.request_timeout
            
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                logger.info(f"请求成功: {url}")
                return response
            except requests.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {url}")
                    return None
        return None
    
    def fetch_article_links(self, page_url: str) -> List[str]:
        """获取文章列表页中的详情页链接"""
        logger.info(f"正在获取文章列表: {page_url}")
        
        response = self.make_request(page_url)
        if not response:
            return []
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            selector = self.selectors.get('article_links', 'a.article-link')
            
            links = []
            for a in soup.select(selector):
                href = a.get('href')
                if href:
                    # 处理相对URL
                    full_url = urljoin(page_url, href)
                    links.append(full_url)
            
            logger.info(f"找到 {len(links)} 篇文章链接")
            return links
            
        except Exception as e:
            logger.error(f"解析列表页失败: {e}")
            return []
    
    def parse_article_detail(self, detail_url: str) -> Optional[Dict]:
        """解析单篇文章详情页，提取关键信息"""
        logger.info(f"正在解析文章详情: {detail_url}")
        
        response = self.make_request(detail_url)
        if not response:
            return None
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取数据
            title = self.extract_text(soup, 'title')
            author = self.extract_text(soup, 'author')
            publish_time = self.extract_text(soup, 'publish_time')
            read_count = self.extract_number(soup, 'read_count')
            like_count = self.extract_number(soup, 'like_count')
            collect_count = self.extract_number(soup, 'collect_count')
            content_summary = self.extract_text(soup, 'summary', max_length=200)
            
            # 数据验证
            if not title:
                logger.warning(f"文章标题为空，跳过: {detail_url}")
                return None
            
            # 判断是否为爆款
            is_bestseller = self.is_bestseller(read_count, like_count + collect_count)
            
            article_data = {
                'title': title,
                'author': author,
                'publish_time': publish_time,
                'read_count': read_count,
                'like_count': like_count,
                'collect_count': collect_count,
                'summary': content_summary,
                'detail_url': detail_url,
                'is_bestseller': is_bestseller
            }
            
            if is_bestseller:
                logger.info(f"发现爆款文章: {title} (阅读量: {read_count}, 互动: {like_count + collect_count})")
            else:
                logger.debug(f"普通文章: {title} (阅读量: {read_count}, 互动: {like_count + collect_count})")
            
            return article_data if is_bestseller else None
            
        except Exception as e:
            logger.error(f"解析详情页失败 {detail_url}: {e}")
            return None
    
    def extract_text(self, soup: BeautifulSoup, field: str, max_length: int = None) -> str:
        """提取文本内容"""
        selector = self.selectors.get(field)
        if not selector:
            logger.warning(f"未找到字段 {field} 的选择器配置")
            return ''
            
        element = soup.select_one(selector)
        if element:
            text = element.text.strip()
            if max_length and len(text) > max_length:
                text = text[:max_length] + '...'
            return text
        return ''
    
    def extract_number(self, soup: BeautifulSoup, field: str) -> int:
        """提取数字内容"""
        selector = self.selectors.get(field)
        if not selector:
            logger.warning(f"未找到字段 {field} 的选择器配置")
            return 0
            
        element = soup.select_one(selector)
        if element:
            try:
                text = element.text.strip().replace(',', '')
                return int(text) if text.isdigit() else 0
            except (ValueError, AttributeError):
                return 0
        return 0
    
    def is_bestseller(self, read_count: int, interaction_count: int) -> bool:
        """判断是否为爆款文章"""
        return (read_count > self.min_read_count) and (interaction_count > self.min_interaction_count)
    
    def fetch_multiple_pages(self, base_url: str = None, max_pages: int = None) -> List[str]:
        """抓取多页文章链接"""
        if base_url is None:
            base_url = self.base_url
        if max_pages is None:
            max_pages = self.max_pages
            
        all_links = []
        for page in range(1, max_pages + 1):
            # 根据实际网站的翻页URL格式调整
            page_url = f"{base_url}?page={page}" if page > 1 else base_url
            logger.info(f"正在抓取第 {page} 页: {page_url}")
            
            links = self.fetch_article_links(page_url)
            if not links:
                logger.warning(f"第 {page} 页无文章，停止翻页")
                break
                
            all_links.extend(links)
            
            # 随机延迟，避免被封
            delay = random.uniform(self.page_delay_min, self.page_delay_max)
            logger.info(f"等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)
            
        logger.info(f"总共获取 {len(all_links)} 篇文章链接")
        return all_links


def save_to_csv(data: List[Dict], filename: str, encoding: str = 'utf-8-sig') -> bool:
    """保存数据到CSV文件"""
    if not data:
        logger.warning("无数据可保存")
        return False
        
    try:
        # 确保目录存在
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, mode='w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"已保存 {len(data)} 条记录到 {filename}")
        return True
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")
        return False


def main():
    """主函数"""
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 设置日志
    global logger
    logger = config_manager.setup_logging()
    
    logger.info("开始执行民商法爆款文章爬虫任务")
    
    # 初始化爬虫
    scraper = WebScraper(config_manager)
    
    # 获取文章链接（支持多页）
    article_links = scraper.fetch_multiple_pages()
    
    if not article_links:
        logger.error("未获取到任何文章链接，任务结束")
        return
    
    # 解析文章详情
    bestsellers = []
    for i, link in enumerate(article_links, 1):
        logger.info(f"处理文章 {i}/{len(article_links)}: {link}")
        
        article_data = scraper.parse_article_detail(link)
        if article_data:
            bestsellers.append(article_data)
        
        # 控制请求频率
        delay = random.uniform(scraper.request_delay_min, scraper.request_delay_max)
        time.sleep(delay)
    
    # 保存结果
    csv_filename = config_manager.get('output.csv_filename', 'minshangfa_bestsellers.csv')
    encoding = config_manager.get('output.encoding', 'utf-8-sig')
    
    if bestsellers:
        save_to_csv(bestsellers, csv_filename, encoding)
        logger.info(f"任务完成！共找到 {len(bestsellers)} 篇爆款文章")
    else:
        logger.warning("未找到符合条件的爆款文章")


if __name__ == '__main__':
    main()