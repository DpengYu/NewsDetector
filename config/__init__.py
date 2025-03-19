"""
config 包初始化文件
用于导出 settings 对象，方便其他模块导入
"""

from .settings import settings  # 从 settings.py 导入 settings 对象

# 显式导出 settings 对象
__all__ = ['settings']