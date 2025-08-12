#!/usr/bin/env python3
"""
Sentiment Analysis Module for Message-Maestro

Provides local sentiment analysis and conversation summarization using
NLTK and TextBlob for lightweight, fast sentiment analysis.
"""

import os
import sys
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re
from collections import defaultdict, Counter

# Core dependencies
import numpy as np

# Advanced NLP libraries for sentiment analysis
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords, wordnet
    from nltk.probability import FreqDist
    from nltk.tag import pos_tag
    from nltk.chunk import ne_chunk
    from nltk.stem import WordNetLemmatizer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as VaderAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from afinn import Afinn
    AFINN_AVAILABLE = True
except ImportError:
    AFINN_AVAILABLE = False

try:
    import emot
    EMOT_AVAILABLE = True
except ImportError:
    EMOT_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from parsers.base_parser import Conversation, Message


@dataclass
class SentimentScore:
    """Container for sentiment analysis results"""
    compound: float  # Overall sentiment (-1 to 1)
    positive: float  # Positive sentiment (0 to 1)
    negative: float  # Negative sentiment (0 to 1)
    neutral: float   # Neutral sentiment (0 to 1)
    confidence: float  # Confidence in the analysis (0 to 1)
    method: str  # Method used for analysis


@dataclass
class ConversationSentiment:
    """Sentiment analysis results for a conversation"""
    overall_sentiment: SentimentScore
    message_sentiments: List[Tuple[Message, SentimentScore]]
    sentiment_by_sender: Dict[str, SentimentScore]
    sentiment_timeline: List[Tuple[datetime, float]]  # Timestamp, compound score
    emotional_peaks: List[Tuple[Message, SentimentScore]]  # Most emotional messages
    summary: str
    keywords: List[Tuple[str, int]]  # Top keywords with frequency
    mood_transitions: List[Dict[str, Any]]  # Significant mood changes


