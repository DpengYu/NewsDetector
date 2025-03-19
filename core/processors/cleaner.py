"""
数据清洗处理器
实现原始数据的标准化和去重
"""

import html
import re
from hashlib import md5
from typing import List, Dict

class DataCleaner:
    """数据清洗器"""
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
    def deduplicate(items: List[Dict]) -> List[Dict]:
        """
        基于内容哈希去重
        参数:
            items: 原始数据列表
        返回:
            List[Dict]: 去重后的数据
        """
        seen = set()
        unique = []
        for item in items:
            # 生成内容指纹
            fingerprint = md5(
                (item['title'] + item['url']).encode('utf-8')
            ).hexdigest()
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(item)
        return unique
    
    @staticmethod
    def normalize_date(date_str: str) -> str:
        """
        标准化日期格式为ISO 8601
        参数:
            date_str: 原始日期字符串
        返回:
            str: YYYY-MM-DDTHH:MM:SSZ 格式
        """
        from dateutil.parser import parse
        try:
            return parse(date_str).isoformat() + 'Z'
        except:
            return ''  # 无效日期置空