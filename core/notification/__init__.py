from .email_sender import EmailSender  # 从 email_sender.py 导入 EmailSender 类
from .email_sender_AI import EmailSenderAI  # 从 email_sender.py 导入 EmailSender 类

# 显式导出 EmailSender 类
__all__ = ['EmailSender','EmailSenderAI']