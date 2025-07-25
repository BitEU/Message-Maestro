#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, colorchooser
import os
from typing import Dict, List, Optional, Set, Tuple
import platform
import json
import re

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

class TagManager:
    """Manages message tags"""
    def __init__(self):
        self.tags = {}  # {tag_id: {'name': str, 'color': str}}
        self.message_tags = {}  # {(conv_id, msg_id): tag_id}
        self.load_default_tags()
    
    def load_default_tags(self):
        """Load default tag set"""
        default_tags = [
            ('Important', '#ff4444'),
            ('Follow-up', '#ff8844'),
            ('Question', '#ffcc44'),
            ('Answer', '#44ff44'),
            ('Personal', '#44ccff'),
            ('Work', '#4488ff'),
            ('Archive', '#8844ff'),
            ('Funny', '#ff44ff'),
            ('Reference', '#888888'),
            ('Action Item', '#ff6666'),
            ('Decision', '#66ff66'),
            ('Idea', '#66ffff'),
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
    
    def export_tags(self) -> Dict:
        """Export tags to dict for saving"""
        return {
            'tags': self.tags,
            'message_tags': {f"{k[0]}|{k[1]}": v for k, v in self.message_tags.items()}
        }
    
    def import_tags(self, data: Dict):
        """Import tags from dict"""
        self.tags = data.get('tags', {})
        self.message_tags = {}
        for key, value in data.get('message_tags', {}).items():
            conv_id, msg_id = key.split('|', 1)
            self.message_tags[(conv_id, msg_id)] = value

class SearchManager:
    """Manages search functionality"""
    def __init__(self):
        self.search_results = []
        self.current_result_index = -1
    
    def search_conversations(self, conversations: List[Conversation], query: str, 
                           search_type: str = 'all') -> List[Dict]:
        """
        Search conversations
        
        Args:
            conversations: List of conversations to search
            query: Search query
            search_type: 'titles', 'content', or 'all'
        
        Returns:
            List of search results with format:
            {'conversation': Conversation, 'matches': List[Message], 'title_match': bool}
        """
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
    
    def highlight_text(self, text: str, query: str) -> List[Tuple[str, bool]]:
        """
        Split text into segments with highlight information
        
        Returns:
            List of (text_segment, is_highlighted) tuples
        """
        if not query:
            return [(text, False)]
        
        segments = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        last_end = 0
        
        for match in pattern.finditer(text):
            # Add non-matching segment
            if match.start() > last_end:
                segments.append((text[last_end:match.start()], False))
            # Add matching segment
            segments.append((text[match.start():match.end()], True))
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            segments.append((text[last_end:], False))
        
        return segments if segments else [(text, False)]

class ModernMessageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Message-Maestro")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
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
        self.selected_parser = tk.StringVar(value="auto")
        self.search_query = tk.StringVar()
        self.search_scope = tk.StringVar(value="all")
        self.message_widgets = {}  # {(conv_id, msg_id): widget}
        
        # In-conversation search state
        self.conv_search_query = tk.StringVar()
        self.search_results = []
        self.current_search_index = -1
        self.last_highlighted_widget = None
        
        # Setup UI
        self.pdf_font_family = self.register_pdf_fonts()
        self.setup_fonts()
        self.setup_styles()
        self.setup_keyboard_navigation()
        self.create_ui()
        self.setup_context_menu()

    def register_pdf_fonts(self):
        """Registers Segoe UI font for PDF generation, with fallback."""
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
                    font_family = "Helvetica"
        
        return font_family
    
    def setup_fonts(self):
        self.fonts = {
            'header': font.Font(family='Segoe UI', size=14, weight='bold'),
            'conversation': font.Font(family='Segoe UI', size=11),
            'message': font.Font(family='Segoe UI', size=10),
            'timestamp': font.Font(family='Segoe UI', size=8),
            'status': font.Font(family='Segoe UI', size=9),
            'search': font.Font(family='Segoe UI', size=10)
        }
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Header.TLabel',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_primary'],
                       font=self.fonts['header'])
        
        style.configure('Status.TLabel',
                       background=self.colors['bg_tertiary'],
                       foreground=self.colors['text_secondary'],
                       font=self.fonts['status'])
        
        # Style for Radiobuttons
        style.configure('TRadiobutton',
                        background=self.colors['bg_secondary'],
                        foreground=self.colors['text_primary'],
                        font=('Segoe UI', 9),
                        padding=(10, 5),
                        indicatorcolor=self.colors['bg_secondary'],
                        bordercolor=self.colors['border'])
        style.map('TRadiobutton',
                  background=[('active', self.colors['hover'])],
                  indicatorcolor=[('selected', self.colors['accent']),
                                  ('!selected', self.colors['text_secondary'])])
    
    def setup_keyboard_navigation(self):
        def on_key_press(event):
            # Search shortcuts
            if event.state & 0x4:  # Ctrl key
                if event.keysym == 'f':
                    self.focus_search()
                    return 'break'
                elif event.keysym == 'g':
                    if event.state & 0x1:  # Shift+Ctrl+G
                        self.find_previous()
                    else:
                        self.find_next()
                    return 'break'
            
            # Navigation shortcuts
            if not self.search_entry.focus_get() == self.search_entry:
                if not self.conv_items:
                    return
                
                if event.keysym == 'Down':
                    self.navigate_conversations(1)
                    return 'break'
                elif event.keysym == 'Up':
                    self.navigate_conversations(-1)
                    return 'break'
                elif event.keysym == 'Return':
                    if self.selected_conv_item:
                        self.select_conversation_by_item(self.selected_conv_item)
                    return 'break'
        
        self.root.bind('<Key>', on_key_press)
        self.root.focus_set()
    
    def setup_context_menu(self):
        """Setup right-click context menu for messages"""
        self.context_menu = tk.Menu(self.root, tearoff=0, bg=self.colors['bg_secondary'],
                                   fg=self.colors['text_primary'], font=self.fonts['message'])
        
        # Tag submenu
        self.tag_menu = tk.Menu(self.context_menu, tearoff=0, bg=self.colors['bg_secondary'],
                               fg=self.colors['text_primary'], font=self.fonts['message'])
        self.context_menu.add_cascade(label="Tag Message", menu=self.tag_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove Tag", command=self.remove_tag_from_message)
        
        self.update_tag_menu()
    
    def update_tag_menu(self):
        """Update the tag submenu with current tags"""
        self.tag_menu.delete(0, tk.END)
        
        for tag_id, tag_info in self.tag_manager.get_tags().items():
            self.tag_menu.add_command(
                label=f"● {tag_info['name']}",
                foreground=tag_info['color'],
                command=lambda tid=tag_id: self.tag_current_message(tid)
            )
        
        self.tag_menu.add_separator()
        self.tag_menu.add_command(label="Manage Tags...", command=self.open_tag_manager)
    
    def navigate_conversations(self, direction):
        if not self.conv_items:
            return
        
        current_index = 0
        if self.selected_conv_item:
            try:
                current_index = self.conv_items.index(self.selected_conv_item)
            except ValueError:
                current_index = 0
        
        new_index = current_index + direction
        new_index = max(0, min(len(self.conv_items) - 1, new_index))
        
        new_item = self.conv_items[new_index]
        self.select_conversation_by_item(new_item)
        self.scroll_to_conversation(new_item)
    
    def scroll_to_conversation(self, conv_item):
        canvas_height = self.conv_canvas.winfo_height()
        scroll_region = self.conv_canvas.bbox("all")
        
        if not scroll_region:
            return
        
        item_y = conv_item.winfo_y()
        item_height = conv_item.winfo_height()
        
        view_top = self.conv_canvas.canvasy(0)
        view_bottom = view_top + canvas_height
        
        if item_y < view_top:
            fraction = item_y / scroll_region[3]
            self.conv_canvas.yview_moveto(fraction)
        elif item_y + item_height > view_bottom:
            fraction = (item_y + item_height - canvas_height) / scroll_region[3]
            self.conv_canvas.yview_moveto(fraction)
    
    def create_ui(self):
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create components
        self.create_sidebar(main_container)
        self.create_chat_area(main_container)
        self.create_status_bar()
    
    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=self.colors['bg_secondary'], width=350)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # Header
        header_frame = tk.Frame(sidebar, bg=self.colors['bg_secondary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_container = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        title_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        title_label = tk.Label(title_container, text="Conversations",
                              bg=self.colors['bg_secondary'],
                              fg=self.colors['text_primary'],
                              font=self.fonts['header'])
        title_label.pack(side=tk.LEFT)
        
        # Buttons container
        buttons_frame = tk.Frame(title_container, bg=self.colors['bg_secondary'])
        buttons_frame.pack(side=tk.RIGHT)
        
        # Tags button
        tags_btn = tk.Button(buttons_frame, text="🏷️",
                           bg=self.colors['bg_tertiary'],
                           fg=self.colors['text_primary'],
                           font=('Segoe UI', 12),
                           bd=0,
                           padx=8,
                           pady=3,
                           cursor='hand2',
                           command=self.open_tag_manager)
        tags_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Open file button
        open_btn = tk.Button(buttons_frame, text="Open File",
                            bg=self.colors['accent'],
                            fg='white',
                            font=('Segoe UI', 9),
                            bd=0,
                            padx=15,
                            pady=5,
                            cursor='hand2',
                            command=self.open_file)
        open_btn.pack(side=tk.LEFT)
        
        # Search bar
        self.create_search_bar(sidebar)
        
        # Parser selection
        self.create_parser_selection(sidebar)
        
        # Conversations list
        self.create_scrollable_conversation_list(sidebar)
    
    def create_search_bar(self, parent):
        """Create search bar in sidebar"""
        search_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        search_frame.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        # Search input container
        search_container = tk.Frame(search_frame, bg=self.colors['bg_tertiary'])
        search_container.pack(fill=tk.X)
        
        # Search icon
        search_icon = tk.Label(search_container, text="🔍",
                             bg=self.colors['bg_tertiary'],
                             fg=self.colors['text_secondary'])
        search_icon.pack(side=tk.LEFT, padx=(10, 5))
        
        # Search entry
        self.search_entry = tk.Entry(search_container,
                                   textvariable=self.search_query,
                                   bg=self.colors['bg_tertiary'],
                                   fg=self.colors['text_primary'],
                                   font=self.fonts['search'],
                                   bd=0,
                                   insertbackground=self.colors['text_primary'])
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=8)
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        self.search_entry.bind('<Escape>', lambda e: self.clear_search())
        
        # Clear button
        self.clear_btn = tk.Button(search_container, text="✕",
                                 bg=self.colors['bg_tertiary'],
                                 fg=self.colors['text_secondary'],
                                 font=('Segoe UI', 10),
                                 bd=0,
                                 cursor='hand2',
                                 command=self.clear_search)
        self.clear_btn.pack(side=tk.RIGHT, padx=(5, 10))
        
        # Search options
        options_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        options_frame.pack(fill=tk.X, padx=20, pady=(5, 10))
        
        # Search scope radio buttons
        tk.Radiobutton(options_frame, text="All",
                      variable=self.search_scope, value="all",
                      bg=self.colors['bg_secondary'],
                      fg=self.colors['text_secondary'],
                      selectcolor=self.colors['bg_secondary'],
                      activebackground=self.colors['bg_secondary'],
                      font=('Segoe UI', 8),
                      command=self.perform_search).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Radiobutton(options_frame, text="Titles",
                      variable=self.search_scope, value="titles",
                      bg=self.colors['bg_secondary'],
                      fg=self.colors['text_secondary'],
                      selectcolor=self.colors['bg_secondary'],
                      activebackground=self.colors['bg_secondary'],
                      font=('Segoe UI', 8),
                      command=self.perform_search).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Radiobutton(options_frame, text="Content",
                      variable=self.search_scope, value="content",
                      bg=self.colors['bg_secondary'],
                      fg=self.colors['text_secondary'],
                      selectcolor=self.colors['bg_secondary'],
                      activebackground=self.colors['bg_secondary'],
                      font=('Segoe UI', 8),
                      command=self.perform_search).pack(side=tk.LEFT)
        
        # Search results label
        self.search_results_label = tk.Label(options_frame, text="",
                                           bg=self.colors['bg_secondary'],
                                           fg=self.colors['text_secondary'],
                                           font=('Segoe UI', 8))
        self.search_results_label.pack(side=tk.RIGHT)
    
    def create_parser_selection(self, parent):
        parser_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        parser_frame.pack(fill=tk.X, padx=20, pady=(10, 0))
        
        label = tk.Label(parser_frame, text="Select Parser:",
                         bg=self.colors['bg_secondary'],
                         fg=self.colors['text_secondary'],
                         font=('Segoe UI', 9, 'bold'))
        label.pack(anchor='w')
        
        # Auto-detect option
        auto_rb = ttk.Radiobutton(parser_frame, text="Auto-detect",
                                  variable=self.selected_parser,
                                  value="auto",
                                  style='TRadiobutton')
        auto_rb.pack(anchor='w')
        
        # Parsers
        for parser in self.parser_manager.get_available_parsers():
            rb = ttk.Radiobutton(parser_frame, text=parser.platform_name,
                                 variable=self.selected_parser,
                                 value=parser.platform_name,
                                 style='TRadiobutton')
            rb.pack(anchor='w')
    
    def create_scrollable_conversation_list(self, parent):
        list_container = tk.Frame(parent, bg=self.colors['bg_secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0))
        
        # Canvas for scrolling
        self.conv_canvas = tk.Canvas(list_container, bg=self.colors['bg_secondary'], 
                                    highlightthickness=0, bd=0)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", 
                                 command=self.conv_canvas.yview)
        
        # Frame inside canvas
        self.conv_frame = tk.Frame(self.conv_canvas, bg=self.colors['bg_secondary'])
        
        # Create window in canvas
        self.canvas_window = self.conv_canvas.create_window((0, 0), 
                                                           window=self.conv_frame, 
                                                           anchor="nw")
        
        # Configure canvas
        self.conv_canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_scroll_region(event=None):
            self.conv_canvas.configure(scrollregion=self.conv_canvas.bbox("all"))
            canvas_width = self.conv_canvas.winfo_width()
            self.conv_canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.conv_frame.bind("<Configure>", configure_scroll_region)
        self.conv_canvas.bind("<Configure>", 
                             lambda e: self.conv_canvas.itemconfig(self.canvas_window, 
                                                                  width=e.width))
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            if self.conv_canvas.winfo_exists():
                self.conv_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.conv_canvas.bind("<MouseWheel>", on_mousewheel)
        
        # Pack widgets
        self.conv_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_chat_area(self, parent):
        chat_container = tk.Frame(parent, bg=self.colors['bg_primary'])
        chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Chat header
        self.chat_header = tk.Frame(chat_container, bg=self.colors['bg_tertiary'], 
                                   height=60)
        self.chat_header.pack(fill=tk.X)
        self.chat_header.pack_propagate(False)
        
        header_content = tk.Frame(self.chat_header, bg=self.colors['bg_tertiary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        self.header_label = tk.Label(header_content,
                                    text="Select a conversation",
                                    bg=self.colors['bg_tertiary'],
                                    fg=self.colors['text_primary'],
                                    font=self.fonts['header'])
        self.header_label.pack(side=tk.LEFT)
        
        # --- In-conversation search bar (initially hidden) ---
        self.conv_search_frame = tk.Frame(header_content, bg=self.colors['bg_tertiary'])
        # self.conv_search_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(self.conv_search_frame, text="Find:", 
                 bg=self.colors['bg_tertiary'], 
                 fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=(0, 5))
        
        conv_search_entry = tk.Entry(self.conv_search_frame, 
                                     textvariable=self.conv_search_query, 
                                     bg=self.colors['bg_secondary'], 
                                     fg=self.colors['text_primary'], 
                                     bd=0, width=20)
        conv_search_entry.pack(side=tk.LEFT, padx=5)
        conv_search_entry.bind('<Return>', lambda e: self.handle_conv_search_enter())
        conv_search_entry.bind('<Escape>', lambda e: self.close_conv_search())
        
        # Previous/Next buttons
        prev_btn = tk.Button(self.conv_search_frame, text="↑ Prev", 
                             command=self.find_previous, **self.get_button_styles('secondary'))
        prev_btn.pack(side=tk.LEFT, padx=5)
        
        next_btn = tk.Button(self.conv_search_frame, text="Next ↓", 
                             command=self.find_next, **self.get_button_styles('secondary'))
        next_btn.pack(side=tk.LEFT, padx=5)
        
        self.conv_search_stats = tk.Label(self.conv_search_frame, text="", 
                                          bg=self.colors['bg_tertiary'], 
                                          fg=self.colors['text_secondary'])
        self.conv_search_stats.pack(side=tk.LEFT, padx=5)
        
        close_btn = tk.Button(self.conv_search_frame, text="✕", 
                              command=self.close_conv_search, **self.get_button_styles('secondary'))
        close_btn.pack(side=tk.LEFT, padx=5)
        
        # --- Header buttons ---
        self.header_buttons_frame = tk.Frame(header_content, bg=self.colors['bg_tertiary'])
        self.header_buttons_frame.pack(side=tk.RIGHT)
        
        # Search in conversation button
        self.search_conv_btn = tk.Button(self.header_buttons_frame, text="🔍 Search",
                                       **self.get_button_styles('secondary'),
                                       command=self.search_in_current_conversation,
                                       state=tk.DISABLED)
        self.search_conv_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export PDF button
        self.export_pdf_btn = tk.Button(self.header_buttons_frame, text="Export as PDF",
                                     bg=self.colors['accent'],
                                     fg='white',
                                     font=('Segoe UI', 9),
                                     bd=0,
                                     padx=15,
                                     pady=5,
                                     cursor='hand2',
                                     command=self.export_to_pdf,
                                     state=tk.DISABLED)
        self.export_pdf_btn.pack(side=tk.LEFT)
        
        # Messages container
        self.create_scrollable_message_area(chat_container)
        
        # Show empty state initially
        self.show_empty_state()
    
    def create_scrollable_message_area(self, parent):
        self.msg_container = tk.Frame(parent, bg=self.colors['bg_primary'])
        self.msg_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create scrollable message area
        self.msg_canvas = tk.Canvas(self.msg_container, bg=self.colors['bg_primary'], 
                                   highlightthickness=0)
        msg_scrollbar = ttk.Scrollbar(self.msg_container, orient="vertical", 
                                     command=self.msg_canvas.yview)
        self.msg_frame = tk.Frame(self.msg_canvas, bg=self.colors['bg_primary'])
        
        self.msg_window = self.msg_canvas.create_window((0, 0), 
                                                       window=self.msg_frame, 
                                                       anchor="nw")
        
        def configure_msg_scroll(event=None):
            self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))
            canvas_width = self.msg_canvas.winfo_width()
            self.msg_canvas.itemconfig(self.msg_window, width=canvas_width)
        
        self.msg_frame.bind("<Configure>", configure_msg_scroll)
        self.msg_canvas.bind("<Configure>", 
                            lambda e: self.msg_canvas.itemconfig(self.msg_window, 
                                                               width=e.width))
        
        self.msg_canvas.configure(yscrollcommand=msg_scrollbar.set)
        
        # Mouse wheel for messages
        def on_msg_mousewheel(event):
            if self.msg_canvas.winfo_exists():
                # Get current scroll position
                top, bottom = self.msg_canvas.yview()
                scroll_amount = int(-1*(event.delta/120))
                
                # Only scroll if there's content to scroll
                if scroll_amount > 0 and bottom < 1.0:  # Scrolling down
                    self.msg_canvas.yview_scroll(scroll_amount, "units")
                elif scroll_amount < 0 and top > 0.0:  # Scrolling up
                    self.msg_canvas.yview_scroll(scroll_amount, "units")
        
        # Store the mousewheel function for use in other methods
        self.on_msg_mousewheel = on_msg_mousewheel
        
        # Function to recursively bind mousewheel to widget and all children
        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", on_msg_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        # Bind mousewheel to canvas, frame, and container
        bind_mousewheel_recursive(self.msg_canvas)
        bind_mousewheel_recursive(self.msg_frame)
        bind_mousewheel_recursive(self.msg_container)
        
        # Store the recursive binding function for use when creating new widgets
        self.bind_mousewheel_recursive = bind_mousewheel_recursive
        
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        msg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_status_bar(self):
        status_bar = tk.Frame(self.root, bg=self.colors['bg_tertiary'], height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(status_bar,
                                    text="No file loaded",
                                    bg=self.colors['bg_tertiary'],
                                    fg=self.colors['text_secondary'],
                                    font=self.fonts['status'])
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
    
    def show_empty_state(self):
        # Clear existing widgets
        for widget in self.msg_frame.winfo_children():
            widget.destroy()
        
        # Empty state message
        empty_label = tk.Label(self.msg_frame,
                              text="📄 Open a message export file to get started",
                              bg=self.colors['bg_primary'],
                              fg=self.colors['text_secondary'],
                              font=('Segoe UI', 12))
        empty_label.pack(expand=True, pady=100)
        
        # Supported formats info
        parsers = self.parser_manager.get_available_parsers()
        if parsers:
            formats_text = "Supported formats: " + ", ".join([p.platform_name for p in parsers])
            formats_label = tk.Label(self.msg_frame,
                                   text=formats_text,
                                   bg=self.colors['bg_primary'],
                                   fg=self.colors['text_secondary'],
                                   font=('Segoe UI', 10))
            formats_label.pack(pady=(10, 0))
    
    def open_file(self):
        # Get file filters from parser manager
        file_filters = self.parser_manager.get_file_filters()
        
        file_path = filedialog.askopenfilename(
            title="Open Message Export File",
            filetypes=file_filters
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        try:
            # Determine which parser to use
            selected_parser_name = self.selected_parser.get()
            parser = None
            
            if selected_parser_name == "auto":
                parser = self.parser_manager.detect_parser(file_path)
            else:
                parser = self.parser_manager.get_parser_by_name(selected_parser_name)

            if not parser:
                messagebox.showerror("Error", 
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
            self.status_label.config(
                text=f"📄 {filename} • {parser.platform_name} • "
                     f"{len(conversations)} conversations"
            )
            
            # Clear message area and disable export button
            self.show_empty_state()
            self.export_pdf_btn.config(state=tk.DISABLED)
            self.search_conv_btn.config(state=tk.DISABLED)
            
            # Clear search
            self.clear_search()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
    
    def populate_conversation_list(self):
        # Clear existing items
        for widget in self.conv_frame.winfo_children():
            widget.destroy()
        
        self.conv_items = []
        self.selected_conv_item = None
        self.current_conversation = None
        
        # Filter conversations based on search
        conversations_to_display = self.conversations
        search_results_map = {}
        
        if self.search_query.get():
            search_results = self.search_manager.search_conversations(
                self.conversations, 
                self.search_query.get(),
                self.search_scope.get()
            )
            conversations_to_display = [r['conversation'] for r in search_results]
            search_results_map = {r['conversation'].id: r for r in search_results}
            
            # Update search results label
            self.search_results_label.config(
                text=f"{len(conversations_to_display)} results"
            )
        else:
            self.search_results_label.config(text="")
        
        # Create conversation items
        for conversation in conversations_to_display:
            search_info = search_results_map.get(conversation.id)
            conv_item = self.create_conversation_item(conversation, search_info)
            self.conv_items.append(conv_item)
        
        # Update scroll region
        self.conv_canvas.configure(scrollregion=self.conv_canvas.bbox("all"))
        
        # Explicitly set focus to the conversation canvas after populating
        if self.conv_items: # Only set focus if there are items to navigate
            self.conv_canvas.focus_set()
            # Select the first item by default if nothing is selected
            if not self.selected_conv_item:
                self.select_conversation_by_item(self.conv_items[0])
    
    def create_conversation_item(self, conversation: Conversation, search_info: Dict = None):
        # Conversation item container
        conv_item = tk.Frame(self.conv_frame, bg=self.colors['bg_secondary'], 
                            cursor='hand2')
        conv_item.pack(fill=tk.X, padx=5, pady=2)
        
        # Store reference to conversation
        conv_item.conversation = conversation
        
        # Inner frame for padding
        inner_frame = tk.Frame(conv_item, bg=self.colors['bg_secondary'])
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Participants
        participants_text = ' ↔ '.join(conversation.participants[:2])
        if len(participants_text) > 30:
            participants_text = participants_text[:30] + '...'
        
        # Highlight if title matches search
        if search_info and search_info.get('title_match'):
            participants_label = tk.Label(inner_frame,
                                         text=participants_text,
                                         bg=self.colors['search_bg'],
                                         fg=self.colors['search_highlight'],
                                         font=self.fonts['conversation'])
        else:
            participants_label = tk.Label(inner_frame,
                                         text=participants_text,
                                         bg=self.colors['bg_secondary'],
                                         fg=self.colors['text_primary'],
                                         font=self.fonts['conversation'])
        participants_label.pack(anchor='w')
        
        # Conversation info
        info_text = f"{len(conversation.messages)} messages"
        if search_info and search_info.get('matches'):
            info_text += f" • {len(search_info['matches'])} matches"
        if hasattr(conversation, 'metadata') and 'error' in conversation.metadata:
            info_text = "⚠️ Parse error"
        
        # Count tagged messages in this conversation
        tagged_count = sum(1 for msg in conversation.messages 
                          if self.tag_manager.get_message_tag(conversation.id, msg.id))
        if tagged_count > 0:
            info_text += f" • {tagged_count} tagged"
        
        info_label = tk.Label(inner_frame,
                             text=info_text,
                             bg=self.colors['bg_secondary'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 9))
        info_label.pack(anchor='w', pady=(2, 0))
        
        # Line number
        line_label = tk.Label(inner_frame,
                             text=f"Line {conversation.line_number}",
                             bg=self.colors['bg_secondary'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 8))
        line_label.pack(anchor='w')
        
        # Bind events
        def on_enter(e):
            if conv_item != self.selected_conv_item:
                self._update_item_colors(conv_item, self.colors['hover'])
        
        def on_leave(e):
            if conv_item != self.selected_conv_item:
                self._update_item_colors(conv_item, self.colors['bg_secondary'])
        
        def on_click(e):
            self.select_conversation_by_item(conv_item)
        
        for widget in [conv_item, inner_frame] + list(inner_frame.winfo_children()):
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_click)
        
        return conv_item
    
    def _update_item_colors(self, conv_item, bg_color):
        """Update colors for conversation item and all children"""
        conv_item.configure(bg=bg_color)
        inner_frame = conv_item.winfo_children()[0]
        inner_frame.configure(bg=bg_color)
        for widget in inner_frame.winfo_children():
            if not isinstance(widget, tk.Label) or widget.cget('bg') != self.colors['search_bg']:
                widget.configure(bg=bg_color)
    
    def select_conversation_by_item(self, conv_item):
        # Update visual selection
        if self.selected_conv_item:
            self._update_item_colors(self.selected_conv_item, self.colors['bg_secondary'])
        
        self.selected_conv_item = conv_item
        self._update_item_colors(conv_item, self.colors['selected'])
        
        # Update current conversation and display
        self.current_conversation = conv_item.conversation
        self.display_conversation()
        
        # Enable export button
        self.export_pdf_btn.config(state=tk.NORMAL)
        self.search_conv_btn.config(state=tk.NORMAL)
    
    def display_conversation(self):
        if not self.current_conversation:
            return
        
        # Clear messages
        for widget in self.msg_frame.winfo_children():
            widget.destroy()
        self.message_widgets.clear()
        
        conversation = self.current_conversation
        
        # Update header
        participants = ' ↔ '.join(conversation.participants[:2])
        self.header_label.config(text=f"💬 {participants}")
        
        # Check for parsing errors
        if hasattr(conversation, 'metadata') and 'error' in conversation.metadata:
            error_label = tk.Label(self.msg_frame,
                                  text=f"⚠️ Error parsing conversation: {conversation.metadata['error']}",
                                  bg=self.colors['bg_primary'],
                                  fg='red',
                                  font=('Segoe UI', 10))
            error_label.pack(pady=20)
            return
        
        # Display messages
        if conversation.messages:
            primary_sender = self.current_parser.get_primary_sender(conversation)
            
            # Check if we should highlight search results
            highlight_messages = set()
            if self.search_query.get() and hasattr(self, '_current_search_conversation'):
                if self._current_search_conversation == conversation.id:
                    highlight_messages = {msg.id for msg in self._current_search_messages}
            
            for message in conversation.messages:
                is_sent = (message.sender_id == primary_sender)
                has_media = bool(message.media_urls or message.urls)
                
                # Get timestamp with date and time
                formatted_time = self.current_parser.format_timestamp(message.timestamp, format_type='long')
                
                # Check if message has tag
                tag_info = self.tag_manager.get_message_tag(conversation.id, message.id)
                
                # Check if message should be highlighted
                should_highlight = message.id in highlight_messages
                
                widget = self.create_message_bubble(
                    message,
                    formatted_time,
                    is_sent,
                    has_media,
                    tag_info,
                    should_highlight
                )
                
                # Store widget reference
                self.message_widgets[(conversation.id, message.id)] = widget
        else:
            no_msg_label = tk.Label(self.msg_frame,
                                   text="No messages in this conversation",
                                   bg=self.colors['bg_primary'],
                                   fg=self.colors['text_secondary'],
                                   font=('Segoe UI', 10))
            no_msg_label.pack(pady=50)
        
        # Update scroll and scroll to bottom
        self.msg_canvas.update_idletasks()
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))
        self.msg_canvas.yview_moveto(1.0)
    
    def create_message_bubble(self, message: Message, timestamp: str, is_sent: bool, 
                            has_media: bool = False, tag_info: Dict = None, 
                            should_highlight: bool = False):
        # Message container
        msg_container = tk.Frame(self.msg_frame, bg=self.colors['bg_primary'])
        msg_container.pack(fill=tk.X, padx=20, pady=5)
        
        # Store message info for context menu
        msg_container.message = message
        msg_container.conversation_id = self.current_conversation.id
        
        # Bubble frame
        bubble_frame = tk.Frame(msg_container, bg=self.colors['bg_primary'])
        
        if is_sent:
            bubble_frame.pack(anchor='e')
        else:
            bubble_frame.pack(anchor='w')
        
        # Message bubble
        bubble_bg = self.colors['bubble_sent'] if is_sent else self.colors['bubble_received']
        
        # Apply tag color if tagged
        if tag_info:
            bubble_bg = tag_info['color']
        
        bubble = tk.Frame(bubble_frame, bg=bubble_bg)
        bubble.pack(fill=tk.X, ipadx=5, ipady=3)
        
        # Inner bubble with padding
        inner_bubble = tk.Frame(bubble, bg=bubble_bg)
        inner_bubble.pack(padx=2, pady=2)
        
        # Message text with search highlighting
        if should_highlight and self.search_query.get():
            # Create text widget for highlighting
            text_widget = tk.Text(inner_bubble, bg=bubble_bg, fg='white',
                                font=self.fonts['message'], wrap='word',
                                width=40, height=1, bd=0, padx=12, pady=8)
            text_widget.pack(anchor='w')
            
            # Insert text with highlights
            segments = self.search_manager.highlight_text(message.text, self.search_query.get())
            for segment, is_highlight in segments:
                if is_highlight:
                    text_widget.insert(tk.END, segment, 'highlight')
                else:
                    text_widget.insert(tk.END, segment)
            
            # Configure highlight tag
            text_widget.tag_config('highlight', background=self.colors['search_highlight'],
                                 foreground='black')
            
            # Calculate height
            text_widget.update_idletasks()
            lines = int(text_widget.index('end-1c').split('.')[0])
            text_widget.config(height=lines, state='disabled')
        else:
            # Regular label
            msg_label = tk.Label(inner_bubble,
                                text=message.text,
                                bg=bubble_bg,
                                fg='white',
                                font=self.fonts['message'],
                                wraplength=350,
                                justify='left',
                                anchor='w')
            msg_label.pack(padx=12, pady=8, anchor='w')
        
        # Media indicator
        if has_media:
            media_label = tk.Label(inner_bubble,
                                  text="📎 Media/Links attached",
                                  bg=bubble_bg,
                                  fg='#cccccc',
                                  font=('Segoe UI', 8),
                                  anchor='w')
            media_label.pack(padx=12, pady=(0, 8), anchor='w')
        
        # Tag indicator
        if tag_info:
            tag_label = tk.Label(inner_bubble,
                               text=f"🏷️ {tag_info['name']}",
                               bg=bubble_bg,
                               fg='white',
                               font=('Segoe UI', 8, 'bold'),
                               anchor='w')
            tag_label.pack(padx=12, pady=(0, 8), anchor='w')
        
        # Timestamp and line info
        info_frame = tk.Frame(bubble_frame, bg=self.colors['bg_primary'])
        info_frame.pack(anchor='e' if is_sent else 'w', pady=(2, 0))
        
        info_text = f"{timestamp} • Line {message.line_number}"
        info_label = tk.Label(info_frame,
                             text=info_text,
                             bg=self.colors['bg_primary'],
                             fg=self.colors['text_secondary'],
                             font=self.fonts['timestamp'])
        info_label.pack()
        
        # Bind context menu to all bubble widgets
        def show_context_menu(event):
            self.current_context_message = msg_container
            self.context_menu.post(event.x_root, event.y_root)
        
        for widget in [bubble, inner_bubble] + list(inner_bubble.winfo_children()):
            widget.bind('<Button-3>', show_context_menu)
        
        # Bind mousewheel to all message bubble widgets
        self.bind_mousewheel_recursive(msg_container)
        
        return msg_container
    
    def add_date_separator(self):
        separator_frame = tk.Frame(self.msg_frame, bg=self.colors['bg_primary'])
        separator_frame.pack(fill=tk.X, pady=20)
        
        # Line
        line_left = tk.Frame(separator_frame, bg=self.colors['border'], height=1)
        line_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Date
        date_label = tk.Label(separator_frame,
                             text="Messages",
                             bg=self.colors['bg_primary'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 9))
        date_label.pack(side=tk.LEFT, padx=10)
        
        # Line
        line_right = tk.Frame(separator_frame, bg=self.colors['border'], height=1)
        line_right.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind mousewheel to date separator widgets
        self.bind_mousewheel_recursive(separator_frame)
    
    def get_button_styles(self, style_type: str = 'primary') -> Dict:
        if style_type == 'primary':
            return {
                'bg': self.colors['accent'], 'fg': 'white', 'font': ('Segoe UI', 9),
                'bd': 0, 'padx': 15, 'pady': 5, 'cursor': 'hand2'
            }
        elif style_type == 'secondary':
            return {
                'bg': self.colors['bg_tertiary'], 'fg': self.colors['text_primary'], 'font': ('Segoe UI', 9),
                'bd': 0, 'padx': 10, 'pady': 3, 'cursor': 'hand2'
            }
        return {}
    
    # Search functionality
    def focus_search(self):
        """Focus on search entry"""
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)
    
    def perform_search(self):
        """Perform search based on current query and scope"""
        query = self.search_query.get()
        if not query:
            self.populate_conversation_list()
            return
        
        # Update conversation list with search results
        self.populate_conversation_list()
        
        # If we have results and a conversation is selected, highlight matches
        if self.current_conversation and self.search_scope.get() in ('content', 'all'):
            matches = self.search_manager.search_in_conversation(
                self.current_conversation, query
            )
            if matches:
                self._current_search_messages = matches
                self._current_search_conversation = self.current_conversation.id
                self.display_conversation()
    
    def clear_search(self):
        """Clear search and reset view"""
        self.search_query.set("")
        self.search_results_label.config(text="")
        self._current_search_messages = []
        self._current_search_conversation = None
        self.populate_conversation_list()
        if self.current_conversation:
            self.display_conversation()
    
    def search_in_current_conversation(self):
        """Shows the in-conversation search bar."""
        if not self.current_conversation:
            return

        self.header_buttons_frame.pack_forget()
        self.conv_search_frame.pack(side=tk.RIGHT, padx=10)
        entry = self.conv_search_frame.winfo_children()[1]
        entry.focus_set()
        entry.selection_range(0, tk.END)

    def close_conv_search(self):
        """Hides the in-conversation search bar and clears results."""
        self.conv_search_frame.pack_forget()
        self.header_buttons_frame.pack(side=tk.RIGHT)

        self.conv_search_query.set("")
        self.search_query.set("")
        self.search_results = []
        self.current_search_index = -1

        if self.last_highlighted_widget:
            self.last_highlighted_widget.config(relief=tk.FLAT, bd=0)
            self.last_highlighted_widget = None

        self.conv_search_stats.config(text="")

        # Redraw conversation without highlights
        self._current_search_messages = []
        self.display_conversation()

    def handle_conv_search_enter(self):
        """Handles the Enter key in the conversation search box."""
        if self.search_results and self.conv_search_query.get() == self.search_query.get():
            self.find_next()
        else:
            self.perform_conv_search()

    def perform_conv_search(self):
        """Performs a search within the current conversation."""
        query = self.conv_search_query.get()
        if not query or not self.current_conversation:
            self.search_results = []
            self.current_search_index = -1
            self.conv_search_stats.config(text="")
            self._current_search_messages = []
            self.display_conversation()
            return

        matches = self.search_manager.search_in_conversation(
            self.current_conversation, query
        )

        self._current_search_messages = matches
        self._current_search_conversation = self.current_conversation.id
        self.search_query.set(query)
        self.display_conversation()
        self.msg_canvas.update_idletasks()

        self.search_results = []
        for msg in matches:
            widget = self.message_widgets.get((self.current_conversation.id, msg.id))
            if widget:
                self.search_results.append(widget)

        self.current_search_index = -1

        if self.last_highlighted_widget:
            self.last_highlighted_widget.config(relief=tk.FLAT, bd=0)
            self.last_highlighted_widget = None

        if self.search_results:
            self.find_next()
        else:
            self.conv_search_stats.config(text="No results")

    def find_next(self):
        """Find next search result"""
        self.navigate_search_results(1)

    def find_previous(self):
        """Find previous search result"""
        self.navigate_search_results(-1)

    def navigate_search_results(self, direction: int):
        """Navigate through search results in the conversation."""
        # If no search results, and there's a query, perform the search first.
        # This handles cases where the conversation was reloaded and search_results became stale.
        if not self.search_results and self.conv_search_query.get():
            self.perform_conv_search()
            # After perform_conv_search, self.search_results will be populated,
            # and it will call find_next() which will re-enter this function.
            # So, we can return here.
            return

        # If still no search results after attempting to perform search, or no query, just return.
        if not self.search_results:
            return

        # Clear previous highlight if it exists and is still valid
        if self.last_highlighted_widget and self.last_highlighted_widget.winfo_exists():
            self.last_highlighted_widget.config(relief=tk.FLAT, bd=0)
        self.last_highlighted_widget = None

        # Calculate the new index
        self.current_search_index += direction
        if self.current_search_index >= len(self.search_results):
            self.current_search_index = 0
        elif self.current_search_index < 0:
            self.current_search_index = len(self.search_results) - 1

        widget_to_show = self.search_results[self.current_search_index]

        # Crucial check: If the widget no longer exists, it means the conversation
        # was redrawn *after* search_results were populated.
        # In this case, we need to re-perform the search to get fresh widget references.
        if not widget_to_show.winfo_exists():
            self.perform_conv_search()
            # perform_conv_search will call find_next() which will re-enter this function
            # with valid widgets. So, we return from this current call.
            return

        # If we reach here, widget_to_show is a valid widget. Proceed with highlighting and scrolling.
        self.msg_canvas.update_idletasks()
        y = widget_to_show.winfo_y()
        canvas_height = self.msg_canvas.winfo_height()

        if canvas_height > 0:
            scroll_region = self.msg_canvas.bbox("all")
            if scroll_region:
                scroll_height = scroll_region[3]
                if scroll_height > 0:
                    position = (y - canvas_height / 3) / scroll_height
                    position = max(0.0, min(position, 1.0))
                    self.msg_canvas.yview_moveto(position)

        widget_to_show.config(
            relief=tk.SOLID,
            highlightbackground=self.colors['search_highlight'],
            highlightcolor=self.colors['search_highlight'],
            highlightthickness=2
        )
        self.last_highlighted_widget = widget_to_show

        self.conv_search_stats.config(
            text=f"{self.current_search_index + 1} of {len(self.search_results)}"
        )
    
    # Tag functionality
    def open_tag_manager(self):
        """Open tag management dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Tags")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg_secondary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        tk.Label(dialog, text="Manage Tags",
                bg=self.colors['bg_secondary'],
                fg=self.colors['text_primary'],
                font=self.fonts['header']).pack(pady=(20, 10))
        
        # Tags list
        tags_frame = tk.Frame(dialog, bg=self.colors['bg_secondary'])
        tags_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create tag entries
        tag_widgets = {}
        
        for i, (tag_id, tag_info) in enumerate(self.tag_manager.get_tags().items()):
            row_frame = tk.Frame(tags_frame, bg=self.colors['bg_secondary'])
            row_frame.pack(fill=tk.X, pady=5)
            
            # Color preview
            color_btn = tk.Button(row_frame, text="",
                                bg=tag_info['color'],
                                width=3,
                                bd=0,
                                cursor='hand2')
            color_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # Tag name entry
            name_var = tk.StringVar(value=tag_info['name'])
            name_entry = tk.Entry(row_frame, textvariable=name_var,
                                bg=self.colors['bg_tertiary'],
                                fg=self.colors['text_primary'],
                                font=self.fonts['message'],
                                width=20)
            name_entry.pack(side=tk.LEFT, padx=(0, 10))
            
            # Usage count
            usage_count = len(self.tag_manager.get_tagged_messages(tag_id))
            usage_label = tk.Label(row_frame,
                                 text=f"{usage_count} messages",
                                 bg=self.colors['bg_secondary'],
                                 fg=self.colors['text_secondary'],
                                 font=('Segoe UI', 8))
            usage_label.pack(side=tk.LEFT)
            
            tag_widgets[tag_id] = {
                'name_var': name_var,
                'color_btn': color_btn,
                'color': tag_info['color']
            }
            
            # Color picker
            def pick_color(tid=tag_id):
                color = colorchooser.askcolor(
                    initialcolor=tag_widgets[tid]['color'],
                    parent=dialog
                )
                if color[1]:  # color[1] is the hex value
                    tag_widgets[tid]['color'] = color[1]
                    tag_widgets[tid]['color_btn'].config(bg=color[1])
            
            color_btn.config(command=pick_color)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_secondary'])
        btn_frame.pack(pady=20)
        
        def save_tags():
            for tag_id, widgets in tag_widgets.items():
                self.tag_manager.update_tag(
                    tag_id,
                    widgets['name_var'].get(),
                    widgets['color']
                )
            self.update_tag_menu()
            # Refresh current conversation to show updated tags
            if self.current_conversation:
                self.display_conversation()
            dialog.destroy()
        
        tk.Button(btn_frame, text="Save",
                 bg=self.colors['accent'],
                 fg='white',
                 font=self.fonts['message'],
                 bd=0,
                 padx=20,
                 pady=5,
                 command=save_tags).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Cancel",
                 bg=self.colors['bg_tertiary'],
                 fg=self.colors['text_primary'],
                 font=self.fonts['message'],
                 bd=0,
                 padx=20,
                 pady=5,
                 command=dialog.destroy).pack(side=tk.LEFT)
    
    def tag_current_message(self, tag_id: str):
        """Tag the currently selected message"""
        if hasattr(self, 'current_context_message'):
            msg_container = self.current_context_message
            self.tag_manager.tag_message(
                msg_container.conversation_id,
                msg_container.message.id,
                tag_id
            )
            # Refresh display
            self.display_conversation()
            # Update conversation list to show tagged count
            self.populate_conversation_list()
    
    def remove_tag_from_message(self):
        """Remove tag from the currently selected message"""
        if hasattr(self, 'current_context_message'):
            msg_container = self.current_context_message
            self.tag_manager.untag_message(
                msg_container.conversation_id,
                msg_container.message.id
            )
            # Refresh display
            self.display_conversation()
            # Update conversation list to show tagged count
            self.populate_conversation_list()
    
    def export_to_pdf(self):
        if not self.current_conversation:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            title="Export Conversation as PDF",
            initialfile=f"{'_'.join(self.current_conversation.participants)}_export.pdf"
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

            # --- Title Page with Tag Legend ---
            participants = ' & '.join(self.current_conversation.participants)
            title_style = styles['h1']
            title_style.fontName = self.pdf_font_family
            title_style.fontSize = self.fonts['header'].cget('size')
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
                fontSize=self.fonts['message'].cget('size'),
                leading=14,
                wordWrap='CJK',
                textColor=hex_to_color(self.colors['text_primary']),
            )

            # Timestamp style
            timestamp_style = ParagraphStyle(
                name='Timestamp',
                parent=styles['Normal'],
                fontName=self.pdf_font_family,
                fontSize=self.fonts['timestamp'].cget('size'),
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
            messagebox.showinfo("Success", f"Conversation successfully exported to\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export to PDF: {e}")

def main():
    root = tk.Tk()
    app = ModernMessageViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()