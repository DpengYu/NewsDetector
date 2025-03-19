import requests
from typing import List, Dict
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class NewsAPICrawler:
    """NewsAPI数据采集器"""
    
    BASE_URL = "https://newsapi.org/v2/top-headlines"
    
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY  # 使用 settings.NEWS_API_KEY
        self.session = requests.Session()
        # 配置请求重试策略
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    def fetch(self) -> List[Dict]:
        """
        获取科技类头条新闻
        返回:
            List[Dict]: 标准化格式的新闻列表
        """
        params = {
            'apiKey': self.api_key,
            'category': 'technology',
            'pageSize': 50  # 最大允许值
        }
        
        try:
            resp = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10,
                verify=True  # 强制SSL验证
            )
            resp.raise_for_status()
            return self._format_data(resp.json()['articles'])
        except Exception as e:
            logger.error(f"NewsAPI请求失败: {str(e)}")
            return []

    def _format_data(self, raw_data: List[Dict]) -> List[Dict]:
        """标准化数据格式"""
        formatted = []
        for item in raw_data:
            if not validate_url(item.get('url', '')):
                continue  # 跳过无效URL
            
            formatted.append({
                'title': item['title'],
                'url': item['url'],
                'description': item.get('description', ''),
                'published_at': item['publishedAt'],
                'source': 'NewsAPI',
                'author': item.get('author')
            })
        return formatted