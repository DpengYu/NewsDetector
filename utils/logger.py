"""
日志系统配置模块
配置统一格式的日志输出
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.settings import BASE_DIR

def configure_logging():
    """配置全局日志格式"""
    # 创建日志目录
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 基础格式配置
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    
    # 控制台处理器
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    
    # 文件处理器（按大小轮转）
    file = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file.setFormatter(formatter)
    
    # 根日志配置
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file)

def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    参数:
        name: 通常使用 __name__ 传递
    返回:
        logging.Logger 实例
    """
    return logging.getLogger(name)