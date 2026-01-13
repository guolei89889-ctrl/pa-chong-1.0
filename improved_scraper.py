import requests
from bs4 import BeautifulSoup
import time
import csv
import logging
from typing import List, Dict, Optional
import random
from urllib.parse import urljoin, urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 示例：以某法律公众号/平台为例（需替换为实际目标平台URL和字段）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
TARGET_PLATFORM_URL = 'https://example-law-platform.com/civil-commercial'  # 替换为实际民商法板块URL
OUTPUT_FILE = 'minshangfa_bestsellers.csv'
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 10


class WebScraper:
    def __init__(self, base_url: str, headers: Dict[str, str]):
        self.base_url = base_url
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(headers)
        
    def make_request(self, url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
        """发送HTTP请求，包含重试机制"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {url} - {e}")
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
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
            # 根据实际页面HTML结构调整选择器（示例：假设文章链接在<a class="article-link">中）
            links = []
            for a in soup.select('a.article-link'):
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

            # 根据实际页面HTML结构调整选择器（以下为示例，需替换为真实字段）
            title = self.extract_text(soup, 'h1.article-title')
            author = self.extract_text(soup, '.author-name')
            publish_time = self.extract_text(soup, '.publish-date')
            read_count = self.extract_number(soup, '.read-count')
            like_count = self.extract_number(soup, '.like-count')
            collect_count = self.extract_number(soup, '.collect-count')
            content_summary = self.extract_text(soup, '.article-summary', max_length=200)

            # 数据验证
            if not title:
                logger.warning(f"文章标题为空，跳过: {detail_url}")
                return None

            # 判断是否为爆款（示例条件：阅读量>1万且点赞+收藏>1000）
            is_bestseller = (read_count > 10000) and (like_count + collect_count > 1000)

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

    def extract_text(self, soup: BeautifulSoup, selector: str, max_length: int = None) -> str:
        """提取文本内容"""
        element = soup.select_one(selector)
        if element:
            text = element.text.strip()
            if max_length and len(text) > max_length:
                text = text[:max_length] + '...'
            return text
        return ''

    def extract_number(self, soup: BeautifulSoup, selector: str) -> int:
        """提取数字内容"""
        element = soup.select_one(selector)
        if element:
            try:
                text = element.text.strip().replace(',', '')
                return int(text) if text.isdigit() else 0
            except (ValueError, AttributeError):
                return 0
        return 0

    def fetch_multiple_pages(self, base_url: str, max_pages: int = 5) -> List[str]:
        """抓取多页文章链接"""
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
            delay = random.uniform(1, 3)
            logger.info(f"等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)
            
        logger.info(f"总共获取 {len(all_links)} 篇文章链接")
        return all_links


def save_to_csv(data: List[Dict], filename: str) -> bool:
    """保存数据到CSV文件"""
    if not data:
        logger.warning("无数据可保存")
        return False
        
    try:
        with open(filename, mode='w', newline='', encoding='utf-8-sig') as f:
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
    logger.info("开始执行民商法爆款文章爬虫任务")
    
    scraper = WebScraper(TARGET_PLATFORM_URL, HEADERS)
    
    # 获取文章链接（支持多页）
    article_links = scraper.fetch_multiple_pages(TARGET_PLATFORM_URL, max_pages=3)
    
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
        delay = random.uniform(0.5, 2)
        time.sleep(delay)
    
    # 保存结果
    if bestsellers:
        save_to_csv(bestsellers, OUTPUT_FILE)
        logger.info(f"任务完成！共找到 {len(bestsellers)} 篇爆款文章")
    else:
        logger.warning("未找到符合条件的爆款文章")


if __name__ == '__main__':
    main()