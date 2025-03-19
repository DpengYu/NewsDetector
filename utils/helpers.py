"""
通用工具函数模块
"""

import re
from datetime import datetime
from typing import Optional
from requests import Session
from urllib3.util.retry import Retry

def validate_url(url: str) -> bool:
    """
    验证URL格式合法性
    参数:
        url: 待验证的URL字符串
    返回:
        bool: 是否合法
    """
    regex = re.compile(
        r'^(?:http)s?://'  # 协议头
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # 域名
        r'localhost|'  # 本地地址
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IPv4
        r'(?::\d+)?'  # 端口
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def safe_parse_date(date_str: Optional[str]) -> Optional[str]:
    """
    安全解析日期字符串
    参数:
        date_str: 原始日期字符串
    返回:
        str: ISO格式日期或None
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError):
        return None

def create_retry_session(retries=3) -> Session:
    """
    创建带重试机制的请求会话
    参数:
        retries: 最大重试次数
    返回:
        Session: 配置好的会话对象
    """
    session = Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.mount('https://', HTTPAdapter(max_retries=retry))
    return session