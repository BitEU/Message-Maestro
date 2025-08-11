"""
Tag storage and persistence functionality
"""

import json
import os
from typing import Dict, Optional, Tuple
from pathlib import Path


class TagStorage:
    """Handles saving and loading tag data"""
    
    def __init__(self, case_file_path: Optional[str] = None):
        self.case_file_path = case_file_path
        
        if case_file_path:
            # Store tag data next to the case file
            case_file = Path(case_file_path)
            case_dir = case_file.parent
            case_name = case_file.stem
            
            self.tags_file = case_dir / f"{case_name}_tags.json"
            self.message_tags_file = case_dir / f"{case_name}_message_tags.json" 
            self.config_file = case_dir / f"{case_name}_tag_config.json"
        else:
            # Fallback to global storage if no case file specified
            self.storage_dir = Path.cwd() / 'tags_data'
            self.storage_dir.mkdir(exist_ok=True)
            
            self.tags_file = self.storage_dir / 'tags.json'
            self.message_tags_file = self.storage_dir / 'message_tags.json'
            self.config_file = self.storage_dir / 'tag_config.json'
    
    def tags_exist(self) -> bool:
        """Check if tag files already exist"""
        return self.tags_file.exists() or self.message_tags_file.exists()
    
    def save_tags(self, tags: Dict[str, Dict]) -> bool:
        """Save tags to storage"""
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(tags, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving tags: {e}")
            return False
    
    def load_tags(self) -> Optional[Dict[str, Dict]]:
        """Load tags from storage"""
        try:
            if self.tags_file.exists():
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading tags: {e}")
        return None
    
    def save_message_tags(self, message_tags: Dict[Tuple[str, str], str]) -> bool:
        """Save message tag assignments to storage"""
        try:
            # Convert tuple keys to strings for JSON serialization
            serializable_data = {
                f"{key[0]}:{key[1]}": value 
                for key, value in message_tags.items()
            }
            
            with open(self.message_tags_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving message tags: {e}")
            return False
    
    def load_message_tags(self) -> Optional[Dict[Tuple[str, str], str]]:
        """Load message tag assignments from storage"""
        try:
            if self.message_tags_file.exists():
                with open(self.message_tags_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert string keys back to tuples
                return {
                    tuple(key.split(':', 1)): value 
                    for key, value in data.items()
                }
        except Exception as e:
            print(f"Error loading message tags: {e}")
        return None
    
    def save_config(self, config: Dict) -> bool:
        """Save configuration to storage"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def load_config(self) -> Optional[Dict]:
        """Load configuration from storage"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        return None
    
    def backup_data(self, backup_path: str) -> bool:
        """Create a backup of all tag data"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(exist_ok=True)
            
            # Copy all data files
            import shutil
            if self.tags_file.exists():
                shutil.copy2(self.tags_file, backup_dir / 'tags.json')
            if self.message_tags_file.exists():
                shutil.copy2(self.message_tags_file, backup_dir / 'message_tags.json')
            if self.config_file.exists():
                shutil.copy2(self.config_file, backup_dir / 'tag_config.json')
            
            return True
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    def restore_data(self, backup_path: str) -> bool:
        """Restore tag data from backup"""
        try:
            backup_dir = Path(backup_path)
            
            # Restore all data files
            import shutil
            backup_tags = backup_dir / 'tags.json'
            backup_message_tags = backup_dir / 'message_tags.json'
            backup_config = backup_dir / 'tag_config.json'
            
            if backup_tags.exists():
                shutil.copy2(backup_tags, self.tags_file)
            if backup_message_tags.exists():
                shutil.copy2(backup_message_tags, self.message_tags_file)
            if backup_config.exists():
                shutil.copy2(backup_config, self.config_file)
            
            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
