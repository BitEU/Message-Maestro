#!/usr/bin/env python3
"""
Base parser interface for messaging platforms
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    """Standardized message format"""
    id: str
    sender_id: str
    recipient_id: str
    text: str
    timestamp: datetime
    line_number: int
    media_urls: List[str] = None
    urls: List[str] = None
    
    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []
        if self.urls is None:
            self.urls = []

@dataclass
class Conversation:
    """Standardized conversation format"""
    id: str
    participants: List[str]
    messages: List[Message]
    line_number: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseParser(ABC):
    """Base class for all message parsers"""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the messaging platform (e.g., 'Twitter DM', 'Kik')"""
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Supported file extensions (e.g., ['.txt', '.json'])"""
        pass
    
    @property
    @abstractmethod
    def file_description(self) -> str:
        """Description for file dialog (e.g., 'Twitter DM Export')"""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str, content: str) -> bool:
        """
        Determine if this parser can handle the given file
        
        Args:
            file_path: Path to the file
            content: First few lines or full content of the file
            
        Returns:
            True if this parser can handle the file
        """
        pass
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Tuple[List[Conversation], List[str]]:
        """
        Parse the given file and extract conversations
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Tuple of (conversations_list, file_lines_list)
        """
        pass
    
    def get_primary_sender(self, conversation: Conversation) -> Optional[str]:
        """
        Determine the primary sender (usually the account owner)
        Default implementation returns sender with most messages
        """
        if not conversation.messages:
            return None
            
        sender_counts = {}
        for msg in conversation.messages:
            sender_counts[msg.sender_id] = sender_counts.get(msg.sender_id, 0) + 1
        
        return max(sender_counts.keys(), key=lambda x: sender_counts[x])
    
    def is_message_from_primary(self, message: Message, conversation: Conversation) -> bool:
        """
        Determine if a message is from the primary user (account owner).
        This method can be overridden by specific parsers for custom logic.
        
        Default implementation compares with get_primary_sender result.
        """
        primary_sender = self.get_primary_sender(conversation)
        return message.sender_id == primary_sender
    
    def format_timestamp(self, timestamp: datetime, format_type: str = 'short') -> str:
        """
        Format timestamp for display
        
        Args:
            timestamp: The datetime object
            format_type: 'short' for "3:45 PM", 'long' for full format
        """
        if format_type == 'short':
            return timestamp.strftime('%I:%M %p')
        else:
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')