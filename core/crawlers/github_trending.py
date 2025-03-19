import requests
from bs4 import BeautifulSoup
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class GitHubTrendingCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'TechNewsMonitor/1.0 (+https://github.com/your_repo)'
        }
        self.session = requests.Session()
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    def get_trending_repos(self):
        try:
            resp = self.session.get(
                settings.TECH_SOURCES["GitHubTrending"],
                headers=self.headers,
                timeout=15
            )
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            return self.parse(soup)
        except Exception as e:
            logger.error(f"GitHub trending爬取失败: {str(e)}")
            return []

    def parse(self, soup):
        repos = []
        for article in soup.select('article'):
            repo = {
                'title': article.h2.text.strip(),
                'url': "https://github.com" + article.h2.a['href'],
                'description': article.p.text.strip() if article.p else "",
                'source': 'GitHub'
            }
            repos.append(repo)
        return repos[:10]