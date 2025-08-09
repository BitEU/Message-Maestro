#!/usr/bin/env python3

import sys
import os
from typing import Dict, List, Optional, Set, Tuple
import platform
import json
import re
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QScrollArea, QFileDialog, QMessageBox,
    QLineEdit, QRadioButton, QButtonGroup, QTextEdit, QMenu, QDialog,
    QColorDialog, QSplitter, QSizePolicy, QSpacerItem, QGroupBox
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, 
    QRect, QSize, QPoint, pyqtProperty, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QFont, QFontDatabase, QPalette, QColor, QAction, QKeySequence,
    QPainter, QPen, QBrush, QLinearGradient, QPixmap, QPainterPath, QIcon
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLFramebufferObject

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.colors import Color, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from parsers.parser_manager import ParserManager
from parsers.base_parser import BaseParser, Conversation, Message
from message_stats.stats_dashboard import StatsDashboard


class GPUAcceleratedScrollArea(QScrollArea):
    """GPU-accelerated scroll area using OpenGL"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        
        # Enable OpenGL viewport for GPU acceleration
        self.gl_widget = QOpenGLWidget()
        self.gl_widget.setStyleSheet("background-color: #1a1a1a;")  # Set to dark gray
        self.setViewport(self.gl_widget)
        
        # Enable smooth scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Performance optimizations
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.viewport().setAutoFillBackground(False)


class AnimatedButton(QPushButton):
    """Custom button with hover animations"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._animation = QPropertyAnimation(self, b"color")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._color = QColor("#1d9bf0")
        self.setMouseTracking(True)
    
    def get_color(self):
        return getattr(self, '_color', QColor("#1d9bf0"))
    
    def set_color(self, color):
        self._color = color
        self.update()
    
    color = pyqtProperty(QColor, get_color, set_color)
    
    def enterEvent(self, event):
        self._animation.setStartValue(self._color)
        self._animation.setEndValue(QColor("#1a8cd8"))
        self._animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._animation.setStartValue(self._color)
        self._animation.setEndValue(QColor("#1d9bf0"))
        self._animation.start()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: 500;
            }}
        """)
        super().paintEvent(event)


class MessageBubble(QFrame):
    """Custom message bubble widget with GPU-accelerated rendering"""
    contextMenuRequested = pyqtSignal(QPoint, object, str)
    
    def __init__(self, message: Message, conversation_id: str, is_sent: bool, 
                 timestamp: str, tag_info: Dict = None, parent=None):
        super().__init__(parent)
        self.message = message
        self.conversation_id = conversation_id
        self.is_sent = is_sent
        self.timestamp = timestamp
        self.tag_info = tag_info
        self.is_highlighted = False
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)
        
        # Bubble container
        bubble_container = QWidget()
        bubble_layout = QHBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.is_sent:
            bubble_layout.addStretch()
        
        # Actual bubble
        self.bubble = QFrame()
        self.bubble.setObjectName("messageBubble")
        self.bubble_inner_layout = QVBoxLayout(self.bubble)
        self.bubble_inner_layout.setContentsMargins(12, 8, 12, 8)
        
        # Message text
        self.text_label = QLabel(self.message.text)
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumWidth(350)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bubble_inner_layout.addWidget(self.text_label)
        
        # Tag indicator (initially None, will be set by update_tag_display)
        self.tag_label = None
        self.update_tag_display()
        
        # Media indicator
        if self.message.media_urls or self.message.urls:
            media_label = QLabel("📎 Media/Links attached")
            media_label.setObjectName("mediaLabel")
            self.bubble_inner_layout.addWidget(media_label)
        
        bubble_layout.addWidget(self.bubble)
        
        if not self.is_sent:
            bubble_layout.addStretch()
        
        layout.addWidget(bubble_container)
        
        # Timestamp
        timestamp_container = QWidget()
        timestamp_layout = QHBoxLayout(timestamp_container)
        timestamp_layout.setContentsMargins(0, 2, 0, 0)
        
        if self.is_sent:
            timestamp_layout.addStretch()
        
        timestamp_label = QLabel(f"{self.timestamp} • Line {self.message.line_number}")
        timestamp_label.setObjectName("timestampLabel")
        timestamp_layout.addWidget(timestamp_label)
        
        if not self.is_sent:
            timestamp_layout.addStretch()
        
        layout.addWidget(timestamp_container)
        
        self.update_style()
    
    def update_tag_display(self):
        """Update the tag display based on current tag_info"""
        # Remove existing tag label if it exists
        if self.tag_label:
            self.bubble_inner_layout.removeWidget(self.tag_label)
            self.tag_label.deleteLater()
            self.tag_label = None
        
        # Add new tag label if tag_info exists
        if self.tag_info:
            self.tag_label = QLabel(f"🏷️ {self.tag_info['name']}")
            self.tag_label.setObjectName("tagLabel")
            # Insert after text label but before media label
            self.bubble_inner_layout.insertWidget(1, self.tag_label)
    
    def set_tag_info(self, tag_info: Dict = None):
        """Update the tag information and refresh display"""
        self.tag_info = tag_info
        self.update_tag_display()
        self.update_style()
    
    def update_style(self):
        """Update bubble styling based on state"""
        if self.tag_info:
            bubble_color = self.tag_info['color']
        elif self.is_sent:
            bubble_color = "#1d9bf0"
        else:
            bubble_color = "#2f3336"
        
        highlight_style = ""
        if self.is_highlighted:
            highlight_style = f"border: 2px solid #ffcc00;"
        
        # Apply styles with higher specificity to override global theme
        self.bubble.setStyleSheet(f"""
            QFrame#messageBubble {{
                background-color: {bubble_color} !important;
                border-radius: 8px;
                {highlight_style}
            }}
            QFrame#messageBubble QLabel {{
                color: white;
                font-size: 10pt;
                background-color: transparent;
            }}
            QFrame#messageBubble QLabel#tagLabel {{
                font-size: 8pt;
                font-weight: bold;
                background-color: transparent;
            }}
            QFrame#messageBubble QLabel#mediaLabel {{
                color: #cccccc;
                font-size: 8pt;
                background-color: transparent;
            }}
        """)
        
        self.setStyleSheet("""
            QLabel#timestampLabel {
                color: #8b8b8b;
                font-size: 8pt;
                background-color: transparent;
            }
        """)
    
    def set_highlighted(self, highlighted: bool):
        """Set highlight state for search results"""
        self.is_highlighted = highlighted
        self.update_style()
    
    def contextMenuEvent(self, event):
        self.contextMenuRequested.emit(event.globalPos(), self.message, self.conversation_id)


class TagManager:
    """Manages message tags"""
    def __init__(self):
        self.tags = {}  # {tag_id: {'name': str, 'color': str}}
        self.message_tags = {}  # {(conv_id, msg_id): tag_id}
        self.load_default_tags()
    
    def load_default_tags(self):
        """Load default tag set"""
        default_tags = [
            ('Bookmark', '#44ff44'),
            ('Evidence', '#ff4444'),
            ('Of interest', '#ffcc44'),
            ('Exceptions', '#ff8844'),
            ('Possible child abuse content', '#4488ff'),
            ('Possible nudity', '#8844ff'),
            ('Blank 1', "#212379"),
            ('Blank 2', '#ff44ff'),
            ('Blank 3', '#888888'),
            ('Blank 4', "#af5e5e"),
            ('Blank 5', "#4e2d0e"),
            ('Blank 6', '#66ffff'),
        ]
        
        for i, (name, color) in enumerate(default_tags):
            self.tags[str(i)] = {'name': name, 'color': color}
    
    def get_tags(self):
        """Get all tags"""
        return self.tags.copy()
    
    def update_tag(self, tag_id: str, name: str, color: str):
        """Update a tag"""
        self.tags[tag_id] = {'name': name, 'color': color}
    
    def tag_message(self, conv_id: str, msg_id: str, tag_id: str):
        """Tag a message"""
        if tag_id in self.tags:
            self.message_tags[(conv_id, msg_id)] = tag_id
    
    def untag_message(self, conv_id: str, msg_id: str):
        """Remove tag from a message"""
        key = (conv_id, msg_id)
        if key in self.message_tags:
            del self.message_tags[key]
    
    def get_message_tag(self, conv_id: str, msg_id: str) -> Optional[Dict]:
        """Get tag for a message"""
        tag_id = self.message_tags.get((conv_id, msg_id))
        if tag_id and tag_id in self.tags:
            return {'id': tag_id, **self.tags[tag_id]}
        return None
    
    def get_tagged_messages(self, tag_id: str = None) -> List[Tuple[str, str]]:
        """Get all messages with a specific tag (or all tagged messages if tag_id is None)"""
        if tag_id is None:
            return list(self.message_tags.keys())
        return [(conv_id, msg_id) for (conv_id, msg_id), tid in self.message_tags.items() if tid == tag_id]


class SearchManager:
    """Manages search functionality"""
    def __init__(self):
        self.search_results = []
        self.current_result_index = -1
    
    def search_conversations(self, conversations: List[Conversation], query: str, 
                           search_type: str = 'all') -> List[Dict]:
        """Search conversations"""
        if not query:
            return []
        
        results = []
        query_lower = query.lower()
        
        for conv in conversations:
            result = {'conversation': conv, 'matches': [], 'title_match': False}
            
            # Search conversation titles
            if search_type in ('titles', 'all'):
                participants_text = ' '.join(conv.participants).lower()
                if query_lower in participants_text:
                    result['title_match'] = True
            
            # Search message content
            if search_type in ('content', 'all'):
                for msg in conv.messages:
                    if query_lower in msg.text.lower():
                        result['matches'].append(msg)
            
            # Add to results if any matches found
            if result['title_match'] or result['matches']:
                results.append(result)
        
        return results
    
    def search_in_conversation(self, conversation: Conversation, query: str) -> List[Message]:
        """Search within a specific conversation"""
        if not query:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for msg in conversation.messages:
            if query_lower in msg.text.lower():
                matches.append(msg)
        
        return matches


class ConversationItem(QFrame):
    """Custom conversation list item"""
    clicked = pyqtSignal(object)
    
    def __init__(self, conversation: Conversation, search_info: Dict = None, 
                 tag_manager: TagManager = None, parent=None):
        super().__init__(parent)
        self.conversation = conversation
        self.search_info = search_info
        self.tag_manager = tag_manager
        self.is_selected = False
        
        self.setup_ui()
        self.setMouseTracking(True)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Participants
        participants_text = ' ↔ '.join(self.conversation.participants[:2])
        if len(participants_text) > 30:
            participants_text = participants_text[:30] + '...'
        
        self.participants_label = QLabel(participants_text)
        self.participants_label.setObjectName("participantsLabel")
        layout.addWidget(self.participants_label)
        
        # Info
        info_text = f"{len(self.conversation.messages)} messages"
        if self.search_info and self.search_info.get('matches'):
            info_text += f" • {len(self.search_info['matches'])} matches"
        
        # Count tagged messages
        if self.tag_manager:
            tagged_count = sum(1 for msg in self.conversation.messages 
                             if self.tag_manager.get_message_tag(self.conversation.id, msg.id))
            if tagged_count > 0:
                info_text += f" • {tagged_count} tagged"
        
        self.info_label = QLabel(info_text)
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)
        
        # Line number
        self.line_label = QLabel(f"Line {self.conversation.line_number}")
        self.line_label.setObjectName("lineLabel")
        layout.addWidget(self.line_label)
        
        self.update_style()
    
    def update_style(self):
        """Update item styling based on state"""
        bg_color = "#1d9bf0" if self.is_selected else "transparent"
        hover_color = "#353535" if not self.is_selected else "#1d9bf0"
        
        highlight_style = ""
        if self.search_info and self.search_info.get('title_match'):
            highlight_style = f"background-color: #3d3d00; color: #ffcc00;"
        
        self.setStyleSheet(f"""
            ConversationItem {{
                background-color: {bg_color};
                border-radius: 5px;
                padding: 5px;
                margin: 2px;
            }}
            ConversationItem:hover {{
                background-color: {hover_color};
            }}
            ConversationItem QLabel#participantsLabel {{
                color: white;
                font-size: 11pt;
                font-weight: 500;
                background-color: transparent;
                {highlight_style}
            }}
            ConversationItem QLabel#infoLabel {{
                color: #8b8b8b;
                font-size: 9pt;
                background-color: transparent;
            }}
            ConversationItem QLabel#lineLabel {{
                color: #8b8b8b;
                font-size: 8pt;
                background-color: transparent;
            }}
        """)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.conversation)
        super().mousePressEvent(event)


class TagManagerDialog(QDialog):
    """Tag management dialog"""
    def __init__(self, tag_manager: TagManager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.tag_widgets = {}
        
        self.setWindowTitle("Manage Tags")
        self.setModal(True)
        self.resize(500, 600)
        
        self.setup_ui()
        self.apply_dark_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Manage Tags")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: white;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        layout.addSpacing(20)
        
        # Tags list
        tags_widget = QWidget()
        tags_layout = QVBoxLayout(tags_widget)
        
        for tag_id, tag_info in self.tag_manager.get_tags().items():
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 5, 0, 5)
            
            # Color button
            color_btn = QPushButton()
            color_btn.setFixedSize(30, 30)
            color_btn.setStyleSheet(f"background-color: {tag_info['color']}; border: none; border-radius: 5px;")
            color_btn.clicked.connect(lambda checked, tid=tag_id: self.pick_color(tid))
            row_layout.addWidget(color_btn)
            
            # Name entry
            name_entry = QLineEdit(tag_info['name'])
            name_entry.setStyleSheet("background-color: #252525; color: white; border: 1px solid #2f3336; padding: 5px;")
            row_layout.addWidget(name_entry)
            
            # Usage count
            usage_count = len(self.tag_manager.get_tagged_messages(tag_id))
            usage_label = QLabel(f"{usage_count} messages")
            usage_label.setStyleSheet("color: #8b8b8b;")
            row_layout.addWidget(usage_label)
            
            tags_layout.addWidget(row_widget)
            
            self.tag_widgets[tag_id] = {
                'name_entry': name_entry,
                'color_btn': color_btn,
                'color': tag_info['color']
            }
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(tags_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Buttons
        layout.addSpacing(20)
        
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d9bf0;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1a8cd8;
            }
        """)
        save_btn.clicked.connect(self.save_tags)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #353535;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addWidget(buttons_widget)
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
            }
        """)
    
    def pick_color(self, tag_id: str):
        current_color = QColor(self.tag_widgets[tag_id]['color'])
        color = QColorDialog.getColor(current_color, self, "Select Tag Color")
        
        if color.isValid():
            self.tag_widgets[tag_id]['color'] = color.name()
            self.tag_widgets[tag_id]['color_btn'].setStyleSheet(
                f"background-color: {color.name()}; border: none; border-radius: 5px;"
            )
    
    def save_tags(self):
        for tag_id, widgets in self.tag_widgets.items():
            self.tag_manager.update_tag(
                tag_id,
                widgets['name_entry'].text(),
                widgets['color']
            )
        self.accept()


class ModernMessageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Modern color scheme
        self.colors = {
            'bg_primary': '#0f0f0f',
            'bg_secondary': '#1a1a1a',
            'bg_tertiary': '#252525',
            'accent': '#1d9bf0',
            'text_primary': '#ffffff',
            'text_secondary': '#8b8b8b',
            'bubble_sent': '#1d9bf0',
            'bubble_received': '#2f3336',
            'border': '#2f3336',
            'hover': '#353535',
            'selected': '#1d9bf0',
            'search_highlight': '#ffcc00',
            'search_bg': '#3d3d00'
        }
        
        # Initialize managers
        self.parser_manager = ParserManager()
        self.tag_manager = TagManager()
        self.search_manager = SearchManager()
        self.current_parser: Optional[BaseParser] = None
        
        # Data
        self.conversations: List[Conversation] = []
        self.current_conversation: Optional[Conversation] = None
        self.file_lines: List[str] = []
        self.current_file: Optional[str] = None
        
        # UI state
        self.selected_conv_item = None
        self.conv_items = []
        self.selected_parser = "auto"
        self.message_widgets = {}  # {(conv_id, msg_id): widget}
        
        # Search state
        self.search_results = []
        self.current_search_index = -1
        self.last_highlighted_widget = None
        
        # Setup UI
        self.pdf_font_family = self.register_pdf_fonts()
        self.setup_ui()
        self.setup_shortcuts()
        self.apply_dark_theme()
        
    def register_pdf_fonts(self):
        """Registers fonts for PDF generation"""
        font_family = "Helvetica"
        if platform.system() == "Windows":
            font_dir = r"C:\Windows\Fonts"
            segoe_variants = {
                'normal': os.path.join(font_dir, 'segoeui.ttf'),
                'bold': os.path.join(font_dir, 'segoeuib.ttf'),
                'italic': os.path.join(font_dir, 'segoeuii.ttf'),
                'bold_italic': os.path.join(font_dir, 'segoeuiz.ttf')
            }
            
            has_font = all(os.path.exists(path) for path in segoe_variants.values())
            
            if has_font:
                try:
                    pdfmetrics.registerFont(TTFont('SegoeUI', segoe_variants['normal']))
                    pdfmetrics.registerFont(TTFont('SegoeUI-Bold', segoe_variants['bold']))
                    pdfmetrics.registerFont(TTFont('SegoeUI-Italic', segoe_variants['italic']))
                    pdfmetrics.registerFont(TTFont('SegoeUI-BoldItalic', segoe_variants['bold_italic']))
                    pdfmetrics.registerFontFamily('SegoeUI',
                                                  normal='SegoeUI',
                                                  bold='SegoeUI-Bold',
                                                  italic='SegoeUI-Italic',
                                                  boldItalic='SegoeUI-BoldItalic')
                    font_family = "SegoeUI"
                except Exception as e:
                    print(f"Could not register Segoe UI font: {e}")
        
        return font_family
    
    def setup_ui(self):
        self.setWindowTitle("Message-Maestro")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Create sidebar and chat area
        self.create_sidebar()
        self.create_chat_area()
        
        # Add to splitter
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.chat_area)
        self.splitter.setSizes([350, 850])
        
        # Status bar
        self.create_status_bar()
        
        # Context menu
        self.setup_context_menu()
    
    def create_sidebar(self):
        """Create the sidebar panel"""
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setObjectName("sidebarHeader")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title_label = QLabel("Conversations")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: white;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Tags button
        tags_btn = QPushButton("🏷️")
        tags_btn.setFixedSize(35, 30)
        tags_btn.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                border: none;
                border-radius: 5px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #353535;
            }
        """)
        tags_btn.clicked.connect(self.open_tag_manager)
        header_layout.addWidget(tags_btn)
        
        # Open file button
        open_btn = AnimatedButton("Open File")
        open_btn.clicked.connect(self.open_file)
        header_layout.addWidget(open_btn)
        
        sidebar_layout.addWidget(header_widget)
        
        # Search bar
        self.create_search_bar(sidebar_layout)
        
        # Parser selection
        self.create_parser_selection(sidebar_layout)
        
        # Conversations list
        self.create_conversation_list(sidebar_layout)
    
    def create_search_bar(self, parent_layout):
        """Create search bar"""
        search_widget = QWidget()
        search_widget.setObjectName("searchWidget")
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(20, 10, 20, 5)
        
        # Search input
        search_container = QWidget()
        search_container.setObjectName("searchContainer")
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(10, 0, 10, 0)
        
        search_icon = QLabel("🔍")
        search_container_layout.addWidget(search_icon)
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search conversations...")
        self.search_entry.setObjectName("searchEntry")
        self.search_entry.returnPressed.connect(self.perform_search)
        search_container_layout.addWidget(self.search_entry)
        
        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(20, 20)
        clear_btn.setObjectName("clearButton")
        clear_btn.clicked.connect(self.clear_search)
        search_container_layout.addWidget(clear_btn)
        
        search_layout.addWidget(search_container)
        
        # Search options
        options_widget = QWidget()
        options_layout = QHBoxLayout(options_widget)
        options_layout.setContentsMargins(0, 5, 0, 0)
        
        self.search_button_group = QButtonGroup()
        
        all_radio = QRadioButton("All")
        all_radio.setChecked(True)
        all_radio.toggled.connect(lambda: self.perform_search() if all_radio.isChecked() else None)
        self.search_button_group.addButton(all_radio, 0)
        options_layout.addWidget(all_radio)
        
        titles_radio = QRadioButton("Titles")
        titles_radio.toggled.connect(lambda: self.perform_search() if titles_radio.isChecked() else None)
        self.search_button_group.addButton(titles_radio, 1)
        options_layout.addWidget(titles_radio)
        
        content_radio = QRadioButton("Content")
        content_radio.toggled.connect(lambda: self.perform_search() if content_radio.isChecked() else None)
        self.search_button_group.addButton(content_radio, 2)
        options_layout.addWidget(content_radio)
        
        options_layout.addStretch()
        
        self.search_results_label = QLabel("")
        self.search_results_label.setObjectName("searchResultsLabel")
        options_layout.addWidget(self.search_results_label)
        
        search_layout.addWidget(options_widget)
        parent_layout.addWidget(search_widget)
    
    def create_parser_selection(self, parent_layout):
        """Create parser selection"""
        parser_widget = QWidget()
        parser_layout = QVBoxLayout(parser_widget)
        parser_layout.setContentsMargins(20, 10, 20, 0)
        
        label = QLabel("Select Parser:")
        label.setStyleSheet("color: #8b8b8b; font-weight: bold;")
        parser_layout.addWidget(label)
        
        self.parser_button_group = QButtonGroup()
        
        # Auto-detect option (use ID 999 to avoid conflicts)
        auto_radio = QRadioButton("Auto-detect")
        auto_radio.setChecked(True)
        self.parser_button_group.addButton(auto_radio, 999)  # Use 999 as auto-detect ID
        parser_layout.addWidget(auto_radio)
        print(f"DEBUG: Added Auto-detect button with ID: {self.parser_button_group.id(auto_radio)}")
        
        # Available parsers (start from ID 0)
        parsers = self.parser_manager.get_available_parsers()
        for i, parser in enumerate(parsers):
            radio = QRadioButton(parser.platform_name)
            self.parser_button_group.addButton(radio, i)
            parser_layout.addWidget(radio)
            print(f"DEBUG: Added {parser.platform_name} button with ID: {self.parser_button_group.id(radio)}")
        
        # Verify button assignments
        print(f"DEBUG: Total buttons in group: {len(self.parser_button_group.buttons())}")
        for button in self.parser_button_group.buttons():
            button_id = self.parser_button_group.id(button)
            print(f"DEBUG: Button '{button.text()}' has ID: {button_id}")
        
        parent_layout.addWidget(parser_widget)
    
    def create_conversation_list(self, parent_layout):
        """Create scrollable conversation list"""
        self.conv_scroll_area = GPUAcceleratedScrollArea()
        self.conv_scroll_area.setObjectName("convScrollArea")
        
        self.conv_list_widget = QWidget()
        self.conv_list_widget.setObjectName("conv_list_widget")  # Add this line
        self.conv_list_layout = QVBoxLayout(self.conv_list_widget)
        self.conv_list_layout.setContentsMargins(10, 10, 10, 10)
        self.conv_list_layout.setSpacing(5)
        
        self.conv_scroll_area.setWidget(self.conv_list_widget)
        parent_layout.addWidget(self.conv_scroll_area, 1)
    
    def create_chat_area(self):
        """Create the chat area"""
        self.chat_area = QWidget()
        self.chat_area.setObjectName("chatArea")
        chat_layout = QVBoxLayout(self.chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        
        # Chat header
        self.chat_header = QWidget()
        self.chat_header.setFixedHeight(60)
        self.chat_header.setObjectName("chatHeader")
        header_layout = QHBoxLayout(self.chat_header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        self.header_label = QLabel("Select a conversation")
        self.header_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: white;")
        header_layout.addWidget(self.header_label)
        
        header_layout.addStretch()
        
        # In-conversation search (initially hidden)
        self.conv_search_widget = QWidget()
        self.conv_search_widget.hide()
        conv_search_layout = QHBoxLayout(self.conv_search_widget)
        conv_search_layout.setContentsMargins(0, 0, 0, 0)
        
        conv_search_layout.addWidget(QLabel("Find:"))
        
        self.conv_search_entry = QLineEdit()
        self.conv_search_entry.setFixedWidth(200)
        self.conv_search_entry.returnPressed.connect(self.handle_conv_search_enter)
        conv_search_layout.addWidget(self.conv_search_entry)
        
        prev_btn = QPushButton("↑ Prev")
        prev_btn.clicked.connect(self.find_previous)
        conv_search_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("Next ↓")
        next_btn.clicked.connect(self.find_next)
        conv_search_layout.addWidget(next_btn)
        
        self.conv_search_stats = QLabel("")
        conv_search_layout.addWidget(self.conv_search_stats)
        
        close_btn = QPushButton("✕")
        close_btn.clicked.connect(self.close_conv_search)
        conv_search_layout.addWidget(close_btn)
        
        header_layout.addWidget(self.conv_search_widget)
        
        # Header buttons
        self.header_buttons_widget = QWidget()
        header_buttons_layout = QHBoxLayout(self.header_buttons_widget)
        header_buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_conv_btn = QPushButton("🔍 Search")
        self.search_conv_btn.setEnabled(False)
        self.search_conv_btn.clicked.connect(self.search_in_current_conversation)
        header_buttons_layout.addWidget(self.search_conv_btn)
        
        self.stats_dashboard_btn = AnimatedButton("📊 Statistics")
        self.stats_dashboard_btn.setEnabled(False)
        self.stats_dashboard_btn.clicked.connect(self.show_statistics_dashboard)
        header_buttons_layout.addWidget(self.stats_dashboard_btn)
        
        self.export_pdf_btn = AnimatedButton("Export as PDF")
        self.export_pdf_btn.setEnabled(False)
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)
        header_buttons_layout.addWidget(self.export_pdf_btn)
        
        header_layout.addWidget(self.header_buttons_widget)
        
        chat_layout.addWidget(self.chat_header)
        
        # Messages area
        self.msg_scroll_area = GPUAcceleratedScrollArea()
        self.msg_scroll_area.setObjectName("msgScrollArea")
        
        self.msg_list_widget = QWidget()
        self.msg_list_widget.setObjectName("msg_list_widget")  # Add this line
        self.msg_list_layout = QVBoxLayout(self.msg_list_widget)
        self.msg_list_layout.setContentsMargins(20, 10, 20, 10)
        self.msg_list_layout.setSpacing(5)
        
        self.msg_scroll_area.setWidget(self.msg_list_widget)
        chat_layout.addWidget(self.msg_scroll_area)
        
        # Show empty state
        self.show_empty_state()
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                color: #8b8b8b;
                font-size: 9pt;
            }
        """)
        self.status_bar.showMessage("No file loaded")
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Search shortcut
        search_action = QAction("Search", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self.focus_search)
        self.addAction(search_action)
        
        # Find next/previous
        find_next_action = QAction("Find Next", self)
        find_next_action.setShortcut(QKeySequence("Ctrl+G"))
        find_next_action.triggered.connect(self.find_next)
        self.addAction(find_next_action)
        
        find_prev_action = QAction("Find Previous", self)
        find_prev_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
        find_prev_action.triggered.connect(self.find_previous)
        self.addAction(find_prev_action)
    
    def setup_context_menu(self):
        """Setup context menu for messages"""
        self.context_menu = QMenu(self)
        
        # Tag submenu
        self.tag_menu = QMenu("Tag Message", self)
        self.context_menu.addMenu(self.tag_menu)
        
        # Remove tag action (will be dynamically shown/hidden)
        self.context_menu.addSeparator()
        self.remove_tag_action = self.context_menu.addAction("Remove Tag")
        self.remove_tag_action.triggered.connect(self.remove_tag_from_message)
        
        # Current tag info action (will be dynamically updated)
        self.current_tag_action = self.context_menu.addAction("Current: None")
        self.current_tag_action.setEnabled(False)  # Just for display, not clickable
        
        self.update_tag_menu()
    
    def update_tag_menu(self):
        """Update tag submenu"""
        self.tag_menu.clear()
        
        # Add a header to the tag menu
        header_action = self.tag_menu.addAction("Available Tags:")
        header_action.setEnabled(False)
        self.tag_menu.addSeparator()
        
        for tag_id, tag_info in self.tag_manager.get_tags().items():
            action = self.tag_menu.addAction(tag_info['name'])
            action.setData(tag_id)
            action.triggered.connect(lambda checked, tid=tag_id: self.tag_current_message(tid))
            
            # Create a colored icon for the action
            icon = self.create_colored_icon(tag_info['color'])
            action.setIcon(icon)
        
        self.tag_menu.addSeparator()
        manage_tags_action = self.tag_menu.addAction("Manage Tags...")
        manage_tags_action.triggered.connect(self.open_tag_manager)
    
    def create_colored_icon(self, color_hex: str) -> QIcon:
        """Create a colored square icon for menu items"""
        # Create a 16x16 pixmap
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("transparent"))
        
        # Paint a colored square
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(QPen(QColor("#ffffff"), 1))  # White border
        painter.drawRoundedRect(2, 2, 12, 12, 2, 2)  # Rounded square with margin
        painter.end()
        
        return QIcon(pixmap)

    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        dark_style = f"""
            QMainWindow {{
                background-color: {self.colors['bg_primary']};
            }}
            
            QDialog {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_primary']};
            }}
            
            QLabel {{
                background-color: transparent;
                color: {self.colors['text_primary']};
            }}
            
            QLineEdit {{
                background-color: {self.colors['bg_tertiary']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                padding: 5px;
                border-radius: 3px;
            }}
            
            QLineEdit:focus {{
                border-color: {self.colors['accent']};
            }}
            
            QTextEdit {{
                background-color: {self.colors['bg_tertiary']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                padding: 5px;
                border-radius: 3px;
            }}
            
            QGroupBox {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            
            QGroupBox::title {{
                color: {self.colors['text_primary']};
                subcontrol-origin: margin;
                padding: 0 5px;
            }}
            
            /* Sidebar specific */
            #sidebar {{
                background-color: {self.colors['bg_secondary']};
            }}
            
            #sidebarHeader {{
                background-color: {self.colors['bg_secondary']};
                border-bottom: 1px solid {self.colors['border']};
            }}
            
            #searchWidget {{
                background-color: {self.colors['bg_secondary']};
            }}
            
            /* Radio buttons */
            QRadioButton {{
                color: {self.colors['text_secondary']};
                font-size: 8pt;
                spacing: 5px;
                background-color: transparent;
            }}
            
            QRadioButton::indicator {{
                width: 13px;
                height: 13px;
                background-color: transparent;
            }}
            
            QRadioButton::indicator:unchecked {{
                background-color: transparent;
                border: 2px solid {self.colors['text_secondary']};
                border-radius: 7px;
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.colors['accent']};
                border: 2px solid {self.colors['accent']};
                border-radius: 7px;
            }}
            
            /* Scroll areas */
            #convScrollArea {{
                background-color: {self.colors['bg_secondary']};
                border: none;
            }}
            
            #msgScrollArea {{
                background-color: {self.colors['bg_primary']};
                border: none;
            }}
            
            #conv_list_widget {{
                background-color: {self.colors['bg_secondary']};
            }}
            
            #msg_list_widget {{
                background-color: {self.colors['bg_primary']};
            }}
            
            /* Chat area */
            #chatArea {{
                background-color: {self.colors['bg_primary']};
            }}
            
            #chatHeader {{
                background-color: {self.colors['bg_tertiary']};
                border-bottom: 1px solid {self.colors['border']};
            }}
            
            /* Scrollbars */
            QScrollBar:vertical {{
                background-color: {self.colors['bg_secondary']};
                width: 10px;
                border: none;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {self.colors['border']};
                border-radius: 5px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['hover']};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            
            QScrollBar:horizontal {{
                background-color: {self.colors['bg_secondary']};
                height: 10px;
                border: none;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {self.colors['border']};
                border-radius: 5px;
                min-width: 20px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.colors['hover']};
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
            }}
            
            /* Menus */
            QMenu {{
                background-color: {self.colors['bg_tertiary']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                padding: 5px;
            }}
            
            QMenu::item {{
                padding: 5px 20px 5px 30px;
                background-color: transparent;
            }}
            
            QMenu::item:selected {{
                background-color: {self.colors['hover']};
            }}
            
            QMenu::icon {{
                padding-left: 10px;
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {self.colors['bg_tertiary']};
                color: {self.colors['text_primary']};
                border: none;
                padding: 5px 10px;
                border-radius: 5px;
            }}
            
            QPushButton:hover {{
                background-color: {self.colors['hover']};
            }}
            
            QPushButton:disabled {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_secondary']};
            }}
            
            /* Splitter */
            QSplitter {{
                background-color: {self.colors['bg_primary']};
            }}
            
            QSplitter::handle {{
                background-color: {self.colors['border']};
            }}
            
            QSplitter::handle:horizontal {{
                width: 3px;
            }}
            
            QSplitter::handle:vertical {{
                height: 3px;
            }}
            
            /* Status bar */
            QStatusBar {{
                background-color: {self.colors['bg_tertiary']};
                color: {self.colors['text_secondary']};
                font-size: 9pt;
                border-top: 1px solid {self.colors['border']};
            }}
            
            /* Message bubbles specific styling */
            MessageBubble {{
                background-color: transparent;
            }}
            
            /* OpenGL widget backgrounds */
            QOpenGLWidget {{
                background-color: {self.colors['bg_primary']};
            }}
            
            /* Viewport backgrounds */
            QAbstractScrollArea::viewport {{
                background-color: transparent;
            }}
        """

        # Also set application-wide palette to ensure consistency
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(self.colors['bg_primary']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.ColorRole.Base, QColor(self.colors['bg_secondary']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.colors['bg_tertiary']))
        palette.setColor(QPalette.ColorRole.Text, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.ColorRole.Button, QColor(self.colors['bg_tertiary']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self.colors['accent']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(self.colors['text_primary']))
        self.setPalette(palette)
        
        self.setStyleSheet(dark_style)
    
    def show_empty_state(self):
        """Show empty state in message area"""
        # Clear existing widgets
        while self.msg_list_layout.count():
            child = self.msg_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        empty_label = QLabel("📄 Open a message export file to get started")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #8b8b8b; font-size: 12pt; padding: 100px;")
        self.msg_list_layout.addWidget(empty_label)
        
        # Supported formats
        parsers = self.parser_manager.get_available_parsers()
        if parsers:
            formats_text = "Supported formats: " + ", ".join([p.platform_name for p in parsers])
            formats_label = QLabel(formats_text)
            formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            formats_label.setStyleSheet("color: #8b8b8b; font-size: 10pt;")
            self.msg_list_layout.addWidget(formats_label)
        
        self.msg_list_layout.addStretch()
    
    def open_file(self):
        """Open file dialog to select a message export file"""
        file_filters = self.parser_manager.get_file_filters()
        filter_string = ";;".join([f"{desc} ({exts})" for desc, exts in file_filters])
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Message Export File",
            "",
            filter_string
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        """Load and parse the selected file"""
        try:
            # Determine which parser to use
            selected_button = self.parser_button_group.checkedButton()
            print(f"DEBUG: Selected button: {selected_button.text() if selected_button else 'None'}")
            
            if selected_button:
                button_id = self.parser_button_group.id(selected_button)
                print(f"DEBUG: Button ID: {button_id}")
                
                if button_id == 999:  # Auto-detect (changed from -1 to 999)
                    parser = self.parser_manager.detect_parser(file_path)
                    print(f"DEBUG: Auto-detect selected parser: {parser.platform_name if parser else 'None'}")
                else:
                    parsers = self.parser_manager.get_available_parsers()
                    print(f"DEBUG: Available parsers: {[p.platform_name for p in parsers]}")
                    parser = parsers[button_id] if button_id < len(parsers) else None
                    print(f"DEBUG: Manual parser selected (ID {button_id}): {parser.platform_name if parser else 'None'}")
            else:
                parser = self.parser_manager.detect_parser(file_path)
                print(f"DEBUG: No button selected, using auto-detect: {parser.platform_name if parser else 'None'}")
            
            if not parser:
                QMessageBox.critical(self, "Error", 
                                   "No suitable parser found for this file format.\n"
                                   "Please select a different parser or use Auto-detect.")
                return
            
            self.current_parser = parser
            
            # Parse file
            conversations, file_lines = parser.parse_file(file_path)
            
            # Update data
            self.conversations = conversations
            self.file_lines = file_lines
            self.current_file = file_path
            
            # Clear previous data
            self.message_widgets.clear()
            
            # Update UI
            self.populate_conversation_list()
            
            # Update status
            filename = os.path.basename(file_path)
            self.status_bar.showMessage(
                f"📄 {filename} • {parser.platform_name} • "
                f"{len(conversations)} conversations"
            )
            
            # Clear message area and disable buttons
            self.show_empty_state()
            self.export_pdf_btn.setEnabled(False)
            self.search_conv_btn.setEnabled(False)
            self.stats_dashboard_btn.setEnabled(False)
            
            # Clear search
            self.clear_search()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file: {str(e)}")
    
    def populate_conversation_list(self):
        """Populate the conversation list"""
        # Clear existing items
        while self.conv_list_layout.count():
            child = self.conv_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Preserve currently selected conversation (if any)
        selected_conv_id = self.current_conversation.id if self.current_conversation else None
        
        self.conv_items = []
        # Do NOT reset self.current_conversation here; it breaks export/search state
        self.selected_conv_item = None
        
        # Filter conversations based on search
        conversations_to_display = self.conversations
        search_results_map = {}
        
        search_query = self.search_entry.text()
        if search_query:
            search_type_map = {0: 'all', 1: 'titles', 2: 'content'}
            search_type = search_type_map.get(self.search_button_group.checkedId(), 'all')
            
            search_results = self.search_manager.search_conversations(
                self.conversations, 
                search_query,
                search_type
            )
            conversations_to_display = [r['conversation'] for r in search_results]
            search_results_map = {r['conversation'].id: r for r in search_results}
            
            # Update search results label
            self.search_results_label.setText(f"{len(conversations_to_display)} results")
        else:
            self.search_results_label.setText("")
        
        # Create conversation items
        for conversation in conversations_to_display:
            search_info = search_results_map.get(conversation.id)
            conv_item = ConversationItem(conversation, search_info, self.tag_manager)
            conv_item.clicked.connect(self.select_conversation)
            self.conv_list_layout.addWidget(conv_item)
            self.conv_items.append(conv_item)
            
            # Restore selection highlight if this is the previously selected conversation
            if selected_conv_id and conversation.id == selected_conv_id:
                conv_item.set_selected(True)
                self.selected_conv_item = conv_item
        
        self.conv_list_layout.addStretch()
    
    def select_conversation(self, conversation: Conversation):
        """Select a conversation and display its messages"""
        # Update visual selection
        for item in self.conv_items:
            item.set_selected(item.conversation.id == conversation.id)
            if item.conversation.id == conversation.id:
                self.selected_conv_item = item
        
        # Update current conversation and display
        self.current_conversation = conversation
        self.display_conversation()
        
        # Enable buttons
        self.export_pdf_btn.setEnabled(True)
        self.search_conv_btn.setEnabled(True)
        self.stats_dashboard_btn.setEnabled(True)
    
    def display_conversation(self):
        """Display messages for the current conversation"""
        if not self.current_conversation:
            return
        
        # Clear messages
        while self.msg_list_layout.count():
            child = self.msg_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.message_widgets.clear()
        
        conversation = self.current_conversation
        
        # Update header
        participants = ' ↔ '.join(conversation.participants[:2])
        self.header_label.setText(f"💬 {participants}")
        
        # Check for parsing errors
        if hasattr(conversation, 'metadata') and 'error' in conversation.metadata:
            error_label = QLabel(f"⚠️ Error parsing conversation: {conversation.metadata['error']}")
            error_label.setStyleSheet("color: red; font-size: 10pt;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.msg_list_layout.addWidget(error_label)
            self.msg_list_layout.addStretch()
            return
        
        # Display messages
        if conversation.messages:
            primary_sender = self.current_parser.get_primary_sender(conversation)
            
            # Check if we should highlight search results
            highlight_messages = set()
            search_query = self.conv_search_entry.text()
            if search_query:
                matches = self.search_manager.search_in_conversation(conversation, search_query)
                highlight_messages = {msg.id for msg in matches}
            
            for message in conversation.messages:
                is_sent = (message.sender_id == primary_sender)
                
                # Get timestamp with date and time
                formatted_time = self.current_parser.format_timestamp(message.timestamp, format_type='long')
                
                # Check if message has tag
                tag_info = self.tag_manager.get_message_tag(conversation.id, message.id)
                
                # Check if message should be highlighted
                should_highlight = message.id in highlight_messages
                
                # Create message bubble
                bubble = MessageBubble(message, conversation.id, is_sent, formatted_time, tag_info)
                bubble.contextMenuRequested.connect(self.show_message_context_menu)
                
                if should_highlight:
                    bubble.set_highlighted(True)
                
                self.msg_list_layout.addWidget(bubble)
                
                # Store widget reference
                self.message_widgets[(conversation.id, message.id)] = bubble
        else:
            no_msg_label = QLabel("No messages in this conversation")
            no_msg_label.setStyleSheet("color: #8b8b8b; font-size: 10pt;")
            no_msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.msg_list_layout.addWidget(no_msg_label)
        
        self.msg_list_layout.addStretch()
        
        # Scroll to bottom with a small delay to ensure layout is complete
        QTimer.singleShot(50, lambda: self.msg_scroll_area.verticalScrollBar().setValue(
            self.msg_scroll_area.verticalScrollBar().maximum()
        ))
    
    def show_message_context_menu(self, pos: QPoint, message: Message, conversation_id: str):
        """Show context menu for a message"""
        self.current_context_message = (message, conversation_id)
        
        # Check if message has a tag
        current_tag = self.tag_manager.get_message_tag(conversation_id, message.id)
        
        # Update context menu based on current tag state
        if current_tag:
            self.remove_tag_action.setVisible(True)
            self.current_tag_action.setVisible(True)
            self.current_tag_action.setText(f"Current: {current_tag['name']}")
            # Create colored icon for current tag
            icon = self.create_colored_icon(current_tag['color'])
            self.current_tag_action.setIcon(icon)
        else:
            self.remove_tag_action.setVisible(False)
            self.current_tag_action.setVisible(False)
        
        self.context_menu.exec(pos)
    
    def tag_current_message(self, tag_id: str):
        """Tag the currently selected message"""
        if hasattr(self, 'current_context_message'):
            message, conversation_id = self.current_context_message
            
            # Check if message already has a tag
            current_tag = self.tag_manager.get_message_tag(conversation_id, message.id)
            
            # If message already has the same tag, don't do anything
            if current_tag and current_tag['id'] == tag_id:
                return
            
            # Apply the new tag (this will automatically replace any existing tag)
            self.tag_manager.tag_message(conversation_id, message.id, tag_id)
            
            # Update the specific message widget instead of redrawing everything
            widget_key = (conversation_id, message.id)
            if widget_key in self.message_widgets:
                new_tag_info = self.tag_manager.get_message_tag(conversation_id, message.id)
                self.message_widgets[widget_key].set_tag_info(new_tag_info)
            
            # Update conversation list to show tagged count
            self.populate_conversation_list()
    
    def remove_tag_from_message(self):
        """Remove tag from the currently selected message"""
        if hasattr(self, 'current_context_message'):
            message, conversation_id = self.current_context_message
            self.tag_manager.untag_message(conversation_id, message.id)
            
            # Update the specific message widget instead of redrawing everything
            widget_key = (conversation_id, message.id)
            if widget_key in self.message_widgets:
                self.message_widgets[widget_key].set_tag_info(None)
            
            # Update conversation list to show tagged count
            self.populate_conversation_list()
    
    def open_tag_manager(self):
        """Open tag management dialog"""
        dialog = TagManagerDialog(self.tag_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_tag_menu()
            # Refresh current conversation to show updated tags
            if self.current_conversation:
                self.display_conversation()
    
    # Search functionality
    def focus_search(self):
        """Focus on search entry"""
        self.search_entry.setFocus()
        self.search_entry.selectAll()
    
    def perform_search(self):
        """Perform search based on current query and scope"""
        self.populate_conversation_list()
    
    def clear_search(self):
        """Clear search and reset view"""
        self.search_entry.clear()
        self.search_results_label.setText("")
        self.populate_conversation_list()
    
    def search_in_current_conversation(self):
        """Show in-conversation search bar"""
        if not self.current_conversation:
            return
        
        self.header_buttons_widget.hide()
        self.conv_search_widget.show()
        self.conv_search_entry.setFocus()
        self.conv_search_entry.selectAll()
    
    def close_conv_search(self):
        """Hide in-conversation search bar"""
        self.conv_search_widget.hide()
        self.header_buttons_widget.show()
        
        self.conv_search_entry.clear()
        self.search_results = []
        self.current_search_index = -1
        
        if self.last_highlighted_widget:
            self.last_highlighted_widget.set_highlighted(False)
            self.last_highlighted_widget = None
        
        self.conv_search_stats.setText("")
        
        # Redraw conversation without highlights
        self.display_conversation()
    
    def handle_conv_search_enter(self):
        """Handle Enter key in conversation search"""
        if self.search_results and self.conv_search_entry.text():
            self.find_next()
        else:
            self.perform_conv_search()
    
    def perform_conv_search(self):
        """Perform search within current conversation"""
        query = self.conv_search_entry.text()
        if not query or not self.current_conversation:
            self.search_results = []
            self.current_search_index = -1
            self.conv_search_stats.setText("")
            self.display_conversation()
            return
        
        # Find matching messages
        matches = self.search_manager.search_in_conversation(
            self.current_conversation, query
        )
        
        # Highlight messages
        self.display_conversation()
        
        # Collect widgets for matched messages
        self.search_results = []
        for msg in matches:
            widget = self.message_widgets.get((self.current_conversation.id, msg.id))
            if widget:
                self.search_results.append(widget)
        
        self.current_search_index = -1
        
        if self.last_highlighted_widget:
            self.last_highlighted_widget.set_highlighted(False)
            self.last_highlighted_widget = None
        
        if self.search_results:
            self.find_next()
        else:
            self.conv_search_stats.setText("No results")
    
    def find_next(self):
        """Find next search result"""
        self.navigate_search_results(1)
    
    def find_previous(self):
        """Find previous search result"""
        self.navigate_search_results(-1)
    
    def navigate_search_results(self, direction: int):
        """Navigate through search results"""
        if not self.search_results:
            if self.conv_search_entry.text():
                self.perform_conv_search()
            return
        
        # Clear previous highlight
        if self.last_highlighted_widget:
            self.last_highlighted_widget.set_highlighted(False)
        
        # Calculate new index
        self.current_search_index += direction
        if self.current_search_index >= len(self.search_results):
            self.current_search_index = 0
        elif self.current_search_index < 0:
            self.current_search_index = len(self.search_results) - 1
        
        widget = self.search_results[self.current_search_index]
        
        # Scroll to widget
        self.msg_scroll_area.ensureWidgetVisible(widget)
        
        # Highlight widget
        widget.set_highlighted(True)
        self.last_highlighted_widget = widget
        
        self.conv_search_stats.setText(
            f"{self.current_search_index + 1} of {len(self.search_results)}"
        )
    
    def export_to_pdf(self):
        """Export current conversation to PDF"""
        if not self.current_conversation:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Conversation as PDF",
            f"{'_'.join(self.current_conversation.participants)}_message-export.pdf",
            "PDF Documents (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            # Define page layout
            doc = SimpleDocTemplate(file_path, pagesize=letter,
                                    leftMargin=0.5*inch, rightMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            story = []
            
            # Title Page with Tag Legend
            participants = ' & '.join(self.current_conversation.participants)
            title_style = styles['h1']
            title_style.fontName = self.pdf_font_family
            title_style.fontSize = 14
            title = Paragraph(f"Conversation: {participants}", title_style)
            story.append(title)
            story.append(Spacer(1, 0.3 * inch))
            
            # Export info
            info_style = ParagraphStyle(
                name='Info',
                parent=styles['Normal'],
                fontName=self.pdf_font_family,
                fontSize=10,
                textColor=Color(0.5, 0.5, 0.5)
            )
            info_text = f"Exported from {self.current_parser.platform_name}<br/>"
            info_text += f"Total Messages: {len(self.current_conversation.messages)}<br/>"
            if self.current_conversation.messages:
                info_text += f"Date Range: {self.current_conversation.messages[0].timestamp.strftime('%Y-%m-%d')} to "
                info_text += f"{self.current_conversation.messages[-1].timestamp.strftime('%Y-%m-%d')}"
            story.append(Paragraph(info_text, info_style))
            story.append(Spacer(1, 0.3 * inch))
            
            # Tag Legend
            tagged_messages = [(msg, self.tag_manager.get_message_tag(self.current_conversation.id, msg.id))
                              for msg in self.current_conversation.messages
                              if self.tag_manager.get_message_tag(self.current_conversation.id, msg.id)]
            
            if tagged_messages:
                legend_title = Paragraph("<b>Tag Legend</b>", styles['h3'])
                story.append(legend_title)
                story.append(Spacer(1, 0.1 * inch))
                
                # Create legend table
                legend_data = []
                used_tags = {}
                for msg, tag_info in tagged_messages:
                    if tag_info['id'] not in used_tags:
                        used_tags[tag_info['id']] = tag_info
                
                for tag_id, tag_info in used_tags.items():
                    count = sum(1 for m, t in tagged_messages if t['id'] == tag_id)
                    legend_data.append([
                        '',  # Color cell
                        tag_info['name'],
                        f"{count} messages"
                    ])
                
                if legend_data:
                    legend_table = Table(legend_data, colWidths=[0.3*inch, 2*inch, 1.5*inch])
                    
                    # Style for legend
                    legend_style_list = []
                    for i, (tag_id, tag_info) in enumerate(used_tags.items()):
                        hex_color = tag_info['color']
                        pdf_color = Color(
                            int(hex_color[1:3], 16) / 255.0,
                            int(hex_color[3:5], 16) / 255.0,
                            int(hex_color[5:7], 16) / 255.0
                        )
                        legend_style_list.append(('BACKGROUND', (0, i), (0, i), pdf_color))
                    
                    legend_style_list.extend([
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTNAME', (0, 0), (-1, -1), self.pdf_font_family),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('TEXTCOLOR', (1, 0), (-1, -1), Color(0.2, 0.2, 0.2)),
                        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [Color(0.95, 0.95, 0.95), Color(1, 1, 1)]),
                        ('GRID', (0, 0), (-1, -1), 0.5, Color(0.8, 0.8, 0.8)),
                    ])
                    
                    legend_table.setStyle(TableStyle(legend_style_list))
                    story.append(legend_table)
            
            # Page break before messages
            story.append(PageBreak())

            # --- Custom Styles ---
            def hex_to_color(hex_val):
                return Color(
                    int(hex_val[1:3], 16) / 255.0,
                    int(hex_val[3:5], 16) / 255.0,
                    int(hex_val[5:7], 16) / 255.0
                )

            # Base message style (for text properties only)
            message_text_style = ParagraphStyle(
                name='MessageText',
                parent=styles['Normal'],
                fontName=self.pdf_font_family,
                fontSize=10,  # Fixed size for Qt6 (was self.fonts['message'].cget('size'))
                leading=14,
                wordWrap='CJK',
                textColor=hex_to_color(self.colors['text_primary']),
            )

            # Timestamp style
            timestamp_style = ParagraphStyle(
                name='Timestamp',
                parent=styles['Normal'],
                fontName=self.pdf_font_family,
                fontSize=8,  # Fixed size for Qt6 (was self.fonts['timestamp'].cget('size'))
                textColor=hex_to_color(self.colors['text_secondary']),
                spaceBefore=2,
                spaceAfter=10,
            )

            # --- Build Story using a Table ---
            primary_sender = self.current_parser.get_primary_sender(self.current_conversation)
            
            table_data = []
            for message in self.current_conversation.messages:
                is_sent = (message.sender_id == primary_sender)
                
                # Get tag info
                tag_info = self.tag_manager.get_message_tag(self.current_conversation.id, message.id)
                
                # Create the message paragraph
                text = message.text.replace('\n', '<br/>')
                
                # Add tag indicator to text if tagged
                if tag_info:
                    text = f"<b>[{tag_info['name']}]</b><br/>{text}"
                
                p = Paragraph(text, message_text_style)

                # Create the bubble for the paragraph using a nested Table
                if tag_info:
                    bubble_color = hex_to_color(tag_info['color'])
                else:
                    bubble_color = hex_to_color(self.colors['bubble_sent'] if is_sent else self.colors['bubble_received'])
                
                bubble_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), bubble_color),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LINEABOVE', (0,0), (-1,0), 1, bubble_color),
                    ('LINEBELOW', (0,-1), (-1,-1), 1, bubble_color),
                    ('LINEBEFORE', (0,0), (0,-1), 1, bubble_color),
                    ('LINEAFTER', (-1,0), (-1,-1), 1, bubble_color),
                ])
                
                # Try to add rounded corners (may not work in all ReportLab versions)
                try:
                    bubble_style.add('ROUND', (0, 0), (-1, -1), 8)
                except:
                    pass  # Ignore if ROUND is not supported
                
                bubble_table = Table([[p]], style=bubble_style)

                # Timestamp
                formatted_time = self.current_parser.format_timestamp(message.timestamp, format_type='long')
                ts_align_style = timestamp_style.clone(
                    'TimestampAligned',
                    alignment=TA_RIGHT if is_sent else TA_LEFT
                )
                timestamp_p = Paragraph(f"{formatted_time} • Line {message.line_number}", ts_align_style)
                
                # Arrange in columns
                if is_sent:
                    table_data.append(('', [bubble_table, timestamp_p]))
                else:
                    table_data.append(([bubble_table, timestamp_p], ''))

            # Create the main table for all messages
            main_table = Table(table_data, colWidths=['50%', '50%'])
            main_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(main_table)

            # --- Generate PDF ---
            doc.build(story)
            QMessageBox.information(self, "Success", f"Conversation successfully exported to\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export to PDF: {e}")
    
    def show_statistics_dashboard(self):
        """Show the statistics dashboard for the current conversation or all conversations"""
        if not self.conversations:
            QMessageBox.warning(self, "No Data", "Please load message data first.")
            return
        
        try:
            # Determine what to analyze
            if self.current_conversation:
                # Show stats for the current conversation only
                conversations_to_analyze = [self.current_conversation]
                title_suffix = f" - {' ↔ '.join(self.current_conversation.participants)}"
            else:
                # Show stats for all conversations
                conversations_to_analyze = self.conversations
                title_suffix = " - All Conversations"
            
            # Create and show the statistics dashboard
            dashboard = StatsDashboard(conversations_to_analyze, parent=self)
            dashboard.setWindowTitle(f"Message Statistics Dashboard{title_suffix}")
            dashboard.show()
            
            # Make sure it stays on top and is properly focused
            dashboard.raise_()
            dashboard.activateWindow()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open statistics dashboard:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    viewer = ModernMessageViewer()
    viewer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()