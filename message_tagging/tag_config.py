"""
Tag configuration and default settings
"""

from typing import Dict


class TagConfig:
    """Manages tag configuration and default settings"""
    
    def __init__(self):
        self.default_tags = self._initialize_default_tags()
        self.default_shortcuts = self._initialize_default_shortcuts()
    
    def _initialize_default_tags(self) -> Dict[str, Dict]:
        """Initialize the default tag set"""
        return {
            '0': {
                'name': 'Bookmark',
                'color': '#44ff44',
                'shortcut': 'ctrl+1',
                'description': 'Important messages to bookmark'
            },
            '1': {
                'name': 'Evidence',
                'color': '#ff4444',
                'shortcut': 'ctrl+2',
                'description': 'Evidence or proof related content'
            },
            '2': {
                'name': 'Of interest',
                'color': '#ffcc44',
                'shortcut': 'ctrl+3',
                'description': 'Messages of particular interest'
            },
            '3': {
                'name': 'Exceptions',
                'color': '#ff8844',
                'shortcut': 'ctrl+4',
                'description': 'Exceptional or unusual content'
            },
            '4': {
                'name': 'Possible child abuse content',
                'color': '#4488ff',
                'shortcut': 'ctrl+5',
                'description': 'Content that may indicate child abuse'
            },
            '5': {
                'name': 'Possible nudity',
                'color': '#8844ff',
                'shortcut': 'ctrl+6',
                'description': 'Content that may contain nudity'
            },
            '6': {
                'name': 'Blank 1',
                'color': '#212379',
                'shortcut': 'ctrl+7',
                'description': 'Customizable tag 1'
            },
            '7': {
                'name': 'Blank 2',
                'color': '#ff44ff',
                'shortcut': 'ctrl+8',
                'description': 'Customizable tag 2'
            },
            '8': {
                'name': 'Blank 3',
                'color': '#888888',
                'shortcut': 'ctrl+9',
                'description': 'Customizable tag 3'
            },
            '9': {
                'name': 'Blank 4',
                'color': '#af5e5e',
                'shortcut': None,
                'description': 'Customizable tag 4'
            },
            '10': {
                'name': 'Blank 5',
                'color': '#4e2d0e',
                'shortcut': None,
                'description': 'Customizable tag 5'
            },
            '11': {
                'name': 'Blank 6',
                'color': '#66ffff',
                'shortcut': None,
                'description': 'Customizable tag 6'
            }
        }
    
    def _initialize_default_shortcuts(self) -> Dict[str, str]:
        """Initialize default keyboard shortcuts"""
        return {
            'ctrl+1': '0',  # Bookmark
            'ctrl+2': '1',  # Evidence
            'ctrl+3': '2',  # Of interest
            'ctrl+4': '3',  # Exceptions
            'ctrl+5': '4',  # Possible child abuse content
            'ctrl+6': '5',  # Possible nudity
            'ctrl+7': '6',  # Blank 1
            'ctrl+8': '7',  # Blank 2
            'ctrl+9': '8',  # Blank 3
            'space': None   # User configurable
        }
    
    def get_default_tags(self) -> Dict[str, Dict]:
        """Get the default tag configuration"""
        return self.default_tags.copy()
    
    def get_default_shortcuts(self) -> Dict[str, str]:
        """Get the default shortcut configuration"""
        return self.default_shortcuts.copy()
    
    def get_available_shortcuts(self) -> list:
        """Get list of available shortcut keys"""
        return [
            'ctrl+1', 'ctrl+2', 'ctrl+3', 'ctrl+4', 'ctrl+5',
            'ctrl+6', 'ctrl+7', 'ctrl+8', 'ctrl+9', 'space'
        ]
    
    def validate_tag_data(self, tag_data: Dict) -> bool:
        """Validate tag data structure"""
        required_fields = ['name', 'color']
        
        for tag_id, tag_info in tag_data.items():
            if not isinstance(tag_info, dict):
                return False
            
            for field in required_fields:
                if field not in tag_info:
                    return False
            
            # Validate color format (hex color)
            color = tag_info['color']
            if not (isinstance(color, str) and color.startswith('#') and len(color) == 7):
                return False
        
        return True
    
    def validate_shortcut(self, shortcut: str) -> bool:
        """Validate if a shortcut key is valid"""
        return shortcut in self.get_available_shortcuts()
    
    def get_tag_color_palette(self) -> list:
        """Get suggested color palette for tags"""
        return [
            '#44ff44',  # Green
            '#ff4444',  # Red
            '#ffcc44',  # Yellow
            '#ff8844',  # Orange
            '#4488ff',  # Blue
            '#8844ff',  # Purple
            '#ff44ff',  # Magenta
            '#44ffff',  # Cyan
            '#888888',  # Gray
            '#212379',  # Dark blue
            '#af5e5e',  # Brown-red
            '#4e2d0e',  # Dark brown
            '#66ffff',  # Light cyan
            '#ff6b6b',  # Light red
            '#4ecdc4',  # Teal
            '#45b7d1',  # Sky blue
            '#96ceb4',  # Mint green
            '#feca57',  # Golden yellow
            '#ff9ff3',  # Pink
            '#54a0ff'   # Bright blue
        ]
