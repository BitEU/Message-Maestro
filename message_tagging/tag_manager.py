"""
Core tag management functionality
"""

from typing import Dict, List, Optional, Tuple
import json
import os
from .tag_storage import TagStorage
from .tag_config import TagConfig


class TagManager:
    """Enhanced tag management with keyboard shortcuts and advanced features"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage = TagStorage(storage_path)
        self.config = TagConfig()
        
        # Load or initialize tags
        self.tags = self.storage.load_tags() or self._get_default_tags()
        self.message_tags = self.storage.load_message_tags() or {}
        
        # Save initial state if this is a fresh install
        if not self.storage.tags_exist():
            self.save_data()
    
    def _get_default_tags(self) -> Dict[str, Dict]:
        """Get default tag configuration"""
        return self.config.get_default_tags()
    
    def get_tags(self) -> Dict[str, Dict]:
        """Get all tags with their metadata"""
        return self.tags.copy()
    
    def get_tag(self, tag_id: str) -> Optional[Dict]:
        """Get a specific tag by ID"""
        return self.tags.get(tag_id)
    
    def update_tag(self, tag_id: str, name: str, color: str, shortcut: str = None):
        """Update a tag's properties"""
        if tag_id in self.tags:
            self.tags[tag_id].update({
                'name': name,
                'color': color,
                'shortcut': shortcut,
                'modified': True
            })
            self.save_data()
    
    def create_tag(self, name: str, color: str, shortcut: str = None) -> str:
        """Create a new tag and return its ID"""
        # Find next available ID
        tag_id = str(len(self.tags))
        while tag_id in self.tags:
            tag_id = str(int(tag_id) + 1)
        
        self.tags[tag_id] = {
            'name': name,
            'color': color,
            'shortcut': shortcut,
            'created': True
        }
        self.save_data()
        return tag_id
    
    def delete_tag(self, tag_id: str) -> bool:
        """Delete a tag and remove all its assignments"""
        if tag_id not in self.tags:
            return False
        
        # Remove all message assignments for this tag
        keys_to_remove = [
            key for key, assigned_tag_id in self.message_tags.items() 
            if assigned_tag_id == tag_id
        ]
        for key in keys_to_remove:
            del self.message_tags[key]
        
        # Remove the tag itself
        del self.tags[tag_id]
        self.save_data()
        return True
    
    def tag_message(self, conv_id: str, msg_id: str, tag_id: str) -> bool:
        """Tag a message with the specified tag"""
        if tag_id not in self.tags:
            return False
        
        key = (conv_id, msg_id)
        self.message_tags[key] = tag_id
        self.save_data()
        return True
    
    def untag_message(self, conv_id: str, msg_id: str) -> bool:
        """Remove tag from a message"""
        key = (conv_id, msg_id)
        if key in self.message_tags:
            del self.message_tags[key]
            self.save_data()
            return True
        return False
    
    def get_message_tag(self, conv_id: str, msg_id: str) -> Optional[Dict]:
        """Get tag information for a specific message"""
        key = (conv_id, msg_id)
        tag_id = self.message_tags.get(key)
        
        if tag_id and tag_id in self.tags:
            tag_info = self.tags[tag_id].copy()
            tag_info['id'] = tag_id
            return tag_info
        return None
    
    def get_tagged_messages(self, tag_id: str = None) -> List[Tuple[str, str]]:
        """Get all messages with a specific tag (or all tagged messages)"""
        if tag_id is None:
            return list(self.message_tags.keys())
        
        return [
            key for key, assigned_tag_id in self.message_tags.items() 
            if assigned_tag_id == tag_id
        ]
    
    def get_tag_usage_count(self, tag_id: str) -> int:
        """Get the number of messages tagged with this tag"""
        return len(self.get_tagged_messages(tag_id))
    
    def bulk_tag_messages(self, message_keys: List[Tuple[str, str]], tag_id: str) -> int:
        """Tag multiple messages at once. Returns number of successfully tagged messages."""
        if tag_id not in self.tags:
            return 0
        
        count = 0
        for conv_id, msg_id in message_keys:
            key = (conv_id, msg_id)
            self.message_tags[key] = tag_id
            count += 1
        
        if count > 0:
            self.save_data()
        return count
    
    def bulk_untag_messages(self, message_keys: List[Tuple[str, str]]) -> int:
        """Remove tags from multiple messages at once. Returns number of untagged messages."""
        count = 0
        for conv_id, msg_id in message_keys:
            key = (conv_id, msg_id)
            if key in self.message_tags:
                del self.message_tags[key]
                count += 1
        
        if count > 0:
            self.save_data()
        return count
    
    def get_tag_statistics(self) -> Dict:
        """Get comprehensive tag usage statistics"""
        stats = {
            'total_tags': len(self.tags),
            'total_tagged_messages': len(self.message_tags),
            'tag_usage': {},
            'most_used_tag': None,
            'least_used_tag': None
        }
        
        # Calculate usage for each tag
        for tag_id, tag_info in self.tags.items():
            usage_count = self.get_tag_usage_count(tag_id)
            stats['tag_usage'][tag_id] = {
                'name': tag_info['name'],
                'count': usage_count,
                'color': tag_info['color']
            }
        
        # Find most and least used tags
        if stats['tag_usage']:
            sorted_usage = sorted(
                stats['tag_usage'].items(), 
                key=lambda x: x[1]['count'], 
                reverse=True
            )
            stats['most_used_tag'] = sorted_usage[0] if sorted_usage else None
            stats['least_used_tag'] = sorted_usage[-1] if sorted_usage else None
        
        return stats
    
    def export_configuration(self) -> Dict:
        """Export complete tag configuration for backup/sharing"""
        return {
            'tags': self.tags,
            'message_tags': {
                f"{key[0]}:{key[1]}": value 
                for key, value in self.message_tags.items()
            },
            'version': '1.0.0',
            'exported_at': __import__('datetime').datetime.now().isoformat()
        }
    
    def import_configuration(self, config_data: Dict) -> bool:
        """Import tag configuration from backup/sharing"""
        try:
            if 'tags' in config_data:
                self.tags = config_data['tags']
            
            if 'message_tags' in config_data:
                # Convert string keys back to tuples
                self.message_tags = {
                    tuple(key.split(':', 1)): value 
                    for key, value in config_data['message_tags'].items()
                }
            
            self.save_data()
            return True
        except Exception:
            return False
    
    def save_data(self):
        """Save all tag data to storage"""
        self.storage.save_tags(self.tags)
        self.storage.save_message_tags(self.message_tags)
