"""
Prometheus监控指标定义模块
"""

from prometheus_client import start_http_server, Counter, Gauge

# 启动指标服务器（在main.py中调用）
def start_monitoring(port=8000):
    """启动Prometheus指标端点"""
    start_http_server(port)

# 请求计数器（按来源和状态分类）
REQUEST_COUNTER = Counter(
    'tech_news_requests_total', 
    'Total news collection requests',
    ['source', 'status']  # 标签维度
)

# 处理耗时统计（按阶段分类）
PROCESS_TIME = Gauge(
    'tech_news_process_seconds',
    'News processing time',
    ['stage']  # 阶段标签：collect/save/total
)

# 新闻数量统计
ITEMS_GAUGE = Gauge(
    'tech_news_items_total',
    'Number of news items processed'
)