"""
技术内容分析模块
实现基于NLP的技术相关性判断
"""
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba # 中文分词库
import re

class TechAnalyzer:
    """技术内容分析器"""
    def __init__(self):
        """初始化技术关键词库和停用词"""
        # 多语言技术关键词库
        self.tech_keywords = {
            'en': ['AI', 'Blockchain', 'Cybersecurity', '5G', 'IoT'],
            'zh': ['人工智能', '元宇宙', '芯片']
        }
        # 简易停用词表（实际项目建议使用外部文件）
        self.stop_words = {
            'en': {'the', 'and', 'this'},
            'zh': {'的', '是', '在'}
        }

    def preprocess_text(self, text, lang='en'):
        """
        文本预处理流程
        参数:
            text: 原始文本
            lang: 语言类型('en'/'zh')
        返回:
            str: 清洗后的文本
        """
        # 移除特殊字符（保留字母数字和空格）
        text = re.sub(r'[^\w\s]', '', text)
        # 中文分词
        if lang == 'zh':
            return ' '.join(jieba.cut(text)) # 生成分词结果
        return text.lower() # 英文转为小写

    def is_tech_related(self, text, lang='en'):
        """
        判断文本是否与技术相关
        参数:
            text: 待分析文本
            lang: 语言类型
        返回:
            bool: 是否属于技术内容
        """
        processed = self.preprocess_text(text, lang)
        tokens = processed.split()
        
        # 规则1：关键词直接匹配
        keyword_match = any(kw.lower() in processed for kw in self.tech_keywords[lang])
        
        # 规则2：TF-IDF特征分析
        try:
            # 初始化TF-IDF向量器（自动过滤停用词）
            tfidf = TfidfVectorizer(stop_words=list(self.stop_words[lang]))
            tfidf.fit([processed])  # 拟合单文档
            # 获取特征词列表
            features = tfidf.get_feature_names_out()
            # 筛选技术相关特征词
            tech_features = [f for f in features if f in self.tech_keywords[lang]]
            # 判断技术特征词占比是否超过阈值
            return keyword_match or (len(tech_features)/len(features) > 0.15) 
        except ValueError:  # 处理空文本异常
            return False