#!/usr/bin/env python3
"""
Statistics Calculator for Message Data

This module provides comprehensive statistical analysis of message conversations
including temporal pa        # Create stats object
        stats = MessageStats(
            total_messages=total_messages,
            messages_per_sender=dict(messages_per_sender),
            messages_by_hour=dict(messages_by_hour),
            messages_by_day_of_week=dict(messages_by_day_of_week),
            average_message_length=average_message_length,
            overall_average_length=overall_average_length,
            response_times=dict(response_times),
            average_response_times=average_response_times,
            conversation_count=len(self.conversations),
            date_range=date_range,
            most_active_hour=most_active_hour,
            most_active_day=most_active_day,
            most_prolific_sender=most_prolific_sender,
            fastest_responder=fastest_responder,
            sentiment_data=sentiment_data,
            sentiment_enabled=include_sentiment
        )vior, and response analytics.
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from dataclasses import dataclass

from parsers.base_parser import Conversation, Message

# Import sentiment analysis types if available
try:
    from .sentiment_analyzer import ConversationSentiment, SentimentScore
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    # Define placeholder types for type hints
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .sentiment_analyzer import ConversationSentiment, SentimentScore
    else:
        ConversationSentiment = Any
        SentimentScore = Any


@dataclass
class MessageStats:
    """Container for all calculated statistics"""
    total_messages: int
    messages_per_sender: Dict[str, int]
    messages_by_hour: Dict[int, int]  # Hour (0-23) -> count
    messages_by_day_of_week: Dict[int, int]  # Day (0=Monday, 6=Sunday) -> count
    average_message_length: Dict[str, float]  # sender -> avg length
    overall_average_length: float
    response_times: Dict[str, List[float]]  # sender -> list of response times in minutes
    average_response_times: Dict[str, float]  # sender -> avg response time in minutes
    conversation_count: int
    date_range: Tuple[Optional[datetime], Optional[datetime]]
    most_active_hour: int
    most_active_day: int
    most_prolific_sender: str
    fastest_responder: str
    # Sentiment analysis data
    sentiment_data: Optional[ConversationSentiment] = None
    sentiment_enabled: bool = False


class StatisticsCalculator:
    """Calculates comprehensive statistics from conversation data"""
    
    def __init__(self):
        self.conversations: List[Conversation] = []
        self.cached_stats: Optional[MessageStats] = None
        self._cache_valid = False
    
    def set_conversations(self, conversations: List[Conversation]) -> None:
        """Set the conversations to analyze and invalidate cache"""
        self.conversations = conversations
        self._cache_valid = False
        self.cached_stats = None
    
    def calculate_stats(self, force_refresh: bool = False, include_sentiment: bool = False, sentiment_analyzer=None) -> MessageStats:
        """
        Calculate comprehensive statistics from the loaded conversations
        
        Args:
            force_refresh: If True, recalculate even if cache is valid
            include_sentiment: If True, include sentiment analysis in results
            sentiment_analyzer: SentimentAnalyzer instance to use for sentiment analysis
            
        Returns:
            MessageStats object containing all calculated statistics
        """
        if self._cache_valid and not force_refresh and not include_sentiment and self.cached_stats:
            return self.cached_stats
        
        if not self.conversations:
            return self._empty_stats()
        
        # Initialize counters
        total_messages = 0
        messages_per_sender = defaultdict(int)
        messages_by_hour = defaultdict(int)
        messages_by_day_of_week = defaultdict(int)
        message_lengths = defaultdict(list)
        response_times = defaultdict(list)
        
        all_timestamps = []
        
        # Sentiment analysis data
        sentiment_data = None
        
        # Process each conversation
        for conversation in self.conversations:
            if not conversation.messages:
                continue
                
            # Sort messages by timestamp for response time calculation
            sorted_messages = sorted(conversation.messages, key=lambda m: m.timestamp)
            
            # Process sentiment analysis if requested
            if include_sentiment and sentiment_analyzer and SENTIMENT_AVAILABLE:
                try:
                    sentiment_data = sentiment_analyzer.analyze_conversation(conversation)
                except Exception as e:
                    print(f"Warning: Sentiment analysis failed: {e}")
                    sentiment_data = None
            
            # Process each message
            for i, message in enumerate(sorted_messages):
                total_messages += 1
                messages_per_sender[message.sender_id] += 1
                
                # Time-based statistics
                hour = message.timestamp.hour
                day_of_week = message.timestamp.weekday()
                messages_by_hour[hour] += 1
                messages_by_day_of_week[day_of_week] += 1
                all_timestamps.append(message.timestamp)
                
                # Message length statistics
                clean_text = self._clean_text(message.text)
                message_lengths[message.sender_id].append(len(clean_text))
                
                # Response time calculation
                if i > 0:
                    prev_message = sorted_messages[i - 1]
                    if prev_message.sender_id != message.sender_id:
                        # Different sender = response
                        time_diff = message.timestamp - prev_message.timestamp
                        response_minutes = time_diff.total_seconds() / 60
                        
                        # Count response times with more flexible thresholds
                        # For social media/messaging apps, responses can happen over days or weeks
                        if response_minutes < 43200:  # 30 days in minutes (more realistic for social platforms)
                            response_times[message.sender_id].append(response_minutes)
        
        # Calculate averages and derived statistics
        average_message_length = {}
        for sender, lengths in message_lengths.items():
            if lengths:
                average_message_length[sender] = sum(lengths) / len(lengths)
        
        overall_average_length = 0
        if message_lengths:
            all_lengths = [length for lengths in message_lengths.values() for length in lengths]
            if all_lengths:
                overall_average_length = sum(all_lengths) / len(all_lengths)
        
        average_response_times = {}
        for sender, times in response_times.items():
            if times:
                average_response_times[sender] = sum(times) / len(times)
        
        # Find extremes
        most_active_hour = max(messages_by_hour, key=messages_by_hour.get) if messages_by_hour else 0
        most_active_day = max(messages_by_day_of_week, key=messages_by_day_of_week.get) if messages_by_day_of_week else 0
        most_prolific_sender = max(messages_per_sender, key=messages_per_sender.get) if messages_per_sender else ""
        
        fastest_responder = ""
        if average_response_times:
            fastest_responder = min(average_response_times, key=average_response_times.get)
        
        # Date range
        date_range = (None, None)
        if all_timestamps:
            date_range = (min(all_timestamps), max(all_timestamps))
        
        # Create stats object
        stats = MessageStats(
            total_messages=total_messages,
            messages_per_sender=dict(messages_per_sender),
            messages_by_hour=dict(messages_by_hour),
            messages_by_day_of_week=dict(messages_by_day_of_week),
            average_message_length=average_message_length,
            overall_average_length=overall_average_length,
            response_times=dict(response_times),
            average_response_times=average_response_times,
            conversation_count=len(self.conversations),
            date_range=date_range,
            most_active_hour=most_active_hour,
            most_active_day=most_active_day,
            most_prolific_sender=most_prolific_sender,
            fastest_responder=fastest_responder,
            sentiment_data=sentiment_data,
            sentiment_enabled=include_sentiment
        )
        
        # Cache the results
        self.cached_stats = stats
        self._cache_valid = True
        
        return stats
    
    def _clean_text(self, text: str) -> str:
        """Clean message text for length calculation"""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def _empty_stats(self) -> MessageStats:
        """Return empty statistics when no data is available"""
        return MessageStats(
            total_messages=0,
            messages_per_sender={},
            messages_by_hour={},
            messages_by_day_of_week={},
            average_message_length={},
            overall_average_length=0.0,
            response_times={},
            average_response_times={},
            conversation_count=0,
            date_range=(None, None),
            most_active_hour=0,
            most_active_day=0,
            most_prolific_sender="",
            fastest_responder="",
            sentiment_data=None,
            sentiment_enabled=False
        )
    
    def get_hourly_activity_pattern(self) -> List[Tuple[str, int]]:
        """Get hourly activity pattern with formatted time labels"""
        if not self.cached_stats:
            self.calculate_stats()
        
        pattern = []
        for hour in range(24):
            count = self.cached_stats.messages_by_hour.get(hour, 0)
            time_label = f"{hour:02d}:00"
            pattern.append((time_label, count))
        
        return pattern
    
    def get_weekly_activity_pattern(self) -> List[Tuple[str, int]]:
        """Get weekly activity pattern with day names"""
        if not self.cached_stats:
            self.calculate_stats()
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        pattern = []
        
        for day_num in range(7):
            count = self.cached_stats.messages_by_day_of_week.get(day_num, 0)
            pattern.append((day_names[day_num], count))
        
        return pattern
    
    def get_top_senders(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top message senders sorted by message count"""
        if not self.cached_stats:
            self.calculate_stats()
        
        sorted_senders = sorted(
            self.cached_stats.messages_per_sender.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_senders[:limit]
    
    def get_response_time_summary(self) -> Dict[str, Dict[str, float]]:
        """Get detailed response time statistics for each sender"""
        if not self.cached_stats:
            self.calculate_stats()
        
        summary = {}
        for sender, times in self.cached_stats.response_times.items():
            if times:
                summary[sender] = {
                    'average': sum(times) / len(times),
                    'median': sorted(times)[len(times) // 2],
                    'min': min(times),
                    'max': max(times),
                    'count': len(times)
                }
        
        return summary
