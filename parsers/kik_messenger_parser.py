#!/usr/bin/env python3
"""
Kik Messenger parser for CSV exports
"""
import csv
from datetime import datetime
from typing import List, Tuple, Dict
from collections import defaultdict

from .base_parser import BaseParser, Message, Conversation

class KikMessengerParser(BaseParser):
    """Parser for Kik Messenger CSV export files"""

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
        # Check for characteristic headers
        expected_headers = ['msg_id', 'sender_jid', 'receiver_jid', 'chat_type', 'msg', 'sent_at']
        return all(header in content for header in expected_headers)

    def parse_file(self, file_path: str) -> Tuple[List[Conversation], List[str]]:
        """Parse Kik Messenger CSV export file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_lines = f.readlines()
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")

        # Use DictReader to easily access columns by name
        reader = csv.DictReader(file_lines)
        
        # Group messages by conversation
        # A conversation is defined by the participants
        conversations_by_participants: Dict[frozenset, List[Message]] = defaultdict(list)
        line_number_by_participants: Dict[frozenset, int] = {}

        for i, row in enumerate(reader):
            try:
                sender = row['sender_jid']
                receiver = row['receiver_jid']
                
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

                message = Message(
                    id=row['msg_id'],
                    sender_id=sender,
                    recipient_id=receiver,
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
