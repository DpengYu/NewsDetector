"""
全局配置管理模块
处理环境变量加载和基础路径配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent # 项目根目录
load_dotenv(BASE_DIR / ".env")

# 数据源配置
TECH_SOURCES = {
    "TechCrunch": os.getenv("TECHCRUNCH_RSS"), # TechCrunch的RSS源
    "GitHubTrending": "https://github.com/trending" # GitHub趋势页面
}

# 数据库配置
DATABASE_CONFIG = {
    'db_path': BASE_DIR / "data/news.db", # SQLite数据库存储路径
    'table_name': 'tech_news' # 数据表名称
}

# 邮件通知服务配置
EMAIL_CONFIG = {
    'smtp_server': os.getenv("SMTP_SERVER"),  # SMTP服务器地址
    'port': 587,  # TLS端口号
    'sender': os.getenv("NOTICE_EMAIL"), # 发件人邮箱
    'password': os.getenv("EMAIL_PASSWORD")  # 邮箱授权码
}