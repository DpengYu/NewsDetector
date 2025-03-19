import time
from apscheduler.schedulers.blocking import BlockingScheduler
from core.crawlers import GitHubTrendingCrawler, NewsAPICrawler
from core.processors import TechAnalyzer
from core.database import NewsDatabase
from utils.logger import configure_logging

configure_logging()

class TechNewsMonitor:
    def __init__(self):
        self.analyzer = TechAnalyzer()
        self.db = NewsDatabase()
        self.crawlers = [
            GitHubTrendingCrawler(),
            NewsAPICrawler()
        ]

    def collect_news(self):
        all_news = []
        for crawler in self.crawlers:
            try:
                data = crawler.fetch()
                filtered = [n for n in data if self.filter_news(n)]
                all_news.extend(filtered)
            except Exception as e:
                logger.error(f"爬取失败: {crawler.__class__.__name__} - {str(e)}")
        return all_news

    def filter_news(self, news_item):
        lang = 'zh' if re.search(r'[\u4e00-\u9fff]', news_item['title']) else 'en'
        return self.analyzer.is_tech_related(
            f"{news_item['title']} {news_item.get('description', '')}",
            lang=lang
        )

    def run(self):
        scheduler = BlockingScheduler()
        scheduler.add_job(self.execute_pipeline, 'interval', hours=1, misfire_grace_time=60)
        try:
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("监控服务已停止")

    def execute_pipeline(self):
        start_time = time.time()
        logger.info("开始执行采集任务...")
        
        try:
            news_data = self.collect_news()
            self.db.save_batch(news_data)
            logger.info(f"本次采集完成，获得{len(news_data)}条有效数据")
        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}")
        
        logger.info(f"任务耗时: {time.time()-start_time:.2f}秒")

if __name__ == "__main__":
    monitor = TechNewsMonitor()
    monitor.run()