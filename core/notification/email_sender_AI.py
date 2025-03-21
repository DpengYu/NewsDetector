"""
邮件通知服务模块（集成智谱AI版）
支持热点摘要生成和中英双语内容推送
"""

import os
import smtplib
import base64
import requests
import json
import certifi
import smtplib
import ssl
from urllib3.util.ssl_ import create_urllib3_context
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from jinja2 import Template, Environment
from jinja2.loaders import FileSystemLoader
from jinja2.exceptions import TemplateNotFound 
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from utils.logger import get_logger


# 加载环境变量
load_dotenv()

# 初始化日志
logger = get_logger(__name__)

class EmailSenderAI:
    """邮件发送器"""
    def __init__(self):
        """初始化邮件发送器"""
        self.email_type = os.getenv('EMAIL_TYPE', 'gmail').lower()
        self.recipients = os.getenv('RECIPIENTS', '').split(',')
        self.template_env = self._init_template_env()
        self.zhipu_api_key = os.getenv('ZHIPU_API_KEY')

        if self.email_type == 'gmail':
            self._init_gmail()
        elif self.email_type == 'qqmail':
            self._init_qqmail()
        else:
            raise ValueError(f"不支持的邮件类型: {self.email_type}")

    def _init_template_env(self) -> Environment:
        # 路径验证逻辑保持不变
        current_file = Path(__file__).resolve()
        possible_paths = [
            current_file.parent.parent / "templates",
            current_file.parent / "templates", 
            Path("/etc/app/templates")
        ]
        
        for path in possible_paths:
            if path.exists():
                template_path = path
                break
        else:
            raise FileNotFoundError(f"找不到模板目录，已尝试：{possible_paths}")

        logger.info(f"使用模板路径：{template_path}")
        
        # 创建基础环境
        env = Environment(
            loader=FileSystemLoader(template_path),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 添加自定义过滤器
        env.filters['format_datetime'] = self._format_datetime
        
        return env

    def _format_datetime(self, value: Optional[str]) -> str:
        """安全的时间格式化过滤器"""
        # 添加空值处理
        if not value or not isinstance(value, str):
            return "时间未提供"
        
        # 支持更多日期格式
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",  # ISO8601
            "%Y-%m-%d %H:%M:%S",   # 普通格式
            "%Y-%m-%d",            # 仅日期
            "%b %d, %Y",           # Mar 22, 2025
            "%d/%m/%Y"             # 22/03/2025
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%m/%d %H:%M") if any(c in fmt for c in ['H','M','S']) else dt.strftime("%m/%d")
            except ValueError:
                continue
        
        # 回退方案：截取有效部分
        try:
            return value[:16]  # 截取前16个字符（2025-03-22T00:57）
        except:
            return value

    def _generate_ai_content(self, news: List[Dict]) -> Dict:
        """生成AI内容（带重试机制）"""
        if not self.zhipu_api_key:
            logger.warning("ZHIPU_API_KEY not configured, skipping AI content")
            return {"title": "Tech Digest", "overview": ""}

        # 明确定义headers
        headers = {
            "Authorization": f"Bearer {self.zhipu_api_key.strip()}",
            "Content-Type": "application/json"
        }

        # 序列化新闻数据
        try:
            news_data = json.dumps(news[:15], 
                ensure_ascii=False, 
                indent=2,
                default=str  # 处理无法序列化的字段
            )
            prompt = f"""请执行以下任务：
            1. 生成吸引人的邮件标题（20字内，包含emoji）
            2. 总结技术趋势（120字内，带3个相关emoji）
            3. 专业翻译标题和摘要（保留术语）
            
            新闻数据：
            {json.dumps(news[:15], ensure_ascii=False, indent=2)}
            
            输出JSON格式：
            {{
                "title": "生成标题",
                "overview": "趋势总结...",
                "translations": {{
                    "原标题1": {{
                        "translated_title": "中文标题",
                        "translated_description": "中文摘要"
                        }},
                        "原标题2": {{ ... }}
                        }}
                        }}"""
            payload = {
                "model": "chatglm-pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        except Exception as e:
            logger.error(f"构造请求负载失败: {str(e)}")
            # 降级为最小payload
            payload = {
                "model": "chatglm-pro",
                "messages": [{"role": "user", "content": "生成默认摘要"}],
                "temperature": 0.5
            }
        for attempt in range(3):
            try:
    # 创建自定义SSL上下文
                ssl_context = create_urllib3_context()
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                
                # 创建适配器
                session = requests.Session()
                session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
                # 在请求中使用
                response = requests.post(
                    "https://api.zhipuai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=15,
                    verify=certifi.where(),
                )
                response.raise_for_status()
                return self._parse_ai_response(response.json())
            except Exception as e:
                logger.warning(f"AI API attempt {attempt+1} failed: {str(e)}")
                if attempt == 2:
                    logger.error("All AI API attempts failed")
                    return {"title": "Tech Digest", "overview": ""}


    def _parse_ai_response(self, response: Dict) -> Dict:
        """解析AI响应"""
        try:
            content = json.loads(response['choices'][0]['message']['content'])
            return {
                "title": content.get("title", "Tech Digest"),
                "overview": content.get("overview", ""),
                "translations": content.get("translations", {})
            }
        except Exception as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            return {"title": "Tech Digest", "overview": "", "translations": {}}


    def _render_html(self, news: List[Dict], overview: str) -> str:
        """渲染邮件 HTML 内容"""
        template_news = Template(self.TEMPLATE_NEWS)
        template_github = Template(self.TEMPLATE_GITHUB)
        # 过滤出不同类型的新闻
        normal_news = [item for item in news if item.get("source") == "NewsAPI"]
        github_news = [item for item in news if item.get("source") == "GitHub"]
        # 渲染 GitHub 新闻
        github_content = template_github.render(
            news=github_news[:10],  # 最多发送 10 条
            date=datetime.now().strftime("%Y-%m-%d")
        )
        # 渲染普通新闻
        news_content = template_news.render(
            news=normal_news[:10],  # 最多发送 10 条
            date=datetime.now().strftime("%Y-%m-%d"),
            overview=overview
        )
        # 合并内容
        contents = github_content + news_content
        return contents

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
        try:
            template = self.template_env.get_template("email_template.html")
        except TemplateNotFound as e:  # 使用正确的异常名称
            logger.error(f"模板文件不存在：{str(e)}")
            logger.error(f"当前搜索路径：{self.template_env.loader.searchpath}")
            raise
        # 分类处理新闻数据
        github_news = [n for n in news if n.get("source") == "GitHub"]
        normal_news = [n for n in news if n.get("source") != "NewsAPI"]

        # 获取AI生成内容
        ai_data = self._generate_ai_content(news)
        
        # 合并翻译数据
        translations = ai_data.get("translations", {})
        for item in news:
            if item["title"] in translations:
                item.update(translations[item["title"]])

        # 渲染模板
        template = self.template_env.get_template("email_template.html")
        html_content = template.render(
            date=datetime.now().strftime("%Y-%m-%d"),
            ai_title=ai_data["title"],
            ai_overview=ai_data["overview"],
            github_news=github_news[:5],
            normal_news=normal_news[:5]
        )

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{ai_data['title']} | {datetime.now().strftime('%m/%d')}"
        msg['From'] = self.notice_email
        msg['To'] = ', '.join(self.recipients)
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        return msg


    def send_digest(self, news: List[Dict]):
        try:
            msg = self._build_email(news)
            # 发送邮件
            if self.email_type == 'gmail':
                self._send_via_gmail(msg)
            elif self.email_type == 'qqmail':
                self._send_via_qqmail(msg)
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
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
