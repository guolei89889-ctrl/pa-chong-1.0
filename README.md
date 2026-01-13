# 民商法爆款文章爬虫项目

这是一个用于抓取民商法相关爆款文章的Python网络爬虫项目。

## 功能特性

### ✅ 已完成的功能

1. **错误处理和重试机制**
   - 自动重试失败的请求（最多3次）
   - 指数退避延迟策略
   - 详细的错误日志记录

2. **多页面抓取**
   - 支持翻页抓取
   - 可配置最大抓取页数
   - 智能停止机制（当页面无内容时）

3. **配置文件管理**
   - JSON格式配置文件
   - 支持自定义选择器
   - 灵活的目标网站适配

4. **日志记录**
   - 详细的运行日志
   - 文件和控制台双重输出
   - 可配置的日志级别

5. **数据验证和清洗**
   - 自动数据类型转换
   - 空值处理
   - 文本长度限制

## 文件结构

```
项目目录/
├── improved_scraper.py          # 改进版爬虫（基础功能）
├── configurable_scraper.py      # 配置版爬虫（推荐）
├── config.json                  # 配置文件
├── requirements.txt             # 依赖包列表
└── README.md                    # 使用说明
```

## 安装依赖

```bash
pip install requests beautifulsoup4 lxml
```

或者使用requirements.txt：
```bash
pip install -r requirements.txt
```

## 使用方法

### 快速开始（推荐配置版）

1. **配置目标网站**
   编辑 `config.json` 文件，修改以下内容：
   ```json
   {
       "target_platform": {
           "base_url": "https://your-target-website.com/law-section",
           "selectors": {
               "article_links": "选择器配置",
               "title": "文章标题选择器",
               "author": "作者选择器",
               "publish_time": "发布时间选择器",
               "read_count": "阅读量选择器",
               "like_count": "点赞数选择器",
               "collect_count": "收藏数选择器",
               "summary": "摘要选择器"
           }
       }
   }
   ```

2. **运行爬虫**
   ```bash
   python configurable_scraper.py
   ```

### 基础使用（改进版）

```bash
python improved_scraper.py
```

## 配置说明

### 目标平台配置 (`target_platform`)

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `base_url` | 目标网站基础URL | `"https://example.com/law"` |
| `headers` | HTTP请求头 | 包含User-Agent等 |
| `selectors` | CSS选择器配置 | 见下表 |

### 选择器配置 (`selectors`)

| 字段 | 说明 | 示例 |
|------|------|------|
| `article_links` | 文章链接选择器 | `"a.article-link"` |
| `title` | 文章标题选择器 | `"h1.article-title"` |
| `author` | 作者选择器 | `"span.author-name"` |
| `publish_time` | 发布时间选择器 | `"time.publish-date"` |
| `read_count` | 阅读量选择器 | `"span.read-count"` |
| `like_count` | 点赞数选择器 | `"span.like-count"` |
| `collect_count` | 收藏数选择器 | `"span.collect-count"` |
| `summary` | 摘要选择器 | `"div.article-summary"` |

### 爬虫配置 (`scraping`)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `max_pages` | 最大抓取页数 | `3` |
| `max_retries` | 最大重试次数 | `3` |
| `retry_delay` | 重试延迟时间(秒) | `2` |
| `request_timeout` | 请求超时时间(秒) | `10` |
| `request_delay_min` | 最小请求延迟(秒) | `0.5` |
| `request_delay_max` | 最大请求延迟(秒) | `2.0` |
| `page_delay_min` | 最小翻页延迟(秒) | `1.0` |
| `page_delay_max` | 最大翻页延迟(秒) | `3.0` |

### 爆款标准 (`bestseller_criteria`)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `min_read_count` | 最小阅读量 | `10000` |
| `min_interaction_count` | 最小互动量(点赞+收藏) | `1000` |

## 输出文件

### CSV文件
包含以下字段：
- `title`: 文章标题
- `author`: 作者
- `publish_time`: 发布时间
- `read_count`: 阅读量
- `like_count`: 点赞数
- `collect_count`: 收藏数
- `summary`: 文章摘要
- `detail_url`: 文章详情页URL
- `is_bestseller`: 是否为爆款文章

### 日志文件
- 文件名：`scraper.log`
- 包含详细的运行日志、错误信息和调试信息

## 使用技巧

### 1. 适配新网站

1. 分析目标网站的HTML结构
2. 使用浏览器开发者工具找到对应的CSS选择器
3. 更新配置文件中的选择器
4. 调整爆款标准以适应不同平台

### 2. 调试和测试

1. 将日志级别设置为`DEBUG`以获取更多信息
2. 先抓取少量页面进行测试
3. 检查生成的CSV文件格式是否正确

### 3. 避免被封

1. 合理设置请求延迟时间
2. 使用真实的User-Agent
3. 控制抓取频率和总量
4. 考虑使用代理IP（高级用法）

## 注意事项

⚠️ **法律合规**
- 确保爬取行为符合目标网站的服务条款
- 尊重robots.txt文件规定
- 避免对目标网站造成过大负担

⚠️ **技术注意**
- 本项目仅供学习和研究使用
- 实际使用前需要适配目标网站的具体结构
- 建议先获得网站所有者的授权

## 扩展功能

### 计划中的功能

- [ ] 代理IP支持
- [ ] 数据库存储（SQLite/MySQL）
- [ ] 分布式抓取
- [ ] 自动选择器识别
- [ ] 数据可视化
- [ ] 定时任务
- [ ] Web界面管理

### 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

MIT License - 详见LICENSE文件