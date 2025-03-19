"""
GitHub趋势仓库爬虫模块
实现GitHub趋势页面的数据抓取和解析
"""

import requests
from bs4 import BeautifulSoup
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class GitHubTrendingCrawler:
    """GitHub趋势仓库采集器"""
    
    def __init__(self):
        """初始化请求会话和头信息"""
        self.headers = {
            # 合规的User-Agent声明
            'User-Agent': 'TechNewsMonitor/1.0 (+https://github.com/your_repo)'
        }
        self.session = requests.Session()  # 复用TCP连接的会话对象
        # 配置请求重试策略（最大重试3次）
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    def get_trending_repos(self) -> list:
        """
        获取当前趋势仓库列表
        返回:
            list: 仓库信息字典列表，格式为
                  [{'title':..., 'url':..., 'description':...}]
        """
        try:
            resp = self.session.get(
                settings.TECH_SOURCES["GitHubTrending"],
                headers=self.headers,
                timeout=15  # 连接超时15秒
            )
            resp.raise_for_status()  # 自动处理HTTP错误状态码
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(resp.text, 'html.parser')
            return self._parse(soup)
        except Exception as e:
            logger.error(f"GitHub trending爬取失败: {str(e)}")
            return []  # 失败时返回空列表保证系统鲁棒性

    def _parse(self, soup: BeautifulSoup) -> list:
        """
        解析页面内容抽取仓库信息
        参数:
            soup: BeautifulSoup解析后的文档对象
        返回:
            list: 解析后的仓库信息列表
        """
        repos = []
        # 使用CSS选择器定位article元素
        for article in soup.select('article'):
            repo = {
                'title': article.h2.text.strip(),  # 仓库标题
                'url': "https://github.com" + article.h2.a['href'],  # 完整URL
                'description': article.p.text.strip() if article.p else "", # 描述
                'source': 'GitHub'  # 固定数据来源标识
            }
            repos.append(repo)
        return repos[:10]  # 返回前10条避免数据量过大