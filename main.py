import time
import re
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from core.crawlers import GitHubTrendingCrawler, NewsAPICrawler
from core.processors import TechAnalyzer
from core.database import NewsDatabase
from utils.logger import configure_logging, get_logger
from utils.metrics import REQUEST_COUNTER, PROCESS_TIME, ITEMS_GAUGE
from prometheus_client import start_http_server
from core.processors.cleaner import DataCleaner
from core.notification import EmailSender,EmailSenderAI
from dotenv import load_dotenv

# 配置日志
configure_logging()
logger = get_logger(__name__)
# 加载环境变量
load_dotenv()

class TechNewsMonitor:
    def __init__(self):
        # 启动Prometheus监控服务
        start_http_server(8000)
        logger.info("Prometheus监控服务已启动，端口：8000")
        
        self.analyzer = TechAnalyzer()
        self.db = NewsDatabase()
        self.crawlers = [
            GitHubTrendingCrawler(),
            NewsAPICrawler()
        ]
        if os.getenv('ENABLE_EMAIL', 'false').lower() == 'true':
            if os.getenv('EMAIL_AI_SENDER', 'false').lower() == 'true':
                self.email_sender = EmailSenderAI()
            else:
                self.email_sender = EmailSender()
        else:
            self.email_sender = None
        logger.info("初始化完成：分析器、数据库、爬虫已加载")

    def collect_news(self):
        all_news = []
        for crawler in self.crawlers:
            crawler_name = crawler.__class__.__name__
            logger.info(f"开始从 {crawler_name} 采集数据...")
            
            try:
                start_time = time.time()
                data = crawler.fetch()
                fetch_time = time.time() - start_time
                logger.info(f"{crawler_name} 采集完成，耗时：{fetch_time:.2f}秒，原始数据量：{len(data)}条")

                # 过滤非技术内容
                start_time = time.time()
                filtered = [n for n in data if self.filter_news(n)]
                filter_time = time.time() - start_time
                logger.info(f"{crawler_name} 过滤完成，耗时：{filter_time:.2f}秒，有效数据量：{len(filtered)}条")
                
                all_news.extend(filtered)
            except Exception as e:
                logger.error(f"{crawler_name} 采集失败：{str(e)}", exc_info=True)
                REQUEST_COUNTER.labels(source=crawler_name, status='error').inc()
        
        logger.info(f"所有爬虫采集完成，总有效数据量：{len(all_news)}条")
        return all_news

    def filter_news(self, news_item):
        lang = 'zh' if re.search(r'[\u4e00-\u9fff]', news_item['title']) else 'en'
        combined_text = f"{news_item['title']} {news_item.get('description', '')}"
        return self.analyzer.is_tech_related(combined_text, lang=lang)

    def run(self):
        scheduler = BlockingScheduler()
        scheduler.add_job(
            self.execute_pipeline,
            'interval',
            hours=1,
            misfire_grace_time=60,
            max_instances=1
        )
        logger.info("调度器已配置，任务间隔：1小时")
        
        # 手动触发第一次任务
        logger.info("手动触发第一次任务...")
        self.execute_pipeline()

        try:
            logger.info("启动调度器...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("监控服务已停止")
        except Exception as e:
            logger.error(f"调度器运行失败：{str(e)}", exc_info=True)

    def execute_pipeline(self):
        start_time = time.time()
        logger.info("开始执行采集任务...")
        
        try:
            # 阶段1：数据采集与过滤
            PROCESS_TIME.labels('collect').set_to_current_time()
            news_data = self.collect_news()

            # 阶段2：数据存储
            PROCESS_TIME.labels('save').set_to_current_time()
            if news_data:
                self.db.save_batch(news_data)
                logger.info(f"数据存储完成，写入量：{len(news_data)}条")
                # 发送邮件通知
                if self.email_sender and news_data:
                    self.email_sender.send_digest(news_data)
            else:
                logger.warning("未采集到有效数据，跳过存储步骤")
            
            # 更新监控指标
            ITEMS_GAUGE.set(len(news_data))
            REQUEST_COUNTER.labels(source='all', status='success').inc()
        except Exception as e:
            logger.error(f"任务执行失败：{str(e)}", exc_info=True)
            REQUEST_COUNTER.labels(source='all', status='error').inc()
        finally:
            total_time = time.time() - start_time
            PROCESS_TIME.labels('total').set(total_time)
            logger.info(f"任务完成，总耗时：{total_time:.2f}秒")

if __name__ == "__main__":
    logger.info("启动 TechNewsMonitor...")
    monitor = TechNewsMonitor()
    monitor.run()