"""
邮件通知服务模块
支持 Gmail 和 QQ 邮箱的可配置邮件发送功能
"""

import os
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict
from jinja2 import Template
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from utils.logger import get_logger
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 加载环境变量
load_dotenv()

# 初始化日志
logger = get_logger(__name__)

class EmailSender:
    """邮件发送器"""
    
    TEMPLATE = """
    <html>
    <body>
        <h2>科技热点速递 {{ date }}</h2>
        {% for item in news[:5] %}  <!-- 限制链接数量 -->
        <div style="margin-bottom: 20px;">
        <h3>{{ item.title|e }}</h3>  <!-- 转义特殊字符 -->
        <p>来源：{{ item.source|e }} | 发布时间：{{ item.published_at }}</p>
        <p>{{ item.description[:100]|e }}...</p>
        <a href="{{ item.url|e }}">阅读全文</a>
        </div>
        {% endfor %}
        <hr>
        <p style="color: #666; font-size: 12px;">
        此邮件为自动发送，如需退订请点击
        <a href="[UNSUBSCRIBE_LINK]">此处</a>。
        </p>
    </body>
    </html>
    """
    
    def __init__(self):
        """初始化邮件发送器"""
        self.email_type = os.getenv('EMAIL_TYPE', 'gmail').lower()
        self.recipients = os.getenv('RECIPIENTS', '').split(',')
        
        if self.email_type == 'gmail':
            self._init_gmail()
        elif self.email_type == 'qqmail':
            self._init_qqmail()
        else:
            raise ValueError(f"不支持的邮件类型: {self.email_type}")
            
    def _render_html(self, news: List[Dict]) -> str:
        """渲染邮件 HTML 内容"""
        template = Template(self.TEMPLATE)
        return template.render(
            news=news[:10],  # 最多发送 10 条
            date=datetime.now().strftime("%Y-%m-%d")
        )

    def _init_gmail(self):
        """初始化 Gmail 配置"""
        self.client_id = os.getenv('GMAIL_CLIENT_ID')
        self.client_secret = os.getenv('GMAIL_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GMAIL_REDIRECT_URI')
        self.notice_email = os.getenv('GMAIL_NOTICE_EMAIL')
        self.creds = self._get_gmail_credentials()

    def _init_qqmail(self):
        """初始化 QQ 邮箱配置"""
        self.smtp_server = os.getenv('QQMAIL_SMTP_SERVER')
        self.smtp_port = int(os.getenv('QQMAIL_SMTP_PORT', 465))
        self.notice_email = os.getenv('QQMAIL_NOTICE_EMAIL')
        self.email_password = os.getenv('QQMAIL_EMAIL_PASSWORD')

    def _get_gmail_credentials(self):
        """获取 Gmail OAuth 2.0 凭据"""
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.send'])
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    {
                        "web": {
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [self.redirect_uri]
                        }
                    },
                    ['https://www.googleapis.com/auth/gmail.send']
                )
                # 启动本地服务器，引导用户授权
                creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def _build_email(self, news: List[Dict]) -> MIMEMultipart:
        """构建邮件内容（根据实际需求完善）"""
        # 生成邮件内容
        html_content = self._render_html(news)
        
        # 转义 Emoji 和特殊字符
        html_content = html_content.replace('🧑🔬', '&#x1F9D1;&#x1F52C;')
        
        # 构建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"科技热点速递（{len(news)}条）"
        msg['From'] = self.notice_email
        msg['To'] = ', '.join(self.recipients)
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        return msg

    def send_digest(self, news: List[Dict]):
        try:
            msg = self._build_email(news)
            # 发送邮件
            self._send_via_qqmail(msg)
        except Exception as e:
            logger.error(f"邮件内容生成失败: {str(e)}")
            raise

    def _send_via_gmail(self, msg):
        """通过 Gmail API 发送邮件"""
        service = build('gmail', 'v1', credentials=self.creds)
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

    def _send_via_qqmail(self, msg):
        try:
            # 创建自定义 SSL 上下文
            context = ssl.create_default_context()
            context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')
            context.minimum_version = ssl.TLSVersion.TLSv1_2  # 强制 TLS 1.2+
            
            with smtplib.SMTP_SSL(
                host=self.smtp_server,
                port=self.smtp_port,
                context=context,
                timeout=10
            ) as server:
                # 登录并发送邮件
                server.login(self.notice_email, self.email_password)
                server.send_message(msg)
                logger.info("邮件已提交到服务器，请检查收件箱")

        except smtplib.SMTPException as e:
            if e.smtp_code == -1 and e.smtp_error == b'\x00\x00\x00':
                logger.warning(f"非标准响应，但邮件可能已到达")
                return  # 标记为成功
            else:
                logger.error(f"SMTP 通信失败: {str(e)}")
                raise
