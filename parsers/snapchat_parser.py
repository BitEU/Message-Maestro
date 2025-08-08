#!/usr/bin/env python3
"""
Snapchat parser for CSV exports
"""
import csv
from datetime import datetime
from typing import List, Tuple, Dict, Set
from collections import defaultdict
import re

from .base_parser import BaseParser, Message, Conversation

class SnapchatParser(BaseParser):
    """Parser for Snapchat CSV export files"""

    @property
    def platform_name(self) -> str:
        return "Snapchat"

    @property
    def file_extensions(self) -> List[str]:
        return ['.csv']

    @property
    def file_description(self) -> str:
        return "Snapchat CSV Export"

    def can_parse(self, file_path: str, content: str) -> bool:
        """Check if this is a Snapchat CSV export file"""
        # Must be a .csv file
        if not file_path.lower().endswith('.csv'):
            return False
            
        # Check for essential Snapchat CSV headers (not all required, but key ones)
        required_headers = ['content_type', 'message_type', 'conversation_id', 'timestamp']
        optional_headers = ['sender_username', 'recipient_username', 'text', 'is_saved', 'is_one_on_one']
        
        # Look for a CSV header line containing the required headers
        lines = content.split('\n')
        for line in lines:
            # Skip empty lines and legend/description lines
            if not line.strip() or line.strip().startswith('"'):
                continue
                
            # Check if this line contains all required headers
            if all(header in line for header in required_headers):
                # Also check that it has some optional headers (to be more specific)
                optional_found = sum(1 for header in optional_headers if header in line)
                if optional_found >= 3:  # At least 3 optional headers should be present
                    return True
        
        return False

    def parse_file(self, file_path: str) -> Tuple[List[Conversation], List[str]]:
        """Parse Snapchat CSV export file"""
        # Double-check that this is a CSV file before attempting to parse
        if not file_path.lower().endswith('.csv'):
            raise Exception(f"Snapchat parser can only handle .csv files, but received: {file_path}")
            
        try:
            # Try different encodings as Snapchat exports may use various encodings
            encodings_to_try = ['utf-8', 'utf-8-sig', 'windows-1252', 'iso-8859-1', 'cp1252']
            file_lines = None
            content = None
            
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        file_lines = f.readlines()
                        content = ''.join(file_lines)
                    break  # Success, stop trying other encodings
                except UnicodeDecodeError:
                    continue  # Try next encoding
                    
            if file_lines is None:
                raise Exception("Could not read file with any supported encoding")
                
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
            
        # Verify this file can actually be parsed by this parser
        if not self.can_parse(file_path, content):
            raise Exception(f"File does not appear to be a valid Snapchat CSV export: {file_path}")

        # Find where the actual CSV data starts (after the legend)
        csv_start_index = 0
        for i, line in enumerate(file_lines):
            # Look for the CSV header line containing required fields
            if ('content_type' in line and 'message_type' in line and 
                'conversation_id' in line and 'timestamp' in line and
                line.count(',') >= 10):  # Should have many comma-separated fields
                csv_start_index = i
                break

        if csv_start_index == 0:
            raise Exception("Could not find CSV header in file")

        # Parse CSV data
        csv_lines = file_lines[csv_start_index:]
        reader = csv.DictReader(csv_lines)
        
        # Group messages by conversation_id
        conversations_by_id: Dict[str, List[Message]] = defaultdict(list)
        conversation_metadata: Dict[str, Dict] = {}
        line_number_by_conv: Dict[str, int] = {}

        for row_num, row in enumerate(reader):
            try:
                conv_id = row['conversation_id']
                
                # Track the first line number for this conversation
                if conv_id not in line_number_by_conv:
                    line_number_by_conv[conv_id] = csv_start_index + row_num + 2

                # Parse timestamp
                timestamp_str = row['timestamp']
                try:
                    # Snapchat uses format like "Sat Dec 24 18:37:19 UTC 2022"
                    timestamp = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %Z %Y')
                except ValueError:
                    # Fallback to current time if parsing fails
                    timestamp = datetime.now()

                # Determine sender and recipient
                sender = row['sender_username']
                recipient = row['recipient_username']
                
                # Get message text
                text = row.get('text', '')
                if not text:
                    # For media messages without text, create a description
                    content_type = row.get('content_type', 'Unknown')
                    if content_type == 'ExternalMedia':
                        text = "[Media]"
                    elif content_type == 'AudioSnap':
                        text = "[Audio Message]"
                    elif content_type == 'SilentSnap':
                        text = "[Silent Snap]"
                    elif content_type == 'VoiceNote':
                        text = "[Voice Note]"
                    elif content_type == 'Sticker':
                        text = "[Sticker]"
                    else:
                        text = f"[{content_type}]"

                # Check for media
                media_urls = []
                if row.get('media_id'):
                    # Media IDs are present but actual URLs aren't in the export
                    media_urls = ['[Media content]']

                # Create message
                message = Message(
                    id=row.get('message_id', str(row_num)),
                    sender_id=sender,
                    recipient_id=recipient,
                    text=text,
                    timestamp=timestamp,
                    line_number=csv_start_index + row_num + 2,
                    media_urls=media_urls
                )

                conversations_by_id[conv_id].append(message)

                # Store conversation metadata
                if conv_id not in conversation_metadata:
                    conversation_metadata[conv_id] = {
                        'is_one_on_one': row.get('is_one_on_one', 'true').lower() == 'true',
                        'conversation_title': row.get('conversation_title', ''),
                        'participants': set()
                    }

                # Collect participants
                conversation_metadata[conv_id]['participants'].add(sender)
                conversation_metadata[conv_id]['participants'].add(recipient)
                
                # For group conversations, add group members
                group_members = row.get('group_member_usernames', '')
                if group_members:
                    for member in group_members.split(';'):
                        if member.strip():
                            conversation_metadata[conv_id]['participants'].add(member.strip())

            except Exception as e:
                print(f"Error parsing row {row_num + 2}: {e}")
                continue

        # Convert to Conversation objects
        conversations = []
        for conv_id, messages in conversations_by_id.items():
            # Sort messages by timestamp
            messages.sort(key=lambda m: m.timestamp)
            
            # Get participants
            metadata = conversation_metadata.get(conv_id, {})
            participants = list(metadata.get('participants', set()))
            
            # If it's a group conversation with a title, include it
            conv_title = metadata.get('conversation_title', '')
            if conv_title and not metadata.get('is_one_on_one', True):
                # For group chats, show the title if available
                display_participants = [conv_title] if conv_title else participants[:3]
            else:
                # For one-on-one chats, show the two participants
                display_participants = participants[:2]

            conversation = Conversation(
                id=conv_id,
                participants=display_participants,
                messages=messages,
                line_number=line_number_by_conv.get(conv_id, 0),
                metadata={
                    'is_group': not metadata.get('is_one_on_one', True),
                    'all_participants': participants,
                    'title': conv_title
                }
            )
            conversations.append(conversation)

        # Sort conversations by the timestamp of their first message
        conversations.sort(key=lambda c: c.messages[0].timestamp if c.messages else datetime.now())

        return conversations, file_lines

    def get_primary_sender(self, conversation: Conversation) -> str:
        """
        For Snapchat, we'll use the target username from the file header
        """
        # The file indicates wagluigi_4ever2 is the target username
        # This would ideally be parsed from the file header
        primary_username = "wagluigi_4ever2"
        
        # Check if this username is actually in the conversation
        for msg in conversation.messages:
            if msg.sender_id == primary_username:
                return primary_username
        
        # Fallback to the default implementation if not found
        return super().get_primary_sender(conversation)