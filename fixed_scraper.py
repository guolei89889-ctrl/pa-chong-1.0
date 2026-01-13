#!/usr/bin/env python3
"""
民商法爆款文章爬虫 - 修复版本
解决SSL错误和目标网站问题
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
import ssl
import urllib3
import os

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fixed_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FixedConfigManager:
    """修复版配置管理器"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_file):
                logger.warning(f"配置文件不存在: {self.config_file}，将使用默认配置")
                return self.get_default_config()
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """获取默认配置 - 使用可访问的测试网站"""
        return {
            "target_platform": {
                "base_url": "https://httpbin.org/html",  # 使用测试网站
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                "selectors": {
                    "article_links": "a",  # 简化选择器
                    "title": "h1",
                    "author": "p",
                    "publish_time": "p",
                    "read_count": "p",
                    "like_count": "p",
                    "collect_count": "p",
                    "summary": "p"
                }
            },
            "scraping": {
                "max_pages": 1,
                "max_retries": 3,
                "retry_delay": 2,
                "request_timeout": 15,  # 增加超时时间
                "request_delay_min": 2.0,  # 增加延迟
                "request_delay_max": 4.0,
                "page_delay_min": 3.0,
                "page_delay_max": 5.0
            },
            "bestseller_criteria": {
                "min_read_count": 100,  # 降低标准以便测试
                "min_interaction_count": 10
            },
            "output": {
                "csv_filename": "fixed_bestsellers.csv",
                "encoding": "utf-8-sig",
                "log_filename": "fixed_scraper.log"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "network": {
                "verify_ssl": False,  # 禁用SSL验证
                "allow_redirects": True,
                "max_redirects": 5
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
                    return default
            
            return value
        except Exception as e:
            logger.error(f"获取配置项失败: {key_path} - {e}")
            return default

class FixedWebScraper:
    """修复版网络爬虫"""
    
    def __init__(self, config_manager: FixedConfigManager):
        self.config = config_manager
        self.session = requests.Session()
        
        # 设置请求头
        headers = self.config.get('target_platform.headers', {})
        if headers:
            self.session.headers.update(headers)
        
        # 获取网络配置
        self.verify_ssl = self.config.get('network.verify_ssl', False)
        self.allow_redirects = self.config.get('network.allow_redirects', True)
        self.max_redirects = self.config.get('network.max_redirects', 5)
        
        # 获取爬虫配置
        self.base_url = self.config.get('target_platform.base_url')
        self.selectors = self.config.get('target_platform.selectors', {})
        self.max_retries = self.config.get('scraping.max_retries', 3)
        self.retry_delay = self.config.get('scraping.retry_delay', 2)
        self.request_timeout = self.config.get('scraping.request_timeout', 15)
        self.request_delay_min = self.config.get('scraping.request_delay_min', 2.0)
        self.request_delay_max = self.config.get('scraping.request_delay_max', 4.0)
        self.page_delay_min = self.config.get('scraping.page_delay_min', 3.0)
        self.page_delay_max = self.config.get('scraping.page_delay_max', 5.0)
        self.max_pages = self.config.get('scraping.max_pages', 1)
        
        # 爆款标准
        self.min_read_count = self.config.get('bestseller_criteria.min_read_count', 100)
        self.min_interaction_count = self.config.get('bestseller_criteria.min_interaction_count', 10)
        
        logger.info(f"修复版爬虫初始化完成")
        logger.info(f"目标URL: {self.base_url}")
        logger.info(f"SSL验证: {self.verify_ssl}")
        logger.info(f"超时设置: {self.request_timeout}s")
        
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
            response = self.session.get(
                url, 
                timeout=self.request_timeout,
                verify=self.verify_ssl,
                allow_redirects=self.allow_redirects
            )
            end_time = time.time()
            
            result['response_time'] = end_time - start_time
            result['status_code'] = response.status_code
            result['headers'] = dict(response.headers)
            result['content_length'] = len(response.text)
            result['success'] = True
            
            logger.info(f"连接测试成功 - 状态码: {response.status_code}, 响应时间: {result['response_time']:.2f}s")
            
            if response.status_code != 200:
                logger.warning(f"非200状态码: {response.status_code}")
                
        except requests.exceptions.SSLError as e:
            result['error'] = f"SSL错误: {str(e)}"
            logger.error(f"SSL连接失败: {e}")
            logger.info("建议: 设置 verify_ssl=False 或检查证书配置")
            
        except requests.exceptions.ConnectionError as e:
            result['error'] = f"连接错误: {str(e)}"
            logger.error(f"网络连接失败: {e}")
            logger.info("建议: 检查网络连接、代理设置或目标网站是否可访问")
            
        except requests.exceptions.Timeout as e:
            result['error'] = f"超时错误: {str(e)}"
            logger.error(f"请求超时: {e}")
            logger.info("建议: 增加 request_timeout 值或检查网络状况")
            
        except requests.exceptions.RequestException as e:
            result['error'] = f"请求异常: {str(e)}"
            logger.error(f"请求失败: {e}")
            
        except Exception as e:
            result['error'] = f"未预期错误: {str(e)}"
            logger.error(f"连接测试异常: {e}")
            logger.error(traceback.format_exc())
        
        return result
    
    def make_request(self, url: str, timeout: int = None) -> Optional[requests.Response]:
        """发送HTTP请求，包含完整的错误处理"""
        if timeout is None:
            timeout = self.request_timeout
            
        logger.info(f"开始请求: {url}")
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"请求尝试 {attempt + 1}/{self.max_retries}: {url}")
                start_time = time.time()
                
                response = self.session.get(
                    url,
                    timeout=timeout,
                    verify=self.verify_ssl,
                    allow_redirects=self.allow_redirects
                )

                if not response.encoding or response.encoding.lower() == "iso-8859-1":
                    try:
                        response.encoding = response.apparent_encoding or "utf-8"
                    except Exception:
                        response.encoding = "utf-8"

                response_time = time.time() - start_time
                logger.info(f"请求成功 - 状态码: {response.status_code}, 响应时间: {response_time:.2f}s, URL: {url}")
                
                if response.status_code != 200:
                    logger.warning(f"非200状态码: {response.status_code}")
                return response
                
            except requests.exceptions.SSLError as e:
                logger.warning(f"SSL错误 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"SSL连接最终失败: {url}")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"网络连接最终失败: {url}")
                    return None
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"请求最终超时: {url}")
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
        """获取文章列表页中的详情页链接"""
        logger.info(f"开始获取文章列表: {page_url}")

        response = self.make_request(page_url)
        if not response:
            logger.error(f"获取文章列表失败: {page_url}")
            if hasattr(self, "log_message"):
                try:
                    self.log_message(f"获取列表页失败（网络/反爬/超时）：{page_url}")
                except Exception:
                    pass
            return []

        try:
            content_type = response.headers.get("Content-Type", "")
            html_len = len(response.text or "")
            logger.info(f"列表页响应: status={response.status_code}, content-type={content_type}, html_len={html_len}")
            if hasattr(self, "log_message"):
                try:
                    self.log_message(f"列表页响应: {response.status_code}, HTML长度: {html_len}")
                except Exception:
                    pass

            soup = BeautifulSoup(response.text, 'html.parser')
            logger.debug(f"页面HTML长度: {len(response.text)} 字符")

            a_count = len(soup.find_all("a"))
            logger.info(f"页面解析统计: a标签数量={a_count}")
            if hasattr(self, "log_message"):
                try:
                    self.log_message(f"页面解析统计: a标签数量={a_count}")
                except Exception:
                    pass
            
            selector = self.selectors.get('article_links', 'a')
            logger.debug(f"使用选择器: {selector}")
            
            links = []
            elements = soup.select(selector)
            logger.info(f"选择器找到 {len(elements)} 个元素")
            if hasattr(self, "log_message"):
                try:
                    self.log_message(f"选择器命中元素数: {len(elements)}（selector={selector}）")
                except Exception:
                    pass
            
            for i, a in enumerate(elements):
                href = a.get('href')
                text = a.get_text(strip=True)
                
                logger.debug(f"链接 {i+1}: href={href}, text={text[:50]}...")
                
                if href:
                    href = str(href).strip()
                    if href:
                        href = href.split()[0]

                    if href.startswith("https:/") and not href.startswith("https://"):
                        href = "https://" + href[len("https:/"):]
                    if href.startswith("http:/") and not href.startswith("http://"):
                        href = "http://" + href[len("http:/"):]

                    lower_href = href.lower()
                    if any(lower_href.endswith(ext) for ext in (".apk", ".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".pdf", ".zip")):
                        continue

                    # 智能过滤
                    text_len = len(text)
                    href_len = len(href)
                    
                    # 过滤规则
                    if text_len < 4:  # 标题太短
                        logger.debug(f"跳过链接(标题太短): {text[:10]}... - {href[:30]}...")
                        continue
                    if href_len < 10:  # 链接太短
                        logger.debug(f"跳过链接(URL太短): {href}")
                        continue
                    if href.startswith('javascript') or href.startswith('#'):
                        logger.debug(f"跳过链接(无效协议): {href}")
                        continue
                    
                    # 排除常见非新闻链接
                    exclude_keywords = ['登录', '注册', '帮助', '关于', '联系', '反馈', '更多', '首页', '地图', '招聘']
                    if any(kw in text for kw in exclude_keywords):
                        logger.debug(f"跳过链接(关键词排除): {text}")
                        continue

                    # 处理相对URL
                    full_url = urljoin(page_url, href)
                    links.append(full_url)
                    logger.debug(f"添加链接: {full_url}")
                else:
                    logger.warning(f"链接 {i+1} 没有href属性")

                if i < 5 and hasattr(self, "log_message"):
                    try:
                        self.log_message(f"样例链接{i+1}: {text[:30]} | {str(href)[:80]}")
                    except Exception:
                        pass
            
            logger.info(f"找到 {len(links)} 个有效文章链接")
            if hasattr(self, "log_message"):
                try:
                    self.log_message(f"有效文章链接数: {len(links)}")
                except Exception:
                    pass
            
            if not links:
                logger.warning(f"未找到任何有效链接，选择器可能不正确: {selector}")
                # 显示页面结构帮助调试
                self.show_page_structure_help(soup)
                if a_count == 0:
                    logger.info(f"页面没有a标签，将把当前页当作单篇文章处理: {page_url}")
                    if hasattr(self, "log_message"):
                        try:
                            self.log_message(f"页面无链接，按单篇文章处理: {page_url}")
                        except Exception:
                            pass
                    return [page_url]
            
            return links
            
        except Exception as e:
            logger.error(f"解析列表页失败: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def show_page_structure_help(self, soup: BeautifulSoup):
        """显示页面结构帮助信息"""
        logger.info("页面结构分析帮助:")
        
        # 显示所有链接
        all_links = soup.find_all('a', href=True)
        logger.info(f"页面中总共有 {len(all_links)} 个带href的链接")
        
        if len(all_links) <= 10:  # 只显示少量链接
            for i, link in enumerate(all_links):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                classes = link.get('class', [])
                link_id = link.get('id', '')
                
                logger.info(f"  链接 {i+1}: href='{href}' text='{text[:30]}...' class={classes} id='{link_id}'")
        
        # 显示常见元素
        common_elements = {
            'h1': soup.find_all('h1'),
            'h2': soup.find_all('h2'),
            'h3': soup.find_all('h3'),
            'p': soup.find_all('p')[:5],  # 只显示前5个
            'div': soup.find_all('div')[:5]
        }
        
        logger.info("常见元素分析:")
        for tag, elements in common_elements.items():
            if elements:
                logger.info(f"  {tag}标签: {len(elements)}个")
                for i, elem in enumerate(elements[:3]):  # 只显示前3个
                    text = elem.get_text(strip=True)
                    classes = elem.get('class', [])
                    elem_id = elem.get('id', '')
                    logger.info(f"    {tag} {i+1}: text='{text[:30]}...' class={classes} id='{elem_id}'")
    
    def parse_article_detail(self, detail_url: str) -> Optional[Dict]:
        """解析单篇文章详情页，提取关键信息"""
        logger.info(f"开始解析文章详情: {detail_url}")
        
        response = self.make_request(detail_url)
        if not response:
            logger.error(f"获取文章详情失败: {detail_url}")
            return {
                'title': '',
                'author': '',
                'publish_time': '',
                'read_count': 0,
                'like_count': 0,
                'collect_count': 0,
                'summary': '',
                'content': '',
                'detail_url': detail_url,
                'is_bestseller': False,
                'status_code': None,
                'error': 'request_failed'
            }
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.debug(f"详情页HTML长度: {len(response.text)} 字符")

            # 提取数据
            title = self.extract_text(soup, 'title')
            if not title:
                fallback_title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
                title = fallback_title
            author = self.extract_text(soup, 'author')
            publish_time = self.extract_text(soup, 'publish_time')
            read_count = self.extract_number(soup, 'read_count')
            like_count = self.extract_number(soup, 'like_count')
            collect_count = self.extract_number(soup, 'collect_count')
            content_summary = self.extract_text(soup, 'summary', max_length=200)
            content = self.extract_content(soup)
            if not content_summary and content:
                content_summary = content[:200] + ("..." if len(content) > 200 else "")
            
            logger.debug(f"提取的数据 - 标题: {title[:50]}..., 作者: {author}, 发布时间: {publish_time}")
            logger.debug(f"统计数据 - 阅读: {read_count}, 点赞: {like_count}, 收藏: {collect_count}")
            
            # 数据验证
            if not title:
                title = detail_url
            
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
                'content': content,
                'detail_url': detail_url,
                'is_bestseller': is_bestseller,
                'status_code': response.status_code,
                'error': None if response.status_code == 200 else f"http_{response.status_code}"
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"解析详情页失败 {detail_url}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def extract_text(self, soup: BeautifulSoup, field: str, max_length: int = None) -> str:
        """提取文本内容"""
        selector = self.selectors.get(field)
        if not selector:
            logger.warning(f"未找到字段 {field} 的选择器配置")
            return ''

    def extract_content(self, soup: BeautifulSoup) -> str:
        for t in soup.find_all(["script", "style", "noscript"]):
            t.decompose()

        selector = self.selectors.get('content')
        if selector:
            try:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text("\n", strip=True)
                    return text
            except Exception:
                pass

        article = soup.find("article")
        if article:
            paragraphs = [p.get_text(" ", strip=True) for p in article.find_all("p")]
            paragraphs = [p for p in paragraphs if len(p) >= 20]
            text = "\n".join(paragraphs).strip()
            if len(text) >= 200:
                return text

        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paragraphs = [p for p in paragraphs if len(p) >= 20]
        text = "\n".join(paragraphs).strip()
        if len(text) >= 200:
            return text

        candidates = soup.find_all(["div", "section", "main"])
        best_text = ""
        for node in candidates:
            node_text = node.get_text("\n", strip=True)
            if len(node_text) > len(best_text):
                best_text = node_text
        return best_text.strip()
        
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
        """提取数字内容"""
        selector = self.selectors.get(field)
        if not selector:
            logger.warning(f"未找到字段 {field} 的选择器配置")
            return 0
        
        try:
            element = soup.select_one(selector)
            if element:
                text = element.text.strip().replace(',', '')
                # 尝试提取数字
                import re
                numbers = re.findall(r'\d+', text)
                if numbers:
                    number = int(numbers[0])
                    logger.debug(f"提取数字 - {field}: {selector} -> {text} -> {number}")
                    return number
                else:
                    logger.debug(f"未找到数字 - {field}: {selector} -> {text}")
                    return 0
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
        """判断是否为爆款文章"""
        result = (read_count > self.min_read_count) and (interaction_count > self.min_interaction_count)
        logger.debug(f"爆款判断 - 阅读: {read_count} > {self.min_read_count} = {read_count > self.min_read_count}, "
                    f"互动: {interaction_count} > {self.min_interaction_count} = {interaction_count > self.min_interaction_count}, "
                    f"结果: {result}")
        return result
    
    def fetch_multiple_pages(self, base_url: str = None, max_pages: int = None) -> List[str]:
        """抓取多页文章链接"""
        if base_url is None:
            base_url = self.base_url
        if max_pages is None:
            max_pages = self.max_pages
            
        logger.info(f"开始抓取多页文章，基础URL: {base_url}, 最大页数: {max_pages}")
        all_links = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"抓取第 {page} 页")
            
            # 根据实际网站的翻页URL格式调整
            if page > 1:
                sep = "&" if "?" in base_url else "?"
                page_url = f"{base_url}{sep}page={page}"
            else:
                page_url = base_url
            logger.debug(f"第 {page} 页URL: {page_url}")
            
            links = self.fetch_article_links(page_url)
            if not links:
                logger.warning(f"第 {page} 页无文章，继续尝试下一页")
                continue
                
            all_links.extend(links)
            logger.info(f"第 {page} 页获取到 {len(links)} 个链接，总计: {len(all_links)}")
            
            # 随机延迟，避免被封
            delay = random.uniform(self.page_delay_min, self.page_delay_max)
            logger.debug(f"等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)
            
        logger.info(f"多页抓取完成，总共获取 {len(all_links)} 篇文章链接")
        return all_links


def save_to_csv(data: List[Dict], filename: str, encoding: str = 'utf-8-sig') -> bool:
    """保存数据到CSV文件"""
    logger.info(f"开始保存数据到CSV文件: {filename}")
    
    try:
        # 确保目录存在
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        default_fieldnames = [
            "title",
            "author",
            "publish_time",
            "read_count",
            "like_count",
            "collect_count",
            "summary",
            "content",
            "detail_url",
            "is_bestseller",
            "status_code",
            "error",
        ]

        fieldnames = list(data[0].keys()) if data else default_fieldnames

        logger.debug(f"数据条数: {len(data)}")
        logger.debug(f"数据字段: {fieldnames}")
        if data:
            logger.debug(f"数据示例: {data[0]}")
        
        with open(filename, mode='w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            if data:
                writer.writerows(data)
        
        logger.info(f"成功保存 {len(data)} 条记录到 {filename}")
        return True
        
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")
        logger.error(traceback.format_exc())
        return False


def run_safe_test():
    """运行安全测试"""
    print("=" * 60)
    print("🕷️ 民商法爆款文章爬虫 - 修复版安全测试")
    print("=" * 60)
    
    try:
        # 初始化配置管理器
        config_manager = FixedConfigManager()
        logger.info("配置管理器初始化完成")
        
        # 初始化爬虫
        scraper = FixedWebScraper(config_manager)
        logger.info("修复版爬虫初始化完成")
        
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
        
        # 2. 运行小规模爬取测试
        print("\n2️⃣ 运行小规模爬取测试...")
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
        
        # 3. 保存结果
        if article_links:
            csv_filename = config_manager.get('output.csv_filename', 'fixed_bestsellers.csv')
            
            # 创建测试数据
            test_data = []
            for i, link in enumerate(article_links[:5]):  # 只取前5个
                article_data = scraper.parse_article_detail(link)
                if article_data:
                    test_data.append(article_data)
            
            if test_data:
                if save_to_csv(test_data, csv_filename):
                    print(f"\n✅ 结果保存成功")
                    print(f"   文件: {csv_filename}")
                    print(f"   记录数: {len(test_data)}")
                else:
                    print(f"\n❌ 结果保存失败")
            else:
                print(f"\n⚠️ 没有有效数据可保存")
        
        print("\n" + "=" * 60)
        print("🔍 修复版测试完成！")
        print(f"   日志文件: fixed_scraper.log")
        print(f"   结果文件: {config_manager.get('output.csv_filename')}")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        return False
    except Exception as e:
        print(f"\n\n测试过程发生错误: {e}")
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    try:
        success = run_safe_test()
        if success:
            print("\n✅ 修复版爬虫测试成功！")
            print("\n💡 使用建议:")
            print("   1. 修改 config.json 中的 base_url 为您要爬取的真实网站")
            print("   2. 根据目标网站结构调整 selectors 配置")
            print("   3. 调整 bestseller_criteria 中的标准值")
            print("   4. 运行 python configurable_scraper.py 开始正式爬取")
        else:
            print("\n❌ 修复版爬虫测试失败，请检查日志文件")
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n程序发生错误: {e}")
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
