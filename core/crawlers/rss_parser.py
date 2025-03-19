"""
通用RSS解析模块
支持多种RSS源的标准化解析
"""

import feedparser
from typing import List, Dict
from dateutil.parser import parse
from utils.helpers import safe_parse_date
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class RSSParser:
    """RSS解析器"""
    def __init__(self, source_name: str):
        """
        初始化指定数据源的解析器
        参数:
            source_name: 配置中定义的数据源名称
        """
        self.feed_url = settings.TECH_SOURCES.get(source_name)
        if not self.feed_url:
            raise ValueError(f"未配置的RSS源: {source_name}")

    def parse(self) -> List[Dict]:
        """解析并返回标准化数据"""
        try:
            feed = feedparser.parse(self.feed_url)
            return [self._format_entry(entry) for entry in feed.entries]
        except Exception as e:
            logger.error(f"RSS解析失败({self.feed_url}): {str(e)}")
            return []

    def _format_entry(self, entry) -> Dict:
        """统一数据格式"""
        return {
            'title': entry.title,
            'url': entry.link,
            'published_at': safe_parse_date(entry.get('published')),
            'source': self.feed_url.split('//')[1].split('/')[0],  # 提取域名
            'description': entry.get('summary', '')
        }