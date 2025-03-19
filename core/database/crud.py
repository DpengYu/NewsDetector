"""
数据库CRUD操作模块
实现新闻数据的存储和查询
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_CONFIG
from .models import Base, NewsArticle

class NewsDatabase:
    """新闻数据库管理类"""
    
    def __init__(self):
        """初始化数据库连接"""
        # 创建SQLite连接引擎
        self.engine = create_engine(
            f'sqlite:///{DATABASE_CONFIG["db_path"]}', 
            echo=False  # 生产环境关闭SQL日志
        )
        # 创建会话工厂
        self.Session = sessionmaker(bind=self.engine)
        
        # 自动创建数据表（如果不存在）
        Base.metadata.create_all(self.engine)

    def save_batch(self, articles: list):
        """
        批量保存新闻数据
        参数:
            articles: 新闻字典列表
        """
        session = self.Session()
        try:
            # 将字典转换为ORM对象
            objs = [NewsArticle(**item) for item in articles]
            session.bulk_save_objects(objs)
            session.commit()  # 批量提交
        except Exception as e:
            session.rollback()  # 回滚事务
            raise e
        finally:
            session.close()  # 确保连接关闭

    def query_recent(self, hours: int = 24) -> list:
        """
        查询最近N小时的新闻
        参数:
            hours: 时间范围（小时）
        返回:
            list: 新闻字典列表
        """
        session = self.Session()
        try:
            # 使用SQLAlchemy核心API提高查询效率
            stmt = text("""
                SELECT * FROM tech_news 
                WHERE published_at > datetime('now', '-:hours hours')
            """)
            result = session.execute(stmt, {'hours': hours})
            return [dict(row) for row in result]
        finally:
            session.close()