class SentimentAnalyzer:
    """
    Lightweight sentiment analyzer using NLTK and TextBlob
    """
    
    def __init__(self, method: str = "auto", enable_advanced: bool = False):
        """
        Initialize the sentiment analyzer
        
        Args:
            method: "auto", "nltk", "textblob", "ensemble"
            enable_advanced: Enable advanced NLP features
        """
        self.method = method
        self.enable_advanced = enable_advanced
        self.analyzers = {}
        self.lemmatizer = None
        self.custom_lexicon = {}
        self.stop_words = set()
        
        # Simple method selection for now
        if NLTK_AVAILABLE and method in ["auto", "nltk", "ensemble"]:
            self._init_nltk_simple()
        elif TEXTBLOB_AVAILABLE and method in ["auto", "textblob"]:
            self.method = "textblob"
        else:
            self.method = "regex"
        
        self.available_methods = [self.method]
    
    def _init_nltk_simple(self):
        """Simple NLTK initialization"""
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        
        self.analyzers['nltk'] = SentimentIntensityAnalyzer()
        self.method = "nltk"
        
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            self.stop_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from'}
    
    def _check_available_methods(self) -> List[str]:
        """Check which sentiment analysis methods are available"""
        try:
            methods = []
            
            if NLTK_AVAILABLE:
                methods.append("nltk")
            
            if TEXTBLOB_AVAILABLE:
                methods.append("textblob")
                
            if VADER_AVAILABLE:
                methods.append("vader")
                
            if AFINN_AVAILABLE:
                methods.append("afinn")
                
            if len(methods) > 1:
                methods.append("ensemble")
                methods.append("hybrid")
            
            return methods
        except Exception as e:
            print(f"Error in _check_available_methods: {e}")
            return ["regex"]
    
    def _initialize_analyzers(self):
        """Initialize all available sentiment analysis methods"""
        if "nltk" in self.available_methods:
            self._init_nltk()
        
        if "textblob" in self.available_methods:
            self._init_textblob()
            
        if "vader" in self.available_methods:
            self._init_vader()
            
        if "afinn" in self.available_methods:
            self._init_afinn()
            
        # If no analyzers available, raise error
        if not self.analyzers:
            raise RuntimeError("No sentiment analysis methods available. Please install required libraries.")
    
    def _init_nltk(self):
        """Initialize advanced NLTK sentiment analyzer"""
        if not NLTK_AVAILABLE:
            return
        
        # Download required NLTK data
        datasets = [
            ('vader_lexicon', 'vader_lexicon'),
            ('punkt', 'tokenizers/punkt'),
            ('stopwords', 'corpora/stopwords'),
            ('averaged_perceptron_tagger', 'taggers/averaged_perceptron_tagger'),
            ('wordnet', 'corpora/wordnet'),
            ('omw-1.4', 'corpora/omw-1.4'),
        ]
        
        for dataset_name, dataset_path in datasets:
            try:
                nltk.data.find(dataset_path)
            except LookupError:
                try:
                    nltk.download(dataset_name, quiet=True)
                except:
                    pass
        
        self.analyzers['nltk'] = SentimentIntensityAnalyzer()
        
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            self.stop_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'will', 'your', 'what', 'when', 'where', 'which', 'their', 'would', 'there', 'could', 'should', 'after', 'before', 'just', 'about', 'into', 'some', 'them', 'other', 'than', 'then', 'also', 'been', 'only', 'very', 'over', 'such', 'being', 'through'}
    
    def _init_textblob(self):
        """Initialize TextBlob sentiment analyzer"""
        if not TEXTBLOB_AVAILABLE:
            return
        self.analyzers['textblob'] = True
    
    def _init_vader(self):
        """Initialize standalone VADER analyzer"""
        if not VADER_AVAILABLE:
            return
        self.analyzers['vader'] = VaderAnalyzer()
    
    def _init_afinn(self):
        """Initialize AFINN sentiment analyzer"""
        if not AFINN_AVAILABLE:
            return
        self.analyzers['afinn'] = Afinn()
    
    def _load_advanced_components(self):
        """Load advanced NLP components for enhanced analysis"""
        if NLTK_AVAILABLE:
            try:
                self.lemmatizer = WordNetLemmatizer()
            except:
                pass
    
    def _build_custom_lexicon(self):
        """Build custom sentiment lexicon with domain-specific terms"""
        # Enhanced lexicon for better sentiment detection
        self.custom_lexicon.update({
            # Intensifiers
            'absolutely': 1.5, 'completely': 1.3, 'totally': 1.3, 'extremely': 1.8,
            'incredibly': 1.5, 'amazingly': 1.4, 'perfectly': 1.2, 'exactly': 1.1,
            
            # Diminishers  
            'slightly': -0.3, 'somewhat': -0.2, 'kind of': -0.3, 'sort of': -0.3,
            'rather': -0.2, 'pretty': -0.1, 'fairly': -0.2,
            
            # Contextual sentiment
            'finally': 0.3, 'unfortunately': -0.8, 'hopefully': 0.6, 'obviously': 0.2,
            'surprisingly': 0.4, 'apparently': -0.1, 'definitely': 0.5,
            
            # Modern expressions
            'lit': 1.2, 'fire': 1.1, 'sick': 0.8, 'dope': 0.9, 'tight': 0.7,
            'cringe': -1.1, 'sus': -0.6, 'cap': -0.4, 'based': 0.8,
        })
    
    def analyze_message(self, message: Message) -> SentimentScore:
        """
        Analyze sentiment of a single message
        
        Args:
            message: Message object to analyze
            
        Returns:
            SentimentScore object with sentiment analysis results
        """
        text = message.text
        
        if not text or len(text.strip()) < 3:
            return SentimentScore(0.0, 0.0, 0.0, 1.0, 0.0, "none")
        
        # Clean text
        text = self._clean_text_simple(text)
        
        # Analyze based on method
        if self.method == "nltk" and 'nltk' in self.analyzers:
            return self._analyze_with_nltk_simple(text)
        elif self.method == "textblob" and TEXTBLOB_AVAILABLE:
            return self._analyze_with_textblob_simple(text)
        else:
            return self._analyze_with_regex(text)
    
    def _clean_text_simple(self, text: str) -> str:
        """Simple text cleaning"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # Remove mentions
        text = re.sub(r'@\w+', '', text)
        # Remove excessive punctuation but keep emoticons
        text = re.sub(r'([!?.]){3,}', r'\1', text)
        return text.strip()
    
    def _analyze_with_nltk_simple(self, text: str) -> SentimentScore:
        """Simple NLTK VADER analysis"""
        scores = self.analyzers['nltk'].polarity_scores(text)
        confidence = abs(scores['compound'])
        
        return SentimentScore(
            compound=scores['compound'],
            positive=scores['pos'],
            negative=scores['neg'],
            neutral=scores['neu'],
            confidence=min(confidence * 1.5, 1.0),
            method="nltk"
        )
    
    def _analyze_with_textblob_simple(self, text: str) -> SentimentScore:
        """Simple TextBlob analysis"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0:
            positive = polarity
            negative = 0
        else:
            positive = 0
            negative = abs(polarity)
        
        neutral = 1.0 - (positive + negative)
        
        return SentimentScore(
            compound=polarity,
            positive=positive,
            negative=negative,
            neutral=neutral,
            confidence=subjectivity,
            method="textblob"
        )
    
    def _advanced_text_preprocessing(self, text: str) -> str:
        """Advanced text preprocessing for enhanced sentiment analysis"""
        # Preserve emoticons and emojis first
        emoticons = re.findall(r'[:\;\=][oO\-\^]?[\)\(\]\[\{\}pPdDxX/\\3<>|*]', text)
        emoji_pattern = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)
        emojis = emoji_pattern.findall(text)
        
        # Clean text while preserving sentiment indicators
        text = re.sub(r'http[s]?://\S+', ' URL ', text)  # Replace URLs with token
        text = re.sub(r'@\w+', ' MENTION ', text)  # Replace mentions
        text = re.sub(r'#(\w+)', r'\1', text)  # Convert hashtags to words
        
        # Normalize repeated characters (but preserve sentiment intensity)
        text = re.sub(r'(.)\1{2,}', r'\1\1', text)  # Max 2 repetitions
        
        # Handle contractions
        contractions = {
            "n't": " not", "'re": " are", "'ve": " have", "'ll": " will",
            "'d": " would", "'m": " am", "can't": "cannot", "won't": "will not"
        }
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        # Restore emoticons and emojis
        text = text + ' ' + ' '.join(emoticons + emojis)
        
        return text.strip()
    
    def _get_multi_analyzer_scores(self, text: str) -> Dict[str, SentimentScore]:
        """Get sentiment scores from all available analyzers"""
        scores = {}
        
        if 'nltk' in self.analyzers:
            scores['nltk'] = self._analyze_with_nltk_advanced(text)
            
        if 'vader' in self.analyzers:
            scores['vader'] = self._analyze_with_vader(text)
            
        if 'textblob' in self.analyzers:
            scores['textblob'] = self._analyze_with_textblob_advanced(text)
            
        if 'afinn' in self.analyzers:
            scores['afinn'] = self._analyze_with_afinn(text)
        
        return scores
    
    def _analyze_with_nltk_advanced(self, text: str) -> SentimentScore:
        """Advanced NLTK analysis with custom lexicon and linguistic features"""
        if 'nltk' not in self.analyzers:
            return SentimentScore(0, 0, 0, 1, 0, "nltk_unavailable")
            
        scores = self.analyzers['nltk'].polarity_scores(text)
        
        # Apply custom lexicon modifications
        custom_boost = self._apply_custom_lexicon(text)
        scores['compound'] = np.clip(scores['compound'] + custom_boost, -1.0, 1.0)
        
        # Recalculate pos/neg based on adjusted compound
        if scores['compound'] > 0:
            scores['pos'] = min(scores['pos'] + abs(custom_boost), 1.0)
        else:
            scores['neg'] = min(scores['neg'] + abs(custom_boost), 1.0)
        
        # Normalize to ensure they sum to 1
        total = scores['pos'] + scores['neg'] + scores['neu']
        if total > 0:
            scores['pos'] /= total
            scores['neg'] /= total
            scores['neu'] /= total
        
        confidence = min(abs(scores['compound']) * 1.8, 1.0)
        
        return SentimentScore(
            compound=scores['compound'],
            positive=scores['pos'],
            negative=scores['neg'],
            neutral=scores['neu'],
            confidence=confidence,
            method="nltk_advanced"
        )
    
    def _analyze_with_vader(self, text: str) -> SentimentScore:
        """Analyze with standalone VADER"""
        if 'vader' not in self.analyzers:
            return SentimentScore(0, 0, 0, 1, 0, "vader_unavailable")
            
        scores = self.analyzers['vader'].polarity_scores(text)
        return SentimentScore(
            compound=scores['compound'],
            positive=scores['pos'],
            negative=scores['neg'],
            neutral=scores['neu'],
            confidence=abs(scores['compound']),
            method="vader"
        )
    
    def _analyze_with_afinn(self, text: str) -> SentimentScore:
        """Analyze with AFINN lexicon"""
        if 'afinn' not in self.analyzers:
            return SentimentScore(0, 0, 0, 1, 0, "afinn_unavailable")
            
        score = self.analyzers['afinn'].score(text)
        # Normalize AFINN score (-5 to +5 range) to compound score (-1 to +1)
        compound = np.clip(score / 5.0, -1.0, 1.0)
        
        if compound > 0:
            pos, neg = abs(compound), 0
        else:
            pos, neg = 0, abs(compound)
        
        neu = 1.0 - (pos + neg)
        
        return SentimentScore(
            compound=compound,
            positive=pos,
            negative=neg,
            neutral=max(neu, 0),
            confidence=min(abs(compound) * 1.2, 1.0),
            method="afinn"
        )
    
    def _analyze_with_textblob_advanced(self, text: str) -> SentimentScore:
        """Advanced TextBlob analysis with subjectivity weighting"""
        if 'textblob' not in self.analyzers:
            return SentimentScore(0, 0, 0, 1, 0, "textblob_unavailable")
            
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Weight polarity by subjectivity for more accurate sentiment
        weighted_polarity = polarity * subjectivity
        
        if weighted_polarity > 0:
            positive = abs(weighted_polarity)
            negative = 0
        else:
            positive = 0
            negative = abs(weighted_polarity)
        
        neutral = 1.0 - (positive + negative)
        
        # Use subjectivity as confidence - more subjective = more confident
        confidence = min(subjectivity * 1.5, 1.0)
        
        return SentimentScore(
            compound=weighted_polarity,
            positive=positive,
            negative=negative,
            neutral=max(neutral, 0),
            confidence=confidence,
            method="textblob_advanced"
        )
    
    def _apply_custom_lexicon(self, text: str) -> float:
        """Apply custom lexicon modifications to sentiment score"""
        boost = 0.0
        text_lower = text.lower()
        
        for term, weight in self.custom_lexicon.items():
            if term in text_lower:
                # Count occurrences for repeated emphasis
                count = text_lower.count(term)
                boost += weight * count * 0.1  # Scale down the boost
        
        return np.clip(boost, -0.5, 0.5)  # Limit boost impact
    
    def _apply_linguistic_enhancements(self, text: str, scores: Dict[str, SentimentScore]) -> Dict[str, SentimentScore]:
        """Apply advanced linguistic analysis to enhance sentiment scores"""
        enhanced_scores = scores.copy()
        
        if not self.enable_advanced or not NLTK_AVAILABLE:
            return enhanced_scores
        
        try:
            # Get POS tags for context analysis
            tokens = word_tokenize(text)
            pos_tags = pos_tag(tokens)
            
            # Analyze linguistic patterns
            linguistic_modifier = self._analyze_linguistic_patterns(tokens, pos_tags)
            
            # Apply modifications to all scores
            for method, score in enhanced_scores.items():
                modified_compound = np.clip(score.compound * (1 + linguistic_modifier), -1.0, 1.0)
                
                # Recalculate components
                if modified_compound > 0:
                    new_pos = min(score.positive * (1 + abs(linguistic_modifier)), 1.0)
                    new_neg = score.negative
                else:
                    new_pos = score.positive
                    new_neg = min(score.negative * (1 + abs(linguistic_modifier)), 1.0)
                
                new_neu = max(1.0 - (new_pos + new_neg), 0)
                
                enhanced_scores[method] = SentimentScore(
                    compound=modified_compound,
                    positive=new_pos,
                    negative=new_neg,
                    neutral=new_neu,
                    confidence=min(score.confidence * 1.2, 1.0),
                    method=f"{method}_enhanced"
                )
        
        except Exception:
            # If linguistic analysis fails, return original scores
            pass
        
        return enhanced_scores
    
    def _analyze_linguistic_patterns(self, tokens: list, pos_tags: list) -> float:
        """Analyze linguistic patterns for sentiment modification"""
        modifier = 0.0
        
        # Count sentiment-affecting POS patterns
        adjective_count = sum(1 for _, pos in pos_tags if pos.startswith('JJ'))
        adverb_count = sum(1 for _, pos in pos_tags if pos.startswith('RB'))
        
        # More descriptive language = higher confidence
        if len(tokens) > 0:
            descriptive_ratio = (adjective_count + adverb_count) / len(tokens)
            modifier += descriptive_ratio * 0.2
        
        # Look for negation patterns
        negation_words = {'not', 'no', 'never', 'nothing', 'nowhere', 'neither', 'nobody'}
        negation_count = sum(1 for token, _ in pos_tags if token.lower() in negation_words)
        
        if negation_count > 0:
            # Reduce confidence for negated statements
            modifier -= negation_count * 0.1
        
        return np.clip(modifier, -0.3, 0.3)
    
    def _ensemble_sentiment(self, scores: Dict[str, SentimentScore], text: str) -> SentimentScore:
        """Combine multiple sentiment scores using weighted ensemble"""
        if not scores:
            return SentimentScore(0, 0, 0, 1, 0, "ensemble_empty")
        
        # Define method weights based on reliability
        method_weights = {
            'nltk_advanced': 0.35,
            'vader': 0.30,
            'textblob_advanced': 0.20,
            'afinn': 0.15
        }
        
        weighted_compound = 0
        weighted_positive = 0
        weighted_negative = 0
        weighted_neutral = 0
        weighted_confidence = 0
        total_weight = 0
        
        for method, score in scores.items():
            base_method = method.replace('_enhanced', '').replace('_advanced', '')
            weight = method_weights.get(base_method, 0.1)
            
            # Boost weight for higher confidence scores
            confidence_boost = score.confidence * 0.5
            final_weight = weight * (1 + confidence_boost)
            
            weighted_compound += score.compound * final_weight
            weighted_positive += score.positive * final_weight
            weighted_negative += score.negative * final_weight
            weighted_neutral += score.neutral * final_weight
            weighted_confidence += score.confidence * final_weight
            total_weight += final_weight
        
        if total_weight > 0:
            final_compound = weighted_compound / total_weight
            final_positive = weighted_positive / total_weight
            final_negative = weighted_negative / total_weight
            final_neutral = weighted_neutral / total_weight
            final_confidence = min(weighted_confidence / total_weight, 1.0)
        else:
            return SentimentScore(0, 0, 0, 1, 0, "ensemble_failed")
        
        return SentimentScore(
            compound=np.clip(final_compound, -1.0, 1.0),
            positive=min(final_positive, 1.0),
            negative=min(final_negative, 1.0),
            neutral=min(final_neutral, 1.0),
            confidence=final_confidence,
            method="ensemble"
        )
    
    def _select_best_method(self, scores: Dict[str, SentimentScore]) -> str:
        """Select the best single method based on confidence and availability"""
        if not scores:
            return "regex"
        
        # Prefer methods with higher confidence
        best_method_name = max(scores.keys(), key=lambda method: scores[method].confidence)
        return best_method_name
    
    def _analyze_with_regex(self, text: str) -> SentimentScore:
        """Basic regex-based sentiment analysis as ultimate fallback"""
        text_lower = text.lower()
        
        # Simple positive/negative word lists
        positive_words = ['good', 'great', 'excellent', 'love', 'wonderful', 'best', 'happy', 'amazing', '😊', '😄', '❤️', '👍']
        negative_words = ['bad', 'terrible', 'hate', 'worst', 'awful', 'horrible', 'sad', 'angry', '😢', '😡', '👎', '💔']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return SentimentScore(0, 0, 0, 1, 0.1, "regex")
        
        compound = (pos_count - neg_count) / total
        positive = pos_count / total
        negative = neg_count / total
        neutral = 1.0 - (positive + negative)
        
        return SentimentScore(
            compound=compound,
            positive=positive,
            negative=negative,
            neutral=max(0, neutral),
            confidence=min(total / 10, 1.0),  # Confidence based on word count
            method="regex"
        )
    
    def analyze_conversation(self, conversation: Conversation) -> ConversationSentiment:
        """
        Perform comprehensive sentiment analysis on a conversation
        
        Args:
            conversation: Conversation object to analyze
            
        Returns:
            ConversationSentiment object with detailed analysis
        """
        if not conversation.messages:
            return self._empty_sentiment_result()
        
        # Analyze each message
        message_sentiments = []
        sentiment_by_sender = defaultdict(list)
        sentiment_timeline = []
        
        for message in conversation.messages:
            sentiment = self.analyze_message(message)
            message_sentiments.append((message, sentiment))
            sentiment_by_sender[message.sender_id].append(sentiment)
            sentiment_timeline.append((message.timestamp, sentiment.compound))
        
        # Calculate overall sentiment
        overall_sentiment = self._calculate_average_sentiment(
            [s for _, s in message_sentiments]
        )
        
        # Calculate per-sender sentiment
        sender_sentiments = {}
        for sender, sentiments in sentiment_by_sender.items():
            sender_sentiments[sender] = self._calculate_average_sentiment(sentiments)
        
        # Find emotional peaks (most positive and negative messages)
        emotional_peaks = self._find_emotional_peaks(message_sentiments)
        
        # Detect mood transitions
        mood_transitions = self._detect_mood_transitions(sentiment_timeline)
        
        # Generate summary
        summary = self._generate_conversation_summary(
            conversation, message_sentiments, overall_sentiment
        )
        
        # Extract keywords
        keywords = self._extract_keywords(conversation)
        
        return ConversationSentiment(
            overall_sentiment=overall_sentiment,
            message_sentiments=message_sentiments,
            sentiment_by_sender=sender_sentiments,
            sentiment_timeline=sentiment_timeline,
            emotional_peaks=emotional_peaks,
            summary=summary,
            keywords=keywords,
            mood_transitions=mood_transitions
        )
    
    def _calculate_average_sentiment(self, sentiments: List[SentimentScore]) -> SentimentScore:
        """Calculate average sentiment from a list of sentiment scores"""
        if not sentiments:
            return SentimentScore(0, 0, 0, 1, 0, "average")
        
        avg_compound = np.mean([s.compound for s in sentiments])
        avg_positive = np.mean([s.positive for s in sentiments])
        avg_negative = np.mean([s.negative for s in sentiments])
        avg_neutral = np.mean([s.neutral for s in sentiments])
        avg_confidence = np.mean([s.confidence for s in sentiments])
        
        return SentimentScore(
            compound=avg_compound,
            positive=avg_positive,
            negative=avg_negative,
            neutral=avg_neutral,
            confidence=avg_confidence,
            method="average"
        )
    
    def _find_emotional_peaks(self, message_sentiments: List[Tuple[Message, SentimentScore]], 
                             top_n: int = 5) -> List[Tuple[Message, SentimentScore]]:
        """Find the most emotionally charged messages"""
        # Sort by absolute compound score (most emotional)
        sorted_sentiments = sorted(
            message_sentiments,
            key=lambda x: abs(x[1].compound),
            reverse=True
        )
        
        return sorted_sentiments[:top_n]
    
    def _detect_mood_transitions(self, sentiment_timeline: List[Tuple[datetime, float]], 
                                threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Detect significant mood transitions in the conversation"""
        transitions = []
        
        if len(sentiment_timeline) < 2:
            return transitions
        
        for i in range(1, len(sentiment_timeline)):
            prev_time, prev_sentiment = sentiment_timeline[i-1]
            curr_time, curr_sentiment = sentiment_timeline[i]
            
            change = curr_sentiment - prev_sentiment
            
            if abs(change) >= threshold:
                transitions.append({
                    'timestamp': curr_time,
                    'from_sentiment': prev_sentiment,
                    'to_sentiment': curr_sentiment,
                    'change': change,
                    'direction': 'positive' if change > 0 else 'negative'
                })
        
        return transitions
    
    def _generate_conversation_summary(self, conversation: Conversation,
                                      message_sentiments: List[Tuple[Message, SentimentScore]],
                                      overall_sentiment: SentimentScore) -> str:
        """Generate a text summary of the conversation sentiment"""
        total_messages = len(conversation.messages)
        
        # Determine overall mood
        if overall_sentiment.compound > 0.5:
            mood = "very positive"
        elif overall_sentiment.compound > 0.1:
            mood = "positive"
        elif overall_sentiment.compound < -0.5:
            mood = "very negative"
        elif overall_sentiment.compound < -0.1:
            mood = "negative"
        else:
            mood = "neutral"
        
        # Count sentiment distribution
        positive_count = sum(1 for _, s in message_sentiments if s.compound > 0.1)
        negative_count = sum(1 for _, s in message_sentiments if s.compound < -0.1)
        neutral_count = total_messages - positive_count - negative_count
        
        # Create summary
        summary_parts = [
            f"This conversation has an overall {mood} tone (sentiment score: {overall_sentiment.compound:.2f}).",
            f"Out of {total_messages} messages: {positive_count} positive, {negative_count} negative, {neutral_count} neutral.",
        ]
        
        # Add participant analysis if multiple participants
        if len(conversation.participants) > 1:
            summary_parts.append(f"The conversation involves {len(conversation.participants)} participants.")
        
        # Note any significant mood shifts
        transitions = self._detect_mood_transitions(
            [(m.timestamp, s.compound) for m, s in message_sentiments]
        )
        if transitions:
            summary_parts.append(f"There were {len(transitions)} significant mood shifts during the conversation.")
        
        return " ".join(summary_parts)
    
    def _extract_keywords(self, conversation: Conversation, top_n: int = 10) -> List[Tuple[str, int]]:
        """Extract top keywords from the conversation"""
        if not NLTK_AVAILABLE:
            return []
        
        # Combine all message texts
        all_text = " ".join([msg.text for msg in conversation.messages])
        
        # Tokenize and filter
        try:
            tokens = word_tokenize(all_text.lower())
        except:
            # If punkt tokenizer not available, use simple split
            tokens = all_text.lower().split()
        
        # Filter out stopwords and short words
        if hasattr(self, 'stop_words'):
            filtered_tokens = [
                token for token in tokens 
                if token.isalnum() and len(token) > 3 and token not in self.stop_words
            ]
        else:
            # Basic filtering without NLTK stopwords
            common_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'will', 'your', 'what', 'when', 'where', 'which', 'their', 'would', 'there', 'could', 'should', 'after', 'before', 'just', 'about', 'into', 'some', 'them', 'other', 'than', 'then', 'also', 'been', 'only', 'very', 'over', 'such', 'being', 'through'}
            filtered_tokens = [
                token for token in tokens 
                if token.isalnum() and len(token) > 3 and token not in common_words
            ]
        
        # Count frequencies
        word_freq = Counter(filtered_tokens)
        
        return word_freq.most_common(top_n)
    
    def _empty_sentiment_result(self) -> ConversationSentiment:
        """Return empty sentiment result for conversations with no messages"""
        return ConversationSentiment(
            overall_sentiment=SentimentScore(0, 0, 0, 1, 0, "none"),
            message_sentiments=[],
            sentiment_by_sender={},
            sentiment_timeline=[],
            emotional_peaks=[],
            summary="No messages to analyze.",
            keywords=[],
            mood_transitions=[]
        )
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the sentiment analysis system"""
        return {
            'available_methods': self.available_methods,
            'current_method': self.method,
            'nltk_available': NLTK_AVAILABLE,
            'textblob_available': TEXTBLOB_AVAILABLE,
            'recommended_method': 'nltk' if NLTK_AVAILABLE else 'textblob'
        }
    
    def estimate_processing_time(self, message_count: int) -> float:
        """Estimate processing time in seconds for given number of messages"""
        # Simple estimates based on method
        if self.method == "nltk":
            return message_count * 0.01  # ~10ms per message
        elif self.method == "textblob":
            return message_count * 0.008  # ~8ms per message
        else:
            return message_count * 0.005  # ~5ms per message for regex