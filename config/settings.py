import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 定义 settings 对象
class Settings:
    # NewsAPI 配置
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # 从环境变量加载

    # 数据源配置
    TECH_SOURCES = {
        "TechCrunch": os.getenv("TECHCRUNCH_RSS"),
        "GitHubTrending": "https://github.com/trending"
    }

    # 数据库配置
    DATABASE_CONFIG = {
        'db_path': BASE_DIR / "data/news.db",
        'table_name': 'tech_news'
    }

    # 邮件配置
    EMAIL_CONFIG = {
        'smtp_server': os.getenv("SMTP_SERVER"),
        'port': 587,
        'sender': os.getenv("NOTICE_EMAIL"),
        'password': os.getenv("EMAIL_PASSWORD")
    }

# 导出 settings 对象
settings = Settings()