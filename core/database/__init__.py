"""
core.database 包初始化文件
导出数据库操作类
"""

from .crud import NewsDatabase  # 从 crud.py 导入 NewsDatabase 类

# 显式导出 NewsDatabase 类
__all__ = ['NewsDatabase']