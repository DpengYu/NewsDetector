"""
数据清洗处理器
实现原始数据的标准化、去重和格式化
"""

import html
import re
from hashlib import md5
from typing import List, Dict, Optional
from datetime import datetime
from dateutil.parser import parse  # 用于解析多种日期格式

class DataCleaner:
    """数据清洗器，提供数据清洗、去重和格式化功能"""

    @staticmethod
    def clean_html(raw_html: str) -> str:
        """
        清除HTML标签并转义特殊字符
        参数:
            raw_html: 包含HTML的原始文本
        返回:
            str: 纯文本内容
        """
        if not raw_html:
            return ''
        # 移除HTML标签
        clean = re.sub(r'<[^>]+>', '', raw_html)
        # 转义特殊字符
        return html.unescape(clean).strip()

    @staticmethod
    def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """
        将字符串时间转换为 datetime 对象
        支持多种日期格式（ISO 8601、RFC 3339等）
        参数:
            dt_str: 日期字符串
        返回:
            Optional[datetime]: 转换后的 datetime 对象，如果失败则返回 None
        """
        if not dt_str:
            return None
        try:
            # 处理 ISO 8601 格式的时间字符串（如 '2025-03-19T02:51:00Z'）
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # 使用 dateutil 解析其他格式的日期
                return parse(dt_str)
            except (ValueError, AttributeError):
                return None  # 如果转换失败，返回 None

    @staticmethod
    def clean_article(article: Dict) -> Dict:
        """
        清洗单条新闻数据
        参数:
            article: 原始新闻数据（字典格式）
        返回:
            Dict: 清洗后的新闻数据
        """
        if not article:
            return {}
        
        # 清洗字段
        cleaned = {
            'title': DataCleaner.clean_html(article.get('title', '')),
            'url': article.get('url', ''),
            'description': DataCleaner.clean_html(article.get('description', '')),
            'source': article.get('source', 'Unknown'),
            'author': article.get('author', 'Anonymous'),
            'published_at': DataCleaner.parse_datetime(article.get('published_at'))
        }
        return cleaned

    @staticmethod
    def deduplicate(items: List[Dict]) -> List[Dict]:
        """
        基于内容哈希去重
        参数:
            items: 原始数据列表
        返回:
            List[Dict]: 去重后的数据
        """
        if not items:
            return []
        
        seen = set()
        unique = []
        for item in items:
            # 生成内容指纹（基于标题和URL）
            fingerprint = md5(
                (item.get('title', '') + item.get('url', '')).encode('utf-8')
            ).hexdigest()
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(item)
        return unique

    @staticmethod
    def normalize_data(items: List[Dict]) -> List[Dict]:
        """
        标准化数据
        参数:
            items: 原始数据列表
        返回:
            List[Dict]: 标准化后的数据
        """
        if not items:
            return []
        
        # 清洗每条数据
        cleaned = [DataCleaner.clean_article(item) for item in items]
        # 去重
        return DataCleaner.deduplicate(cleaned)