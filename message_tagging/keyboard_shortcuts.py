"""
Keyboard shortcuts management for tagging system
"""

from typing import Dict, Optional, Callable, Any
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from .tag_storage import TagStorage


class TagShortcutManager(QObject):
    """Manages keyboard shortcuts for tagging operations"""
    
    # Signals
    tag_requested = pyqtSignal(str)  # Emitted when a tag shortcut is pressed
    spacebar_tag_changed = pyqtSignal(str)  # Emitted when spacebar tag assignment changes
    
    def __init__(self, parent_widget: QWidget, case_file_path: Optional[str] = None):
        super().__init__()
        self.parent_widget = parent_widget
        self.storage = TagStorage(case_file_path)
        
        # Shortcut mappings
        self.shortcuts = {}  # QShortcut objects
        self.shortcut_to_tag = {}  # Maps shortcut keys to tag IDs
        self.tag_to_shortcut = {}  # Maps tag IDs to shortcut keys
        self.spacebar_tag_id = None  # Tag assigned to spacebar
        
        # Load configuration
        self.load_configuration()
        
        # Set up default shortcuts
        self.setup_default_shortcuts()
    
    def setup_default_shortcuts(self):
        """Set up the default Ctrl+1-9 shortcuts"""
        default_mappings = {
            'Ctrl+1': '0',
            'Ctrl+2': '1', 
            'Ctrl+3': '2',
            'Ctrl+4': '3',
            'Ctrl+5': '4',
            'Ctrl+6': '5',
            'Ctrl+7': '6',
            'Ctrl+8': '7',
            'Ctrl+9': '8'
        }
        
        for shortcut_key, tag_id in default_mappings.items():
            self.assign_shortcut(shortcut_key, tag_id)
        
        # Set up spacebar shortcut (initially unassigned)
        self.setup_spacebar_shortcut()
    
    def setup_spacebar_shortcut(self):
        """Set up the spacebar shortcut"""
        if 'Space' in self.shortcuts:
            self.shortcuts['Space'].deleteLater()
        
        spacebar_shortcut = QShortcut(QKeySequence('Space'), self.parent_widget)
        spacebar_shortcut.activated.connect(self.handle_spacebar_press)
        self.shortcuts['Space'] = spacebar_shortcut
    
    def assign_shortcut(self, shortcut_key: str, tag_id: str) -> bool:
        """Assign a keyboard shortcut to a tag"""
        try:
            # Remove existing shortcut if it exists
            if shortcut_key in self.shortcuts:
                self.shortcuts[shortcut_key].deleteLater()
            
            # Remove any existing mapping for this tag
            old_shortcut = self.tag_to_shortcut.get(tag_id)
            if old_shortcut and old_shortcut in self.shortcut_to_tag:
                del self.shortcut_to_tag[old_shortcut]
            
            # Create new shortcut
            shortcut = QShortcut(QKeySequence(shortcut_key), self.parent_widget)
            shortcut.activated.connect(lambda tid=tag_id: self.handle_tag_shortcut(tid))
            
            # Store mappings
            self.shortcuts[shortcut_key] = shortcut
            self.shortcut_to_tag[shortcut_key] = tag_id
            self.tag_to_shortcut[tag_id] = shortcut_key
            
            self.save_configuration()
            return True
            
        except Exception as e:
            print(f"Error assigning shortcut {shortcut_key} to tag {tag_id}: {e}")
            return False
    
    def remove_shortcut(self, shortcut_key: str) -> bool:
        """Remove a keyboard shortcut"""
        try:
            if shortcut_key in self.shortcuts:
                # Remove QShortcut object
                self.shortcuts[shortcut_key].deleteLater()
                del self.shortcuts[shortcut_key]
                
                # Remove mappings
                if shortcut_key in self.shortcut_to_tag:
                    tag_id = self.shortcut_to_tag[shortcut_key]
                    del self.shortcut_to_tag[shortcut_key]
                    if tag_id in self.tag_to_shortcut:
                        del self.tag_to_shortcut[tag_id]
                
                self.save_configuration()
                return True
            return False
            
        except Exception as e:
            print(f"Error removing shortcut {shortcut_key}: {e}")
            return False
    
    def assign_spacebar_tag(self, tag_id: Optional[str]) -> bool:
        """Assign a tag to the spacebar key"""
        try:
            self.spacebar_tag_id = tag_id
            self.save_configuration()
            self.spacebar_tag_changed.emit(tag_id or "")
            return True
        except Exception as e:
            print(f"Error assigning spacebar tag: {e}")
            return False
    
    def get_spacebar_tag(self) -> Optional[str]:
        """Get the tag assigned to spacebar"""
        return self.spacebar_tag_id
    
    def handle_tag_shortcut(self, tag_id: str):
        """Handle a tag shortcut activation"""
        self.tag_requested.emit(tag_id)
    
    def handle_spacebar_press(self):
        """Handle spacebar press"""
        if self.spacebar_tag_id:
            self.tag_requested.emit(self.spacebar_tag_id)
    
    def get_shortcut_for_tag(self, tag_id: str) -> Optional[str]:
        """Get the shortcut key assigned to a tag"""
        return self.tag_to_shortcut.get(tag_id)
    
    def get_tag_for_shortcut(self, shortcut_key: str) -> Optional[str]:
        """Get the tag assigned to a shortcut key"""
        return self.shortcut_to_tag.get(shortcut_key)
    
    def get_all_shortcuts(self) -> Dict[str, str]:
        """Get all shortcut mappings"""
        result = self.shortcut_to_tag.copy()
        if self.spacebar_tag_id:
            result['Space'] = self.spacebar_tag_id
        return result
    
    def get_available_shortcuts(self) -> list:
        """Get list of available shortcut keys"""
        all_shortcuts = [
            'Ctrl+1', 'Ctrl+2', 'Ctrl+3', 'Ctrl+4', 'Ctrl+5',
            'Ctrl+6', 'Ctrl+7', 'Ctrl+8', 'Ctrl+9', 'Space'
        ]
        return [s for s in all_shortcuts if s not in self.shortcut_to_tag]
    
    def is_shortcut_available(self, shortcut_key: str) -> bool:
        """Check if a shortcut key is available"""
        if shortcut_key == 'Space':
            return True  # Spacebar can always be reassigned
        return shortcut_key not in self.shortcut_to_tag
    
    def update_shortcuts_for_tags(self, tags: Dict[str, Dict]):
        """Update shortcuts when tags are modified"""
        # Remove shortcuts for tags that no longer exist
        tags_to_remove = []
        for tag_id in self.tag_to_shortcut.keys():
            if tag_id not in tags:
                tags_to_remove.append(tag_id)
        
        for tag_id in tags_to_remove:
            shortcut_key = self.tag_to_shortcut[tag_id]
            self.remove_shortcut(shortcut_key)
        
        # Check if spacebar tag still exists
        if self.spacebar_tag_id and self.spacebar_tag_id not in tags:
            self.spacebar_tag_id = None
            self.save_configuration()
    
    def save_configuration(self):
        """Save shortcut configuration to storage"""
        config = {
            'shortcuts': self.shortcut_to_tag.copy(),
            'spacebar_tag': self.spacebar_tag_id
        }
        self.storage.save_config(config)
    
    def load_configuration(self):
        """Load shortcut configuration from storage"""
        config = self.storage.load_config()
        if config:
            # Load regular shortcuts
            if 'shortcuts' in config:
                self.shortcut_to_tag = config['shortcuts']
                # Reverse mapping
                self.tag_to_shortcut = {v: k for k, v in self.shortcut_to_tag.items()}
            
            # Load spacebar assignment
            if 'spacebar_tag' in config:
                self.spacebar_tag_id = config['spacebar_tag']
    
    def get_shortcut_display_text(self, shortcut_key: str) -> str:
        """Get user-friendly display text for shortcut"""
        display_map = {
            'Ctrl+1': 'Ctrl+1', 'Ctrl+2': 'Ctrl+2', 'Ctrl+3': 'Ctrl+3',
            'Ctrl+4': 'Ctrl+4', 'Ctrl+5': 'Ctrl+5', 'Ctrl+6': 'Ctrl+6',
            'Ctrl+7': 'Ctrl+7', 'Ctrl+8': 'Ctrl+8', 'Ctrl+9': 'Ctrl+9',
            'Space': 'Spacebar'
        }
        return display_map.get(shortcut_key, shortcut_key)
    
    def export_configuration(self) -> Dict:
        """Export shortcut configuration"""
        return {
            'shortcuts': self.shortcut_to_tag.copy(),
            'spacebar_tag': self.spacebar_tag_id,
            'version': '1.0.0'
        }
    
    def import_configuration(self, config: Dict) -> bool:
        """Import shortcut configuration"""
        try:
            # Clear existing shortcuts
            for shortcut in self.shortcuts.values():
                shortcut.deleteLater()
            self.shortcuts.clear()
            self.shortcut_to_tag.clear()
            self.tag_to_shortcut.clear()
            
            # Import new configuration
            if 'shortcuts' in config:
                for shortcut_key, tag_id in config['shortcuts'].items():
                    self.assign_shortcut(shortcut_key, tag_id)
            
            if 'spacebar_tag' in config:
                self.spacebar_tag_id = config['spacebar_tag']
            
            # Recreate spacebar shortcut
            self.setup_spacebar_shortcut()
            
            self.save_configuration()
            return True
            
        except Exception as e:
            print(f"Error importing shortcut configuration: {e}")
            return False
    
    def reinitialize_for_case(self, case_file_path: str):
        """Reinitialize shortcut manager for a new case file"""
        # Clear existing shortcuts
        for shortcut in self.shortcuts.values():
            shortcut.deleteLater()
        self.shortcuts.clear()
        self.shortcut_to_tag.clear()
        self.tag_to_shortcut.clear()
        self.spacebar_tag_id = None
        
        # Update storage
        self.storage = TagStorage(case_file_path)
        
        # Load configuration for this case
        self.load_configuration()
        
        # Set up shortcuts
        self.setup_default_shortcuts()
