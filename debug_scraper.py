#!/usr/bin/env python3
"""
民商法爆款文章爬虫 - 调试版本
用于诊断和解决爬虫运行中的问题
"""

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
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG级别以获取更多信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DebugConfigManager:
    """调试配置管理器"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """加载配置文件，包含详细的错误信息"""
        try:
            if not os.path.exists(self.config_file):
                logger.warning(f"配置文件不存在: {self.config_file}，将使用默认配置")
                return self.get_default_config()
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"配置文件内容: {content[:200]}...")
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            logger.error(f"错误位置: 行 {e.lineno}, 列 {e.colno}")
            logger.error(f"错误详情: {e.msg}")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.error(traceback.format_exc())
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """获取默认配置"""
        logger.info("使用默认配置")
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
                "max_pages": 1,  # 调试时只抓取1页
                "max_retries": 3,
                "retry_delay": 2,
                "request_timeout": 10,
                "request_delay_min": 1.0,
                "request_delay_max": 2.0,
                "page_delay_min": 2.0,
                "page_delay_max": 3.0
            },
            "bestseller_criteria": {
                "min_read_count": 1000,  # 调试时降低标准
                "min_interaction_count": 100
            },
            "output": {
                "csv_filename": "debug_bestsellers.csv",
                "encoding": "utf-8-sig",
                "log_filename": "debug_scraper.log"
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def get(self, key_path: str, default=None):
        """获取配置项，支持点号分隔的路径"""
        try:
            keys = key_path.split('.')
            value = self.config
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    logger.debug(f"配置项未找到: {key_path}，返回默认值: {default}")
                    return default
            
            logger.debug(f"获取配置项: {key_path} = {value}")
            return value
        except Exception as e:
            logger.error(f"获取配置项失败: {key_path} - {e}")
            return default

class DebugWebScraper:
    """调试版网络爬虫"""
    
    def __init__(self, config_manager: DebugConfigManager):
        self.config = config_manager
        self.session = requests.Session()
        
        # 设置请求头
        headers = self.config.get('target_platform.headers', {})
        if headers:
            self.session.headers.update(headers)
            logger.debug(f"设置请求头: {headers}")
        else:
            logger.warning("未设置请求头，使用默认请求头")
        
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
        self.max_pages = self.config.get('scraping.max_pages', 1)
        
        # 爆款标准
        self.min_read_count = self.config.get('bestseller_criteria.min_read_count', 10000)
        self.min_interaction_count = self.config.get('bestseller_criteria.min_interaction_count', 1000)
        
        logger.info(f"爬虫初始化完成，目标URL: {self.base_url}")
        logger.info(f"选择器配置: {self.selectors}")
        
    def test_connection(self, url: str = None) -> Dict:
        """测试网络连接"""
        if url is None:
            url = self.base_url
            
        logger.info(f"测试网络连接: {url}")
        result = {
            'success': False,
            'status_code': None,
            'headers': None,
            'content_length': 0,
            'error': None,
            'response_time': 0
        }
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=self.request_timeout)
            end_time = time.time()
            
            result['response_time'] = end_time - start_time
            result['status_code'] = response.status_code
            result['headers'] = dict(response.headers)
            result['content_length'] = len(response.text)
            result['success'] = True
            
            logger.info(f"连接测试成功 - 状态码: {response.status_code}, 响应时间: {result['response_time']:.2f}s, 内容长度: {result['content_length']}")
            
            # 检查响应内容
            if response.status_code == 200:
                logger.debug(f"响应内容前200字符: {response.text[:200]}...")
            else:
                logger.warning(f"HTTP状态码异常: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            result['error'] = str(e)
            logger.error(f"连接测试失败: {e}")
            logger.error(traceback.format_exc())
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"连接测试异常: {e}")
            logger.error(traceback.format_exc())
        
        return result
    
    def analyze_page_structure(self, url: str) -> Dict:
        """分析页面结构，帮助选择器配置"""
        logger.info(f"分析页面结构: {url}")
        result = {
            'success': False,
            'title': None,
            'all_links': [],
            'article_links': [],
            'suggested_selectors': {},
            'error': None
        }
        
        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            result['title'] = soup.title.string if soup.title else None
            
            # 获取所有链接
            all_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                all_links.append({
                    'href': href,
                    'text': text,
                    'class': link.get('class', []),
                    'id': link.get('id', '')
                })
            result['all_links'] = all_links
            
            # 智能识别文章链接
            article_links = []
            common_patterns = ['article', 'post', 'news', 'blog', 'content']
            
            for link in all_links:
                href = link['href'].lower()
                text = link['text'].lower()
                link_classes = [cls.lower() for cls in link['class']] if link['class'] else []
                link_id = link['id'].lower()
                
                # 检查是否匹配常见模式
                if any(pattern in href or pattern in text or any(pattern in cls for cls in link_classes) or pattern in link_id for pattern in common_patterns):
                    article_links.append(link)
            
            result['article_links'] = article_links
            
            # 生成建议的选择器
            suggested_selectors = {}
            if article_links:
                # 基于class的建议
                class_counts = {}
                for link in article_links:
                    for cls in link['class']:
                        class_counts[cls] = class_counts.get(cls, 0) + 1
                
                if class_counts:
                    most_common_class = max(class_counts, key=class_counts.get)
                    suggested_selectors['article_links'] = f"a.{most_common_class}"
                
                # 基于其他元素的建议
                suggested_selectors['title'] = "h1, h2, .title, .post-title, .article-title"
                suggested_selectors['author'] = ".author, .byline, .writer, .post-author"
                suggested_selectors['publish_time'] = ".date, .time, .publish-date, .post-date"
                suggested_selectors['read_count'] = ".read, .views, .read-count, .view-count"
                suggested_selectors['like_count'] = ".like, .likes, .thumb, .vote"
                suggested_selectors['collect_count'] = ".collect, .bookmark, .favorite"
                suggested_selectors['summary'] = ".summary, .excerpt, .description, .post-content"
            
            result['suggested_selectors'] = suggested_selectors
            result['success'] = True
            
            logger.info(f"页面分析完成 - 标题: {result['title']}")
            logger.info(f"发现文章链接: {len(article_links)} 个")
            logger.info(f"建议的选择器: {suggested_selectors}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"页面结构分析失败: {e}")
            logger.error(traceback.format_exc())
        
        return result
    
    def test_selectors(self, url: str, selectors: Dict) -> Dict:
        """测试选择器是否有效"""
        logger.info(f"测试选择器: {url}")
        result = {
            'success': False,
            'selector_results': {},
            'error': None
        }
        
        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            selector_results = {}
            
            for field, selector in selectors.items():
                try:
                    elements = soup.select(selector)
                    selector_results[field] = {
                        'selector': selector,
                        'found_elements': len(elements),
                        'sample_text': elements[0].get_text(strip=True) if elements else None,
                        'status': 'found' if elements else 'not_found'
                    }
                    
                    if elements:
                        logger.info(f"选择器测试成功 - {field}: {selector} (找到 {len(elements)} 个元素)")
                        if len(elements) > 0:
                            logger.debug(f"示例内容: {elements[0].get_text(strip=True)[:100]}...")
                    else:
                        logger.warning(f"选择器未找到元素 - {field}: {selector}")
                        
                except Exception as e:
                    selector_results[field] = {
                        'selector': selector,
                        'found_elements': 0,
                        'error': str(e),
                        'status': 'error'
                    }
                    logger.error(f"选择器测试错误 - {field}: {selector} - {e}")
            
            result['selector_results'] = selector_results
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"选择器测试失败: {e}")
            logger.error(traceback.format_exc())
        
        return result
    
    def make_request(self, url: str, timeout: int = None) -> Optional[requests.Response]:
        """发送HTTP请求，包含详细的错误处理"""
        if timeout is None:
            timeout = self.request_timeout
            
        logger.info(f"开始请求: {url}")
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"请求尝试 {attempt + 1}/{self.max_retries}: {url}")
                start_time = time.time()
                
                response = self.session.get(url, timeout=timeout)
                response_time = time.time() - start_time
                
                logger.info(f"请求成功 - 状态码: {response.status_code}, 响应时间: {response_time:.2f}s, URL: {url}")
                
                if response.status_code != 200:
                    logger.warning(f"非200状态码: {response.status_code} for {url}")
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"请求最终超时: {url}")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"连接最终失败: {url}")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP错误: {url} - {e}")
                logger.error(f"响应状态码: {response.status_code if 'response' in locals() else '未知'}")
                return None
                
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                logger.error(f"异常类型: {type(e).__name__}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {url}")
                    return None
                    
            except Exception as e:
                logger.error(f"未预期的异常 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                logger.error(traceback.format_exc())
                return None
        
        return None
    
    def fetch_article_links(self, page_url: str) -> List[str]:
        """获取文章列表页中的详情页链接 - 调试版本"""
        logger.info(f"开始获取文章列表: {page_url}")
        
        response = self.make_request(page_url)
        if not response:
            logger.error(f"获取文章列表失败: {page_url}")
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.debug(f"页面HTML长度: {len(response.text)} 字符")
            
            selector = self.selectors.get('article_links', 'a.article-link')
            logger.debug(f"使用选择器: {selector}")
            
            links = []
            elements = soup.select(selector)
            logger.info(f"选择器找到 {len(elements)} 个元素")
            
            for i, a in enumerate(elements):
                href = a.get('href')
                text = a.get_text(strip=True)
                
                logger.debug(f"链接 {i+1}: href={href}, text={text[:50]}...")
                
                if href:
                    # 处理相对URL
                    full_url = urljoin(page_url, href)
                    links.append(full_url)
                    logger.debug(f"添加链接: {full_url}")
                else:
                    logger.warning(f"链接 {i+1} 没有href属性")
            
            logger.info(f"找到 {len(links)} 个有效文章链接")
            
            if not links:
                logger.warning(f"未找到任何有效链接，选择器可能不正确: {selector}")
                # 尝试分析页面结构
                structure_analysis = self.analyze_page_structure(page_url)
                if structure_analysis['success'] and structure_analysis['suggested_selectors']:
                    logger.info(f"建议尝试的选择器: {structure_analysis['suggested_selectors']}")
            
            return links
            
        except Exception as e:
            logger.error(f"解析列表页失败: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def parse_article_detail(self, detail_url: str) -> Optional[Dict]:
        """解析单篇文章详情页，提取关键信息 - 调试版本"""
        logger.info(f"开始解析文章详情: {detail_url}")
        
        response = self.make_request(detail_url)
        if not response:
            logger.error(f"获取文章详情失败: {detail_url}")
            return None
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.debug(f"详情页HTML长度: {len(response.text)} 字符")
            
            # 提取数据
            title = self.extract_text(soup, 'title')
            author = self.extract_text(soup, 'author')
            publish_time = self.extract_text(soup, 'publish_time')
            read_count = self.extract_number(soup, 'read_count')
            like_count = self.extract_number(soup, 'like_count')
            collect_count = self.extract_number(soup, 'collect_count')
            content_summary = self.extract_text(soup, 'summary', max_length=200)
            
            logger.debug(f"提取的数据 - 标题: {title[:50]}..., 作者: {author}, 发布时间: {publish_time}")
            logger.debug(f"统计数据 - 阅读: {read_count}, 点赞: {like_count}, 收藏: {collect_count}")
            
            # 数据验证
            if not title:
                logger.warning(f"文章标题为空，跳过: {detail_url}")
                return None
            
            # 判断是否为爆款
            interaction_count = like_count + collect_count
            is_bestseller = self.is_bestseller(read_count, interaction_count)
            
            logger.info(f"文章分析 - 标题: {title[:30]}..., 阅读量: {read_count}, 互动: {interaction_count}, 爆款: {is_bestseller}")
            
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
            
            return article_data if is_bestseller else None
            
        except Exception as e:
            logger.error(f"解析详情页失败 {detail_url}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def extract_text(self, soup: BeautifulSoup, field: str, max_length: int = None) -> str:
        """提取文本内容 - 调试版本"""
        selector = self.selectors.get(field)
        if not selector:
            logger.warning(f"未找到字段 {field} 的选择器配置")
            return ''
        
        try:
            element = soup.select_one(selector)
            if element:
                text = element.text.strip()
                if max_length and len(text) > max_length:
                    text = text[:max_length] + '...'
                logger.debug(f"提取文本 - {field}: {selector} -> {text[:50]}...")
                return text
            else:
                logger.debug(f"未找到元素 - {field}: {selector}")
                return ''
        except Exception as e:
            logger.error(f"提取文本失败 - {field}: {selector} - {e}")
            return ''
    
    def extract_number(self, soup: BeautifulSoup, field: str) -> int:
        """提取数字内容 - 调试版本"""
        selector = self.selectors.get(field)
        if not selector:
            logger.warning(f"未找到字段 {field} 的选择器配置")
            return 0
        
        try:
            element = soup.select_one(selector)
            if element:
                text = element.text.strip().replace(',', '')
                number = int(text) if text.isdigit() else 0
                logger.debug(f"提取数字 - {field}: {selector} -> {text} -> {number}")
                return number
            else:
                logger.debug(f"未找到数字元素 - {field}: {selector}")
                return 0
        except (ValueError, AttributeError) as e:
            logger.warning(f"数字转换失败 - {field}: {selector} - {e}")
            return 0
        except Exception as e:
            logger.error(f"提取数字失败 - {field}: {selector} - {e}")
            return 0
    
    def is_bestseller(self, read_count: int, interaction_count: int) -> bool:
        """判断是否为爆款文章 - 调试版本"""
        result = (read_count > self.min_read_count) and (interaction_count > self.min_interaction_count)
        logger.debug(f"爆款判断 - 阅读: {read_count} > {self.min_read_count} = {read_count > self.min_read_count}, "
                    f"互动: {interaction_count} > {self.min_interaction_count} = {interaction_count > self.min_interaction_count}, "
                    f"结果: {result}")
        return result
    
    def fetch_multiple_pages(self, base_url: str = None, max_pages: int = None) -> List[str]:
        """抓取多页文章链接 - 调试版本"""
        if base_url is None:
            base_url = self.base_url
        if max_pages is None:
            max_pages = self.max_pages
            
        logger.info(f"开始抓取多页文章，基础URL: {base_url}, 最大页数: {max_pages}")
        all_links = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"抓取第 {page} 页")
            
            # 根据实际网站的翻页URL格式调整
            page_url = f"{base_url}?page={page}" if page > 1 else base_url
            logger.debug(f"第 {page} 页URL: {page_url}")
            
            links = self.fetch_article_links(page_url)
            if not links:
                logger.warning(f"第 {page} 页无文章，停止翻页")
                break
                
            all_links.extend(links)
            logger.info(f"第 {page} 页获取到 {len(links)} 个链接，总计: {len(all_links)}")
            
            # 随机延迟，避免被封
            delay = random.uniform(self.page_delay_min, self.page_delay_max)
            logger.debug(f"等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)
            
        logger.info(f"多页抓取完成，总共获取 {len(all_links)} 篇文章链接")
        return all_links


def debug_save_to_csv(data: List[Dict], filename: str, encoding: str = 'utf-8-sig') -> bool:
    """保存数据到CSV文件 - 调试版本"""
    logger.info(f"开始保存数据到CSV文件: {filename}")
    
    if not data:
        logger.warning("无数据可保存")
        return False
    
    try:
        # 确保目录存在
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"数据条数: {len(data)}")
        if data:
            logger.debug(f"数据字段: {list(data[0].keys())}")
            logger.debug(f"数据示例: {data[0]}")
        
        with open(filename, mode='w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"成功保存 {len(data)} 条记录到 {filename}")
        return True
        
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")
        logger.error(traceback.format_exc())
        return False


def run_diagnostics():
    """运行完整的诊断测试"""
    print("=" * 60)
    print("🕷️ 民商法爆款文章爬虫 - 诊断模式")
    print("=" * 60)
    
    # 初始化配置管理器
    config_manager = DebugConfigManager()
    logger.info("配置管理器初始化完成")
    
    # 初始化爬虫
    scraper = DebugWebScraper(config_manager)
    logger.info("调试爬虫初始化完成")
    
    # 1. 测试网络连接
    print("\n1️⃣ 测试网络连接...")
    connection_test = scraper.test_connection()
    if connection_test['success']:
        print(f"✅ 网络连接正常")
        print(f"   状态码: {connection_test['status_code']}")
        print(f"   响应时间: {connection_test['response_time']:.2f}秒")
        print(f"   内容长度: {connection_test['content_length']}字符")
    else:
        print(f"❌ 网络连接失败")
        print(f"   错误: {connection_test['error']}")
        return False
    
    # 2. 分析页面结构
    print("\n2️⃣ 分析页面结构...")
    structure_analysis = scraper.analyze_page_structure(scraper.base_url)
    if structure_analysis['success']:
        print(f"✅ 页面结构分析完成")
        print(f"   页面标题: {structure_analysis['title']}")
        print(f"   总链接数: {len(structure_analysis['all_links'])}")
        print(f"   文章链接数: {len(structure_analysis['article_links'])}")
        
        if structure_analysis['suggested_selectors']:
            print(f"   建议的选择器:")
            for field, selector in structure_analysis['suggested_selectors'].items():
                print(f"     {field}: {selector}")
    else:
        print(f"❌ 页面结构分析失败")
        print(f"   错误: {structure_analysis['error']}")
    
    # 3. 测试当前选择器
    print("\n3️⃣ 测试当前选择器配置...")
    selector_test = scraper.test_selectors(scraper.base_url, scraper.selectors)
    if selector_test['success']:
        print(f"✅ 选择器测试完成")
        for field, result in selector_test['selector_results'].items():
            status_icon = "✅" if result['status'] == 'found' else "❌"
            print(f"   {status_icon} {field}: {result['selector']}")
            print(f"      找到元素: {result['found_elements']}个")
            if result['sample_text']:
                print(f"      示例内容: {result['sample_text'][:50]}...")
            if result['status'] == 'error':
                print(f"      错误: {result.get('error', '未知错误')}")
    else:
        print(f"❌ 选择器测试失败")
        print(f"   错误: {selector_test['error']}")
    
    # 4. 运行小规模爬取测试
    print("\n4️⃣ 运行小规模爬取测试...")
    try:
        # 只抓取一页，降低标准
        article_links = scraper.fetch_multiple_pages(max_pages=1)
        print(f"✅ 爬取测试完成")
        print(f"   获取文章链接: {len(article_links)}个")
        
        if article_links:
            print(f"   前3个链接:")
            for i, link in enumerate(article_links[:3]):
                print(f"     {i+1}. {link}")
            
            # 测试解析第一个文章
            print(f"\n   测试解析第一个文章...")
            first_article = scraper.parse_article_detail(article_links[0])
            if first_article:
                print(f"✅ 文章解析成功")
                print(f"   标题: {first_article['title'][:50]}...")
                print(f"   作者: {first_article['author']}")
                print(f"   阅读量: {first_article['read_count']}")
                print(f"   是否为爆款: {first_article['is_bestseller']}")
            else:
                print(f"⚠️ 文章解析失败或不符合爆款标准")
        else:
            print(f"⚠️ 未获取到任何文章链接")
            
    except Exception as e:
        print(f"❌ 爬取测试失败: {e}")
        logger.error(traceback.format_exc())
    
    print("\n" + "=" * 60)
    print("🔍 诊断完成！请查看日志文件获取详细信息:")
    print(f"   日志文件: debug_scraper.log")
    print(f"   结果文件: debug_bestsellers.csv")
    print("=" * 60)
    
    return True


def main():
    """主函数"""
    try:
        run_diagnostics()
    except KeyboardInterrupt:
        print("\n\n用户中断诊断")
    except Exception as e:
        print(f"\n\n诊断过程发生错误: {e}")
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()