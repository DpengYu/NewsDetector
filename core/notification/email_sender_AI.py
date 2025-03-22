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
from json import JSONDecodeError
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

from google import genai
from zhipuai import ZhipuAI

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
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.ai_mode = os.getenv('AI_MODE')

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
        if not self.zhipu_api_key:
            logger.warning("未配置智谱API密钥")
            return {"title": "技术摘要", "overview": ""}

        try:
                # 在prompt中明确要求JSON格式
            prompt = f"""请严格按照以下JSON格式输出：{{
            "title": "总结内容，生成趣味性标题，标题内容必须与新闻内容相关(30字以内，带有emoj)",
            "overview": "今日热点及趋势总结...（一定要在300字以上）",
            "translations": {{
                翻译所有新闻数据的标题和摘要（包括source为github或newsapi），以以下格数输出
                "原标题1": {{
                    "translated_title": "中文标题",
                    "translated_description": "中文摘要"
                    }}
                "原标题2": {{
                "translated_title": "中文标题",
                "translated_description": "中文摘要"
                }}
                “...”
                “原标题n”{{
                "translated_title": "中文标题",
                "translated_description": "中文摘要"   
                }}
                }}
            }}

            请根据以下新闻数据生成内容：
            {json.dumps(news[:15], ensure_ascii=False, indent=2)}"""

            if self.ai_mode == "gemini":
                # gemini 2
                client = genai.Client(api_key=self.gemini_api_key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt)
                return self._parse_gemini_response(response)
            else:
                # 智谱AI    
                client = ZhipuAI(api_key=self.zhipu_api_key)
                response = client.chat.completions.create(
                    model="glm-4-flash",  # 使用官方支持的模型名称
                    messages=[
                        {
                            "role": "user",  # 必需字段
                            "content": prompt  # 必需字段
                        }
                    ],
                    temperature=0.3
                )
                return self._parse_zhipu_response(response)
        except Exception as e:
            logger.error(f"AI内容生成失败: {str(e)}")
            return {"title": "技术摘要", "overview": ""}

    def _parse_gemini_response(self, response) -> Dict:
        """解析Gemini响应"""
        try:
            # 验证候选内容存在性
            if not response.candidates:
                logger.error("Gemini未返回有效候选内容")
                return {"title": "无候选内容", "overview": ""}

            # 提取首个候选的文本内容
            candidate = response.candidates[0]
            parts = [part.text for part in candidate.content.parts]
            raw_content = "".join(parts).strip()

            # 记录原始响应（调试用）
            logger.debug(f"Gemini原始响应：{raw_content[:2000]}...")

            # 空内容处理
            if not raw_content:
                logger.error("收到空响应内容")
                return {"title": "空响应", "overview": ""}

            # 智能提取JSON内容
            start_idx = raw_content.find('{')
            end_idx = raw_content.rfind('}')
            if start_idx == -1 or end_idx == -1:
                logger.error("未检测到JSON结构")
                return {"title": "格式错误", "overview": raw_content[:500]}

            json_str = raw_content[start_idx:end_idx+1]
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 | 错误位置：{e.pos} | 内容片段：{json_str[e.pos-30:e.pos+30]}")
            return {"title": "解析失败", "overview": raw_content[:500]}
        except Exception as e:
            logger.error(f"解析异常：{str(e)}")
            return {"title": "系统错误", "overview": ""}

    def _parse_raw_content(self, raw: str) -> Dict:
        """通用文本解析"""
        try:
            return json.loads(raw)
        except JSONDecodeError:
            # 智能提取JSON内容
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                return json.loads(raw[start:end+1])
            else:
                return {
                    "title": "自动生成标题",
                    "overview": raw[:500],
                    "translations": {}
                }

    def _parse_ai_response(self, response) -> Dict:
        """增强版JSON解析"""
        try:
            raw_content = response.choices[0].message.content
            
            # 记录原始响应（调试用）
            logger.debug(f"原始响应内容：{raw_content[:5000]}...")  # 截断长内容
            
            # 预处理非法字符
            cleaned_content = raw_content.strip()
            cleaned_content = cleaned_content.replace('\x00', '').replace('\ufeff', '')
            
            # 处理多JSON对象情况
            if cleaned_content.count('{') > 1:
                first_brace = cleaned_content.find('{')
                last_brace = cleaned_content.rfind('}')
                cleaned_content = cleaned_content[first_brace:last_brace+1]
            
            # 解析JSON
            content = json.loads(cleaned_content)
            
            # 验证必需字段
            if not isinstance(content.get("translations", {}), dict):
                raise ValueError("translations字段格式错误")
                
            return {
                "title": content.get("title", "技术摘要"),
                "overview": content.get("overview", ""),
                "translations": content.get("translations", {})
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 | 错误位置：{e.pos} | 内容片段：{cleaned_content[e.pos-30:e.pos+30]}")
            return {"title": "解析失败", "overview": "", "translations": {}}
        except Exception as e:
            logger.error(f"响应解析异常：{str(e)}", exc_info=True)
            return {"title": "技术摘要", "overview": "", "translations": {}}


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
        normal_news = [n for n in news if n.get("source") != "GitHub"]

        # 获取AI生成内容
        news_send = github_news[:5] + normal_news[:10]
        ai_data = self._generate_ai_content(news_send)
        
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
            normal_news=normal_news[:10]
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
