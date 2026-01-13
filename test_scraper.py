#!/usr/bin/env python3
"""
测试民商法爆款文章爬虫
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from configurable_scraper import WebScraper, ConfigManager, save_to_csv
import json


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""
    
    def setUp(self):
        self.config_manager = ConfigManager()
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        config = self.config_manager.get_default_config()
        self.assertIn('target_platform', config)
        self.assertIn('scraping', config)
        self.assertIn('bestseller_criteria', config)
    
    def test_get_config_value(self):
        """测试获取配置值"""
        base_url = self.config_manager.get('target_platform.base_url')
        self.assertIsNotNone(base_url)
        
        max_pages = self.config_manager.get('scraping.max_pages')
        self.assertEqual(max_pages, 3)
    
    def test_get_nested_config(self):
        """测试获取嵌套配置"""
        selectors = self.config_manager.get('target_platform.selectors')
        self.assertIsInstance(selectors, dict)
        self.assertIn('title', selectors)


class TestWebScraper(unittest.TestCase):
    """测试网络爬虫"""
    
    def setUp(self):
        self.config_manager = ConfigManager()
        self.scraper = WebScraper(self.config_manager)
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.scraper.session)
        self.assertEqual(self.scraper.max_retries, 3)
        self.assertEqual(self.scraper.min_read_count, 10000)
    
    def test_is_bestseller(self):
        """测试爆款判断"""
        # 测试爆款文章
        self.assertTrue(self.scraper.is_bestseller(15000, 1500))
        
        # 测试普通文章
        self.assertFalse(self.scraper.is_bestseller(5000, 500))
        self.assertFalse(self.scraper.is_bestseller(15000, 500))
        self.assertFalse(self.scraper.is_bestseller(5000, 1500))
    
    def test_extract_text(self):
        """测试文本提取"""
        from bs4 import BeautifulSoup
        
        html = '<html><body><h1 class="article-title">测试标题</h1></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        # 模拟选择器配置
        self.scraper.selectors['title'] = 'h1.article-title'
        
        result = self.scraper.extract_text(soup, 'title')
        self.assertEqual(result, '测试标题')
    
    def test_extract_number(self):
        """测试数字提取"""
        from bs4 import BeautifulSoup
        
        html = '<html><body><span class="read-count">12,345</span></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        # 模拟选择器配置
        self.scraper.selectors['read_count'] = 'span.read-count'
        
        result = self.scraper.extract_number(soup, 'read_count')
        self.assertEqual(result, 12345)


class TestSaveToCSV(unittest.TestCase):
    """测试CSV保存功能"""
    
    def test_save_empty_data(self):
        """测试保存空数据"""
        result = save_to_csv([], 'test.csv')
        self.assertFalse(result)
    
    def test_save_valid_data(self):
        """测试保存有效数据"""
        test_data = [
            {
                'title': '测试文章',
                'author': '测试作者',
                'read_count': 10000,
                'like_count': 1000,
                'is_bestseller': True
            }
        ]
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        try:
            result = save_to_csv(test_data, temp_file)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(temp_file))
            
            # 验证文件内容
            with open(temp_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                self.assertIn('测试文章', content)
                self.assertIn('测试作者', content)
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch('requests.Session.get')
    def test_full_scraping_process(self, mock_get):
        """测试完整的爬虫流程"""
        # 模拟响应
        mock_response = Mock()
        mock_response.text = '''
        <html>
        <body>
            <a class="article-link" href="/article/1">文章1</a>
            <a class="article-link" href="/article/2">文章2</a>
        </body>
        </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        config_manager = ConfigManager()
        scraper = WebScraper(config_manager)
        
        # 测试获取文章链接
        links = scraper.fetch_article_links('http://example.com')
        self.assertEqual(len(links), 2)
        self.assertIn('http://example.com/article/1', links)
        self.assertIn('http://example.com/article/2', links)


def run_basic_test():
    """运行基础测试"""
    print("运行基础测试...")
    
    # 测试配置管理器
    config_manager = ConfigManager()
    print(f"✓ 配置管理器初始化成功")
    print(f"  - 目标URL: {config_manager.get('target_platform.base_url')}")
    print(f"  - 最大页数: {config_manager.get('scraping.max_pages')}")
    print(f"  - 爆款标准: 阅读量>{config_manager.get('bestseller_criteria.min_read_count')}, 互动>{config_manager.get('bestseller_criteria.min_interaction_count')}")
    
    # 测试爬虫初始化
    scraper = WebScraper(config_manager)
    print(f"✓ 爬虫初始化成功")
    
    # 测试爆款判断
    test_cases = [
        (15000, 1500, True, "爆款文章"),
        (5000, 500, False, "普通文章"),
        (15000, 500, False, "阅读量高但互动低"),
        (5000, 1500, False, "互动高但阅读量低")
    ]
    
    for read_count, interaction_count, expected, description in test_cases:
        result = scraper.is_bestseller(read_count, interaction_count)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}: 阅读量={read_count}, 互动={interaction_count} -> {'爆款' if result else '普通'}")
    
    print("\n基础测试完成！")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'unittest':
        # 运行完整的单元测试
        unittest.main(argv=[''], exit=False)
    else:
        # 运行基础测试
        run_basic_test()