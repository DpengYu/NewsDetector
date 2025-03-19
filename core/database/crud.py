from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base, NewsArticle
from config.settings import settings

class NewsDatabase:
    """数据库操作类"""
    
    def __init__(self):
        """初始化数据库连接"""
        # 确保路径正确
        db_path = str(settings.DATABASE_CONFIG["db_path"])
        self.engine = create_engine(
            f'sqlite:///{db_path}',  # 使用绝对路径
            echo=False
        )
        self.Session = sessionmaker(bind=self.engine)
        
        # 自动创建数据表（如果不存在）
        Base.metadata.create_all(self.engine)

    def save_batch(self, articles: list):
        """批量保存新闻数据"""
        session = self.Session()
        try:
            objs = [NewsArticle(**item) for item in articles]
            session.bulk_save_objects(objs)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def query_recent(self, hours: int = 24) -> list:
        """查询最近N小时的新闻"""
        session = self.Session()
        try:
            stmt = text("""
                SELECT * FROM tech_news 
                WHERE published_at > datetime('now', '-:hours hours')
            """)
            result = session.execute(stmt, {'hours': hours})
            return [dict(row) for row in result]
        finally:
            session.close()