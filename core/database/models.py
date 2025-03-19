"""
数据库ORM模型定义
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class NewsArticle(Base):
    """新闻文章数据表模型"""
    __tablename__ = 'tech_news'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)  # URL唯一约束
    description = Column(Text)
    source = Column(String(100), index=True)  # 来源索引
    published_at = Column(DateTime(timezone=True), index=True)  # 时间索引
    content_hash = Column(String(32), index=True)  # 内容哈希索引
    
    # 联合索引优化查询性能
    __table_args__ = (
        Index('idx_source_pubdate', 'source', 'published_at'),
    )
    
    def __repr__(self):
        return f"<NewsArticle {self.title[:50]}...>"