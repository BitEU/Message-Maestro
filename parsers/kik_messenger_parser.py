#!/usr/bin/env python3
"""
Kik Messenger parser for CSV exports
"""
import csv
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

from .base_parser import BaseParser, Message, Conversation

class KikMessengerParser(BaseParser):
    """Parser for Kik Messenger CSV export files"""

    def __init__(self):
        super().__init__()
        # Configuration for account owner - can be set by user
        self.account_owner = None

    def set_account_owner(self, username: str):
        """Set which Kik username is the account owner (for proper message direction)"""
        self.account_owner = username

    @property
    def platform_name(self) -> str:
        return "Kik Messenger"

    @property
    def file_extensions(self) -> List[str]:
        return ['.csv']

    @property
    def file_description(self) -> str:
        return "Kik Messenger CSV Export"

    def can_parse(self, file_path: str, content: str) -> bool:
        """Check if this is a Kik Messenger CSV export file"""
        # Must be a .csv file
        if not file_path.lower().endswith('.csv'):
            return False
            
        # Check for the exact Kik CSV header pattern
        # Look for a header line containing all required fields
        expected_headers = ['msg_id', 'sender_jid', 'receiver_jid', 'chat_type', 'msg', 'sent_at']
        
        # Split content into lines and check if any line contains all headers as CSV format
        lines = content.split('\n')
        for line in lines:
            # Check if this line looks like a CSV header with all required fields
            if all(header in line for header in expected_headers):
                # Additional check: should have commas separating the headers
                if line.count(',') >= len(expected_headers) - 1:
                    return True
        
        return False

    def parse_file(self, file_path: str) -> Tuple[List[Conversation], List[str]]:
        """Parse Kik Messenger CSV export file"""
        # Double-check that this is a CSV file before attempting to parse
        if not file_path.lower().endswith('.csv'):
            raise Exception(f"Kik parser can only handle .csv files, but received: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_lines = f.readlines()
                content = ''.join(file_lines)
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
            
        # Verify this file can actually be parsed by this parser
        if not self.can_parse(file_path, content):
            raise Exception(f"File does not appear to be a valid Kik CSV export: {file_path}")

        # Use DictReader to easily access columns by name
        reader = csv.DictReader(file_lines)
        
        # Group messages by conversation
        # A conversation is defined by the participants
        conversations_by_participants: Dict[frozenset, List[Message]] = defaultdict(list)
        line_number_by_participants: Dict[frozenset, int] = {}

        for i, row in enumerate(reader):
            try:
                # CRITICAL FIX: Use the actual sender and receiver from CSV
                sender = row['sender_jid']  # This is who SENT the message
                receiver = row['receiver_jid']  # This is who RECEIVED the message
                
                # For group chats, the conversation is with the group jid
                if row['chat_type'] == 'groupchat':
                    participants = frozenset([sender, receiver])
                else:
                    # For one-on-one chats, the participants are the sender and receiver
                    participants = frozenset([sender, receiver])

                if not participants in line_number_by_participants:
                    line_number_by_participants[participants] = i + 2 # 1-based index, plus header

                timestamp_str = row['sent_at']
                try:
                    # Handle timezone 'Z'
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+00:00'
                    timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    # Fallback for different timestamp formats if necessary
                    timestamp = datetime.now()

                # CRITICAL FIX: DO NOT swap sender/receiver - use them exactly as they are in the CSV
                message = Message(
                    id=row['msg_id'],
                    sender_id=sender,      # sender_jid from CSV = actual sender
                    recipient_id=receiver, # receiver_jid from CSV = actual recipient  
                    text=row['msg'],
                    timestamp=timestamp,
                    line_number=i + 2, # 1-based index, plus header
                )
                conversations_by_participants[participants].append(message)
            except KeyError as e:
                # Handle rows with missing columns if necessary
                print(f"Skipping row {i+2} due to missing key: {e}")
                continue

        # Convert grouped messages into Conversation objects
        conversations = []
        for participants, messages in conversations_by_participants.items():
            # Sort messages by timestamp
            messages.sort(key=lambda m: m.timestamp)
            
            # Create a unique ID for the conversation
            conv_id = "-".join(sorted(list(participants)))
            
            conversation = Conversation(
                id=conv_id,
                participants=list(participants),
                messages=messages,
                line_number=line_number_by_participants[participants]
            )
            conversations.append(conversation)
            
        # Sort conversations by the timestamp of the first message
        conversations.sort(key=lambda c: c.messages[0].timestamp if c.messages else datetime.now())

        return conversations, file_lines
    
    def get_primary_sender(self, conversation: Conversation) -> Optional[str]:
        """
        For Kik, we need a smarter way to determine the account owner.
        Since message count isn't reliable, we'll use multiple heuristics.
        """
        if not conversation.messages:
            return None
        
        senders = list(set(msg.sender_id for msg in conversation.messages))
        
        # If there are exactly 2 participants, we need to make an educated guess
        if len(senders) == 2:
            # Heuristic 1: The sender who appears first chronologically might be more likely to be the account owner
            # (since they often initiate conversations from their own device)
            first_message = min(conversation.messages, key=lambda m: m.timestamp)
            first_sender = first_message.sender_id
            
            # Debug info to help troubleshoot
            print(f"Kik Debug: Conversation participants: {senders}")
            print(f"Kik Debug: First message from: {first_sender} ('{first_message.text}')")
            print(f"Kik Debug: Selected as primary sender: {first_sender}")
            
            return first_sender
        
        # Fallback to default behavior for group chats or edge cases
        sender_counts = {}
        for msg in conversation.messages:
            sender_counts[msg.sender_id] = sender_counts.get(msg.sender_id, 0) + 1
        
        primary = max(sender_counts.keys(), key=lambda x: sender_counts[x])
        print(f"Kik Debug: Using message count fallback, selected: {primary}")
        return primary
    
    def is_message_from_primary(self, message: Message, conversation: Conversation) -> bool:
        """
        Override to provide Kik-specific logic for determining message direction.
        If account_owner is set, use that. Otherwise, fall back to heuristics.
        """
        # If user has specified which account is theirs, use that
        if self.account_owner:
            return message.sender_id == self.account_owner
        
        # Otherwise, use the heuristic-based primary sender detection
        primary_sender = self.get_primary_sender(conversation)
        return message.sender_id == primary_sender