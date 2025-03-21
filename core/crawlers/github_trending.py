import re
import requests
from bs4 import BeautifulSoup
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

def extract_star_number(text: str) -> int:
    """从文本中提取星星数量"""
    match = re.search(r'[\d,]+', text)
    if match:
        return int(match.group().replace(',', ''))
    return 0

class GitHubTrendingCrawler:
    """GitHub趋势仓库采集器（支持打印未解析的完整文本）"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'TechNewsMonitor/1.0 (+https://github.com/your_repo)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        self.session = requests.Session()
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    def fetch(self) -> list:
        """
        获取当前趋势仓库列表
        返回:
            list: 按今日star数降序排列的仓库列表
        """
        try:
            resp = self.session.get(
                settings.TECH_SOURCES["GitHubTrending"],
                headers=self.headers,
                timeout=15
            )
            resp.raise_for_status()

            # 打印未解析的完整HTML文本
            # logger.info(f"未解析的完整HTML文本： {resp.text}")

            soup = BeautifulSoup(resp.text, 'lxml')
            return self._parse(soup)
        except Exception as e:
            logger.error(f"GitHub trending爬取失败: {str(e)}")
            return []

    def _parse(self, soup: BeautifulSoup) -> list:
        """解析页面并提取仓库信息"""
        repos = []
        
        for article in soup.select('article.Box-row'):
            # 基础信息解析
            repo = {
                'title': article.h2.get_text(strip=True),
                'url': "https://github.com" + article.h2.a['href'],
                'description': (article.p.get_text(strip=True) 
                               if article.p else ""),
                'source': 'GitHub'
            }

            # Star数量解析
            star_stats = article.select('div.f6.color-fg-muted.mt-2 > span')
            
            for span in star_stats:
                text = span.get_text(strip=True).lower()
                if 'star' in text:
                    if 'today' in text:
                        today_stars = extract_star_number(text)

            repo.update({
                'today_stars': today_stars
            })
            repos.append(repo)

        # 按今日star数降序排序
        sorted_repos = sorted(
            repos,
            key=lambda x: x['today_stars'],
            reverse=True
        )
        
        return sorted_repos[:10]  # 返回Top10

# 使用示例
if __name__ == "__main__":
    crawler = GitHubTrendingCrawler()
    trending_repos = crawler.fetch()
    for idx, repo in enumerate(trending_repos, 1):
        print(f"\n{idx}. {repo['title']}")
        print(f"今日新增：{repo['today_stars']} stars")
        print(f"描述：{repo['description']}")