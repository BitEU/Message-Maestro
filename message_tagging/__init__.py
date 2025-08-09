"""
Message Tagging System Module

This module provides comprehensive tagging functionality for messages,
including tag management, keyboard shortcuts, and UI components.
"""

from .tag_manager import TagManager
from .tag_widgets import TagManagerDialog, TagDisplay
from .tag_storage import TagStorage
from .keyboard_shortcuts import TagShortcutManager
from .tag_config import TagConfig

__all__ = [
    'TagManager',
    'TagManagerDialog', 
    'TagDisplay',
    'TagStorage',
    'TagShortcutManager',
    'TagConfig'
]

__version__ = '1.0.0'
