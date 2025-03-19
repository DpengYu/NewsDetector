from sklearn.feature_extraction.text import TfidfVectorizer
import jieba
import re

class TechAnalyzer:
    def __init__(self):
        self.tech_keywords = {
            'en': ['AI', 'Blockchain', 'Cybersecurity', '5G', 'IoT'],
            'zh': ['人工智能', '元宇宙', '芯片']
        }
        self.stop_words = {
            'en': {'the', 'and', 'this'},
            'zh': {'的', '是', '在'}
        }

    def preprocess_text(self, text, lang='en'):
        # 清洗特殊字符
        text = re.sub(r'[^\w\s]', '', text)
        # 中文分词
        if lang == 'zh':
            return ' '.join(jieba.cut(text))
        return text.lower()

    def is_tech_related(self, text, lang='en'):
        processed = self.preprocess_text(text, lang)
        tokens = processed.split()
        
        # 关键词匹配
        keyword_match = any(kw.lower() in processed for kw in self.tech_keywords[lang])
        
        # TF-IDF分析
        tfidf = TfidfVectorizer(stop_words=list(self.stop_words[lang]))
        try:
            tfidf.fit([processed])
            features = tfidf.get_feature_names_out()
            tech_features = [f for f in features if f in self.tech_keywords[lang]]
            return keyword_match or (len(tech_features)/len(features) > 0.15
        except ValueError:
            return False