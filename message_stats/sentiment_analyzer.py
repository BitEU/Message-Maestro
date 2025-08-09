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

# NLTK for sentiment analysis
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.probability import FreqDist
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# TextBlob as an alternative
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

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
    
    def __init__(self, method: str = "auto"):
        """
        Initialize the sentiment analyzer
        
        Args:
            method: "auto", "nltk", "textblob", or "hybrid"
        """
        self.method = method
        self.analyzer = None
        
        # Check available methods
        self.available_methods = self._check_available_methods()
        
        # Initialize the chosen method
        self._initialize_analyzer()
    
    def _check_available_methods(self) -> List[str]:
        """Check which sentiment analysis methods are available"""
        methods = []
        
        if NLTK_AVAILABLE:
            methods.append("nltk")
        
        if TEXTBLOB_AVAILABLE:
            methods.append("textblob")
        
        return methods
    
    def _initialize_analyzer(self):
        """Initialize the chosen sentiment analysis method"""
        if self.method == "auto":
            # Choose the best available method
            if "nltk" in self.available_methods:
                self._init_nltk()
            elif "textblob" in self.available_methods:
                self._init_textblob()
            else:
                raise RuntimeError("No sentiment analysis method available. Please install NLTK or TextBlob.")
        
        elif self.method == "nltk":
            self._init_nltk()
        
        elif self.method == "textblob":
            self._init_textblob()
        
        elif self.method == "hybrid":
            # Initialize multiple methods for comparison
            if "nltk" in self.available_methods:
                self._init_nltk()
    
    def _init_nltk(self):
        """Initialize NLTK sentiment analyzer"""
        if not NLTK_AVAILABLE:
            raise ImportError("NLTK is not installed. Run: pip install nltk")
        
        # Download required NLTK data (only once)
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            print("Downloading NLTK sentiment data...")
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        
        self.analyzer = SentimentIntensityAnalyzer()
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            # Fallback if stopwords not available
            self.stop_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'will', 'your', 'what', 'when', 'where', 'which', 'their', 'would', 'there', 'could', 'should', 'after', 'before', 'just', 'about', 'into', 'some', 'them', 'other', 'than', 'then', 'also', 'been', 'only', 'very', 'over', 'such', 'being', 'through'}
    
    def _init_textblob(self):
        """Initialize TextBlob sentiment analyzer"""
        if not TEXTBLOB_AVAILABLE:
            raise ImportError("TextBlob is not installed. Run: pip install textblob")
        
        # TextBlob doesn't need explicit initialization
        self.method = "textblob"
    
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
            # Return neutral for very short or empty messages
            return SentimentScore(
                compound=0.0,
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                confidence=0.0,
                method="none"
            )
        
        # Clean text
        text = self._clean_text(text)
        
        # Analyze based on available method
        if self.analyzer:  # NLTK
            return self._analyze_with_nltk(text)
        elif TEXTBLOB_AVAILABLE:
            return self._analyze_with_textblob(text)
        else:
            return self._analyze_with_regex(text)  # Fallback
    
    def _clean_text(self, text: str) -> str:
        """Clean text for sentiment analysis"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove mentions (for social media text)
        text = re.sub(r'@\w+', '', text)
        
        # Remove excessive punctuation but keep emoticons
        text = re.sub(r'([!?.]){3,}', r'\1', text)
        
        return text.strip()
    
    def _analyze_with_nltk(self, text: str) -> SentimentScore:
        """Analyze sentiment using NLTK VADER"""
        scores = self.analyzer.polarity_scores(text)
        
        # Calculate confidence based on the strength of sentiment
        confidence = abs(scores['compound'])
        
        return SentimentScore(
            compound=scores['compound'],
            positive=scores['pos'],
            negative=scores['neg'],
            neutral=scores['neu'],
            confidence=min(confidence * 1.5, 1.0),  # Scale confidence
            method="nltk"
        )
    
    def _analyze_with_textblob(self, text: str) -> SentimentScore:
        """Analyze sentiment using TextBlob"""
        blob = TextBlob(text)
        
        # TextBlob polarity ranges from -1 to 1
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Convert to our format
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
        # Rough estimates based on method
        if self.analyzer:  # NLTK
            return message_count * 0.01  # ~10ms per message
        else:
            return message_count * 0.005  # ~5ms per message for simple methods