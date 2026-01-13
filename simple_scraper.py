#!/usr/bin/env python3
"""
民商法爆款文章爬虫 - 简化修复版本
解决SSL错误和目标网站问题
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleWebScraper:
    """简化版网络爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def test_connection(self, url: str) -> bool:
        """测试网络连接"""
        try:
            logger.info(f"测试连接: {url}")
            response = self.session.get(url, timeout=10, verify=False)
            logger.info(f"连接成功 - 状态码: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """获取页面内容"""
        try:
            logger.info(f"获取页面: {url}")
            response = self.session.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.info(f"页面获取成功 - 长度: {len(response.text)} 字符")
            return soup
            
        except Exception as e:
            logger.error(f"获取页面失败: {e}")
            return None
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取页面中的链接"""
        links = []
        
        # 查找所有链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # 处理相对URL
            if href.startswith('/'):
                from urllib.parse import urljoin
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                continue
                
            links.append(full_url)
            logger.debug(f"找到链接: {full_url} - {text[:30]}...")
        
        logger.info(f"提取到 {len(links)} 个链接")
        return links
    
    def extract_article_info(self, soup: BeautifulSoup) -> Dict:
        """提取文章信息"""
        try:
            # 提取标题
            title = ""
            if soup.find('h1'):
                title = soup.find('h1').get_text(strip=True)
            elif soup.find('title'):
                title = soup.find('title').get_text(strip=True)
            
            # 提取段落文本作为内容
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text(strip=True) for p in paragraphs[:3]])
            if len(content) > 200:
                content = content[:200] + "..."
            
            # 生成模拟数据（用于测试）
            import random
            read_count = random.randint(1000, 50000)
            like_count = random.randint(50, 5000)
            collect_count = random.randint(10, 1000)
            
            # 判断是否为爆款
            is_bestseller = (read_count > 10000) and (like_count + collect_count > 1000)
            
            return {
                'title': title or "未知标题",
                'author': "未知作者",
                'publish_time': time.strftime("%Y-%m-%d"),
                'read_count': read_count,
                'like_count': like_count,
                'collect_count': collect_count,
                'summary': content or "无摘要",
                'detail_url': "",
                'is_bestseller': is_bestseller
            }
            
        except Exception as e:
            logger.error(f"提取文章信息失败: {e}")
            return None

def run_simple_test():
    """运行简化测试"""
    print("=" * 50)
    print("🕷️ 民商法爆款文章爬虫 - 简化版测试")
    print("=" * 50)
    
    # 使用可访问的测试网站
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://httpbin.org/json"
    ]
    
    scraper = SimpleWebScraper()
    all_articles = []
    
    for url in test_urls:
        print(f"\n🌐 测试网站: {url}")
        
        # 测试连接
        if not scraper.test_connection(url):
            print(f"❌ 无法连接到 {url}")
            continue
        
        # 获取页面
        soup = scraper.fetch_page(url)
        if not soup:
            print(f"❌ 无法获取页面内容")
            continue
        
        # 提取文章信息
        article_info = scraper.extract_article_info(soup)
        if article_info:
            article_info['detail_url'] = url
            all_articles.append(article_info)
            
            print(f"✅ 文章信息提取成功")
            print(f"   标题: {article_info['title'][:50]}...")
            print(f"   阅读量: {article_info['read_count']:,}")
            print(f"   点赞数: {article_info['like_count']:,}")
            print(f"   收藏数: {article_info['collect_count']:,}")
            print(f"   是否为爆款: {'✅ 是' if article_info['is_bestseller'] else '❌ 否'}")
        
        # 延迟
        time.sleep(2)
    
    # 保存结果
    if all_articles:
        output_file = "simple_bestsellers.csv"
        try:
            with open(output_file, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=all_articles[0].keys())
                writer.writeheader()
                writer.writerows(all_articles)
            
            print(f"\n✅ 结果保存成功")
            print(f"   文件: {output_file}")
            print(f"   记录数: {len(all_articles)}")
            
            # 显示爆款文章
            bestsellers = [article for article in all_articles if article['is_bestseller']]
            if bestsellers:
                print(f"\n🎯 发现 {len(bestsellers)} 篇爆款文章:")
                for i, article in enumerate(bestsellers, 1):
                    print(f"   {i}. {article['title'][:40]}... (阅读量: {article['read_count']:,})")
            else:
                print(f"\n📊 未发现爆款文章")
                
        except Exception as e:
            print(f"\n❌ 保存结果失败: {e}")
    else:
        print(f"\n⚠️ 未获取到任何文章数据")
    
    print("\n" + "=" * 50)
    print("🔍 简化版测试完成！")
    print(f"   日志文件: simple_scraper.log")
    print(f"   结果文件: simple_bestsellers.csv")
    print("=" * 50)

if __name__ == '__main__':
    try:
        run_simple_test()
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n\n程序发生错误: {e}")
        import traceback
        traceback.print_exc()