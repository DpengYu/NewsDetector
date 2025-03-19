"""
邮件通知服务模块
实现热点新闻的邮件摘要发送
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings
from typing import List, Dict
from jinja2 import Template
from utils.logger import get_logger

logger = get_logger(__name__)

class EmailSender:
    """邮件发送器"""
    
    TEMPLATE = """
    <html>
      <body>
        <h2>科技热点速递 {{ date }}</h2>
        {% for item in news %}
        <div style="margin-bottom: 20px;">
          <h3>{{ item.title }}</h3>
          <p>来源：{{ item.source }} | 发布时间：{{ item.published_at }}</p>
          <p>{{ item.description[:100] }}...</p>
          <a href="{{ item.url }}">阅读全文</a>
        </div>
        {% endfor %}
      </body>
    </html>
    """
    
    def __init__(self):
        self.config = settings.EMAIL_CONFIG
    
    def send_digest(self, news: List[Dict], recipients: List[str]):
        """
        发送每日摘要邮件
        参数:
            news: 新闻数据列表
            recipients: 收件人列表
        """
        msg = MIMEMultipart()
        msg['Subject'] = f"科技热点速递（{len(news)}条）"
        msg['From'] = self.config['sender']
        msg['To'] = ', '.join(recipients)
        
        # 渲染HTML内容
        template = Template(self.TEMPLATE)
        html = template.render(
            news=news[:10],  # 最多发送10条
            date=datetime.now().strftime("%Y-%m-%d")
        )
        msg.attach(MIMEText(html, 'html'))
        
        try:
            with smtplib.SMTP(self.config['smtp_server'], self.config['port']) as server:
                server.starttls()
                server.login(self.config['sender'], self.config['password'])
                server.send_message(msg)
            logger.info(f"成功发送邮件至{len(recipients)}个收件人")
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")