"""
爬虫模块入口文件
暴露所有爬虫类供外部调用
"""

from .news_api import NewsAPICrawler  # noqa: F401
from .rss_parser import RSSParser  # noqa: F401
from .github_trending import GitHubTrendingCrawler  # noqa: F401

__all__ = ['NewsAPICrawler', 'RSSParser', 'GitHubTrendingCrawler']