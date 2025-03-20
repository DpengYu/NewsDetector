"""
邮件通知服务模块
使用 Gmail API 和 OAuth 2.0 凭据发送热点新闻摘要
支持无头模式（Headless Mode）和手动令牌加载
"""

import sys
import os
from datetime import datetime
from typing import List, Dict
from jinja2 import Template
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 初始化日志
from utils.logger import get_logger
logger = get_logger(__name__)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 配置 OAuth 2.0 凭据
CLIENT_ID = os.getenv('CLIENT_ID')  # 客户端 ID
CLIENT_SECRET = os.getenv('CLIENT_SECRET')  # 客户端密钥
REDIRECT_URI = os.getenv('REDIRECT_URI')  # 重定向 URI

# 配置权限范围
SCOPES = ['https://www.googleapis.com/auth/gmail.send']  # 发送邮件的权限

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
        """初始化邮件发送器"""
        self.creds = self._get_credentials()

    def _get_credentials(self):
        """
        获取 OAuth 2.0 凭据
        返回:
            Credentials: OAuth 2.0 凭据对象
        """
        creds = None
        # 检查是否有已保存的凭据
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # 如果没有有效凭据，引导用户登录
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # 刷新访问令牌
                creds.refresh(Request())
            else:
                # 初始化 OAuth 2.0 流程
                flow = InstalledAppFlow.from_client_config(
                    {
                        "web": {
                            "client_id": CLIENT_ID,
                            "client_secret": CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [REDIRECT_URI]
                        }
                    },
                    SCOPES
                )
                # 使用无头模式（Console 模式）进行认证
                creds = flow.run_console()
            
            # 保存凭据
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def send_digest(self, news: List[Dict]):
        """
        发送每日摘要邮件
        参数:
            news: 新闻数据列表
        """
        try:
            # 初始化 Gmail API 服务
            service = build('gmail', 'v1', credentials=self.creds)

            # 渲染 HTML 内容
            template = Template(self.TEMPLATE)
            html = template.render(
                news=news[:10],  # 最多发送 10 条
                date=datetime.now().strftime("%Y-%m-%d")
            )

            # 创建邮件内容
            msg = MIMEMultipart()
            msg['Subject'] = f"科技热点速递（{len(news)}条）"
            msg['From'] = os.getenv('NOTICE_EMAIL')  # 发件人邮箱
            msg['To'] = os.getenv('RECIPIENTS')  # 收件人列表
            msg.attach(MIMEText(html, 'html'))

            # 将邮件内容编码为 Base64
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

            # 发送邮件
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"成功发送邮件至 {os.getenv('RECIPIENTS')}")
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")

# 示例：发送邮件
if __name__ == "__main__":
    # 示例新闻数据
    news = [
        {
            'title': '测试新闻 1',
            'source': '测试来源',
            'published_at': '2023-10-01',
            'description': '这是测试新闻的描述。',
            'url': 'https://example.com'
        },
        {
            'title': '测试新闻 2',
            'source': '测试来源',
            'published_at': '2023-10-02',
            'description': '这是另一条测试新闻的描述。',
            'url': 'https://example.com'
        }
    ]

    # 发送邮件
    sender = EmailSender()
    sender.send_digest(news)