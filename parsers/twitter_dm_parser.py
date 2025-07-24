#!/usr/bin/env python3
"""
Twitter DM parser for exported Twitter DM files
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

from .base_parser import BaseParser, Message, Conversation

class TwitterDMParser(BaseParser):
    """Parser for Twitter DM export files"""
    
    @property
    def platform_name(self) -> str:
        return "Twitter DM"
    
    @property
    def file_extensions(self) -> List[str]:
        return ['.txt']
    
    @property
    def file_description(self) -> str:
        return "Twitter DM Export Files"
    
    def can_parse(self, file_path: str, content: str) -> bool:
        """Check if this is a Twitter DM export file"""
        # Look for PGP signature and conversation markers
        has_pgp = '-----BEGIN PGP SIGNED MESSAGE-----' in content
        has_conversation_marker = '**** conversationId:' in content
        has_dm_conversation = '"dmConversation"' in content
        
        return has_pgp and has_conversation_marker and has_dm_conversation
    
    def parse_file(self, file_path: str) -> Tuple[List[Conversation], List[str]]:
        """Parse Twitter DM export file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                file_lines = content.split('\n')
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
        
        # Extract content between PGP markers
        pgp_start = None
        pgp_end = None
        
        for i, line in enumerate(file_lines):
            if '-----BEGIN PGP SIGNED MESSAGE-----' in line:
                pgp_start = i
            elif '-----BEGIN PGP SIGNATURE-----' in line:
                pgp_end = i
                break
        
        if pgp_start is None or pgp_end is None:
            raise Exception("No PGP signed content found in file")
        
        dm_content = '\n'.join(file_lines[pgp_start:pgp_end])
        conversations = self._parse_conversations(dm_content, pgp_start, file_lines)
        
        return conversations, file_lines
    
    def _parse_conversations(self, content: str, start_line: int, file_lines: List[str]) -> List[Conversation]:
        """Parse conversations from PGP content"""
        conversations = []
        
        # Find conversation markers
        conv_pattern = r'\*\*\*\* conversationId: ([^\s]+) \*\*\*\*'
        conv_matches = list(re.finditer(conv_pattern, content))
        
        for match in conv_matches:
            conv_id = match.group(1)
            conv_start = match.start()
            
            # Find line number in original file
            lines_before = content[:conv_start].count('\n')
            line_num = start_line + lines_before + 1
            
            try:
                # Extract JSON block
                json_start = content.find('{', conv_start)
                if json_start == -1:
                    continue
                
                # Find matching closing brace
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                json_str = content[json_start:json_end]
                cleaned_json = self._clean_json_string(json_str)
                
                try:
                    conv_data = json.loads(cleaned_json)
                except json.JSONDecodeError:
                    # Try additional fixing
                    cleaned_json = self._fix_malformed_json(cleaned_json)
                    conv_data = json.loads(cleaned_json)
                
                # Convert to standardized format
                conversation = self._convert_to_conversation(conv_id, conv_data, line_num, file_lines)
                conversations.append(conversation)
                
            except Exception as e:
                # Create error conversation
                error_conv = Conversation(
                    id=conv_id,
                    participants=['Parse Error'],
                    messages=[],
                    line_number=line_num,
                    metadata={'error': str(e), 'raw_content': json_str[:500] + '...' if len(json_str) > 500 else json_str}
                )
                conversations.append(error_conv)
        
        return conversations
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean JSON string to fix common issues"""
        # Remove trailing commas before closing brackets/braces
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Remove invalid control characters but preserve newlines and tabs
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
        
        return json_str
    
    def _fix_malformed_json(self, json_str: str) -> str:
        """Fix malformed JSON strings"""
        lines = json_str.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Fix incomplete JSON strings - specifically the "id" field issue
            if '"id"' in line and line.count('"') == 3:  # Missing closing quote
                line = re.sub(r'"id"\s*:\s*"([^"]*),\s*$', r'"id" : "\1",', line)
            
            # More general fix for incomplete quoted values ending with comma
            elif line.count('"') % 2 != 0 and line.strip().endswith(','):
                match = re.search(r'"([^"]+)"\s*:\s*"([^"]*),\s*$', line)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    line = re.sub(r'"' + key + r'"\s*:\s*"[^"]*,\s*$', f'"{key}" : "{value}",', line)
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _convert_to_conversation(self, conv_id: str, conv_data: Dict, line_num: int, file_lines: List[str]) -> Conversation:
        """Convert Twitter DM data to standardized Conversation format"""
        participants = set()
        messages = []
        
        if 'dmConversation' in conv_data and 'messages' in conv_data['dmConversation']:
            for msg_data in conv_data['dmConversation']['messages']:
                if 'messageCreate' in msg_data:
                    msg_create = msg_data['messageCreate']
                    
                    # Extract participants
                    sender_id = msg_create.get('senderId', '')
                    recipient_id = msg_create.get('recipientId', '')
                    participants.add(sender_id)
                    participants.add(recipient_id)
                    
                    # Parse timestamp
                    timestamp_str = msg_create.get('createdAt', '')
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now()
                    
                    # Find line number for this message
                    msg_id = msg_create.get('id', '')
                    msg_line = self._find_message_line(msg_id, file_lines)
                    
                    # Create message
                    message = Message(
                        id=msg_id,
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        text=msg_create.get('text', ''),
                        timestamp=timestamp,
                        line_number=msg_line,
                        media_urls=msg_create.get('mediaUrls', []),
                        urls=[url.get('expanded', url.get('url', '')) for url in msg_create.get('urls', [])]
                    )
                    messages.append(message)
        
        return Conversation(
            id=conv_id,
            participants=list(participants),
            messages=messages,
            line_number=line_num
        )
    
    def _find_message_line(self, msg_id: str, file_lines: List[str]) -> int:
        """Find the line number containing a specific message ID"""
        for i, line in enumerate(file_lines):
            if msg_id in line:
                return i + 1
        return 0