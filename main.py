import time
import re  # 正则表达式模块，用于文本匹配
from apscheduler.schedulers.blocking import BlockingScheduler  # 定时任务调度器
from core.crawlers import GitHubTrendingCrawler, NewsAPICrawler  # 自定义爬虫类
from core.processors import TechAnalyzer  # 技术分析模块
from core.database import NewsDatabase  # 数据库操作类
from utils.logger import configure_logging  # 日志配置工具
from utils.metrics import REQUEST_COUNTER, PROCESS_TIME, ITEMS_GAUGE  # 监控指标

configure_logging()  # 调用自定义方法配置日志格式、存储路径等
# 作用：统一日志输出格式，确保INFO/WARNING/ERROR分级记录

class TechNewsMonitor:
    def __init__(self):
        # 启动Prometheus指标服务（端口8000）
        start_http_server(8000)  
        self.analyzer = TechAnalyzer()  # 初始化技术分析器（含NLP处理）
        self.db = NewsDatabase()        # 创建数据库连接实例
        # 加载所有数据爬虫
        self.crawlers = [
            GitHubTrendingCrawler(),  # GitHub趋势爬虫
            NewsAPICrawler()          # NewsAPI官方源爬虫
        ]

    def collect_news(self):
        all_news = []  # 存储有效新闻的容器
        for crawler in self.crawlers:  # 遍历所有注册的爬虫
            try:
                data = crawler.fetch()  # 执行爬取动作
                # 使用分析器过滤非技术内容
                filtered = [n for n in data if self.filter_news(n)]  
                all_news.extend(filtered)  # 合并有效数据
            except Exception as e:
                # 记录具体爬虫的故障信息
                logger.error(f"爬取失败: {crawler.__class__.__name__} - {str(e)}")  
        return all_news  # 返回所有合格数据

    def filter_news(self, news_item):
        # 自动检测内容语言（中文/英文）
        lang = 'zh' if re.search(r'[\u4e00-\u9fff]', news_item['title']) else 'en'
        # 组合标题和描述进行分析
        combined_text = f"{news_item['title']} {news_item.get('description', '')}"
        # 调用技术分析器判断相关性
        return self.analyzer.is_tech_related(combined_text, lang=lang)

    def run(self):
        # 创建调度器实例
        scheduler = BlockingScheduler()  
        # 配置定时任务：
        # - 每小时执行一次
        # - 允许60秒内的任务延迟（防止任务堆积）
        # - 同一时间只允许一个实例运行
        scheduler.add_job(
            self.execute_pipeline, 
            'interval', 
            hours=1, 
            misfire_grace_time=60,
            max_instances=1
        )
        try:
            scheduler.start()  # 启动调度器（阻塞主线程）
        except KeyboardInterrupt:  # 捕获Ctrl+C信号
            logger.info("监控服务已停止")  # 优雅退出日志

    def execute_pipeline(self):
        start_time = time.time()  # 记录任务开始时间
        logger.info("开始执行采集任务...")
        try:
            # 阶段1：数据采集与过滤
            PROCESS_TIME.labels('collect').set_to_current_time()
            news_data = self.collect_news()
            # 阶段2：数据存储
            PROCESS_TIME.labels('save').set_to_current_time()
            self.db.save_batch(news_data)  # 批量写入数据库
            # 记录成功指标
            ITEMS_GAUGE.set(len(news_data))  # 更新采集数量指标
            REQUEST_COUNTER.labels(source='all', status='success').inc()  # 成功计数器+1
            logger.info(f"本次采集完成，获得{len(news_data)}条有效数据")
        except Exception as e:  # 全局异常捕获
            # 记录失败指标
            REQUEST_COUNTER.labels(source='all', status='error').inc()  
            logger.error(f"任务执行失败: {str(e)}")
        finally:
            # 记录总耗时指标
            PROCESS_TIME.labels('total').set(time.time() - start_time)
            logger.info(f"任务耗时: {time.time()-start_time:.2f}秒")

if __name__ == "__main__":
    monitor = TechNewsMonitor()  # 创建监控实例
    monitor.run()  # 启动主循环