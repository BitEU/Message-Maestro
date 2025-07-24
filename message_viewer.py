#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import os
from typing import Dict, List, Optional
import platform

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.colors import Color, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from parsers.parser_manager import ParserManager
from parsers.base_parser import BaseParser, Conversation, Message

class ModernMessageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Message Viewer")
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
            'selected': '#1d9bf0'
        }
        
        # Initialize parser manager
        self.parser_manager = ParserManager()
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
        
        # Setup UI
        self.pdf_font_family = self.register_pdf_fonts()
        self.setup_fonts()
        self.setup_styles()
        self.setup_keyboard_navigation()
        self.create_ui()

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
                    font_family = "Helvetica" # Fallback on error
        
        return font_family
    
    def setup_fonts(self):
        self.fonts = {
            'header': font.Font(family='Segoe UI', size=14, weight='bold'),
            'conversation': font.Font(family='Segoe UI', size=11),
            'message': font.Font(family='Segoe UI', size=10),
            'timestamp': font.Font(family='Segoe UI', size=8),
            'status': font.Font(family='Segoe UI', size=9)
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
        
        # Open file button
        open_btn = tk.Button(title_container, text="Open File",
                            bg=self.colors['accent'],
                            fg='white',
                            font=('Segoe UI', 9),
                            bd=0,
                            padx=15,
                            pady=5,
                            cursor='hand2',
                            command=self.open_file)
        open_btn.pack(side=tk.RIGHT)
        
        # Parser selection
        self.create_parser_selection(sidebar)
        
        # Conversations list
        self.create_scrollable_conversation_list(sidebar)
    
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
        
        self.header_label = tk.Label(self.chat_header,
                                    text="Select a conversation",
                                    bg=self.colors['bg_tertiary'],
                                    fg=self.colors['text_primary'],
                                    font=self.fonts['header'])
        self.header_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Export PDF button
        self.export_pdf_btn = tk.Button(self.chat_header, text="Export as PDF",
                                     bg=self.colors['accent'],
                                     fg='white',
                                     font=('Segoe UI', 9),
                                     bd=0,
                                     padx=15,
                                     pady=5,
                                     cursor='hand2',
                                     command=self.export_to_pdf,
                                     state=tk.DISABLED)
        self.export_pdf_btn.pack(side=tk.RIGHT, padx=20)
        
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
                self.msg_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.msg_canvas.bind("<MouseWheel>", on_msg_mousewheel)
        
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
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
    
    def populate_conversation_list(self):
        # Clear existing items
        for widget in self.conv_frame.winfo_children():
            widget.destroy()
        
        self.conv_items = []
        self.selected_conv_item = None
        self.current_conversation = None
        
        # Create conversation items
        for conversation in self.conversations:
            conv_item = self.create_conversation_item(conversation)
            self.conv_items.append(conv_item)
        
        # Update scroll region
        self.conv_canvas.configure(scrollregion=self.conv_canvas.bbox("all"))
    
    def create_conversation_item(self, conversation: Conversation):
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
        
        participants_label = tk.Label(inner_frame,
                                     text=participants_text,
                                     bg=self.colors['bg_secondary'],
                                     fg=self.colors['text_primary'],
                                     font=self.fonts['conversation'])
        participants_label.pack(anchor='w')
        
        # Conversation info
        info_text = f"{len(conversation.messages)} messages"
        if hasattr(conversation, 'metadata') and 'error' in conversation.metadata:
            info_text = "⚠️ Parse error"
        
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
    
    def display_conversation(self):
        if not self.current_conversation:
            return
        
        # Clear messages
        for widget in self.msg_frame.winfo_children():
            widget.destroy()
        
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
            
            for message in conversation.messages:
                is_sent = (message.sender_id == primary_sender)
                has_media = bool(message.media_urls or message.urls)
                
                # Get timestamp with date and time
                formatted_time = self.current_parser.format_timestamp(message.timestamp, format_type='long')
                
                self.create_message_bubble(
                    message.text,
                    formatted_time,
                    message.line_number,
                    is_sent,
                    has_media
                )
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
    
    def create_message_bubble(self, text, timestamp, line_num, is_sent, has_media=False):
        # Message container
        msg_container = tk.Frame(self.msg_frame, bg=self.colors['bg_primary'])
        msg_container.pack(fill=tk.X, padx=20, pady=5)
        
        # Bubble frame
        bubble_frame = tk.Frame(msg_container, bg=self.colors['bg_primary'])
        
        if is_sent:
            bubble_frame.pack(anchor='e')
        else:
            bubble_frame.pack(anchor='w')
        
        # Message bubble
        bubble_bg = self.colors['bubble_sent'] if is_sent else self.colors['bubble_received']
        
        bubble = tk.Frame(bubble_frame, bg=bubble_bg)
        bubble.pack(fill=tk.X, ipadx=5, ipady=3)
        
        # Inner bubble with padding
        inner_bubble = tk.Frame(bubble, bg=bubble_bg)
        inner_bubble.pack(padx=2, pady=2)
        
        # Message text
        msg_label = tk.Label(inner_bubble,
                            text=text,
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
        
        # Timestamp and line info
        info_frame = tk.Frame(bubble_frame, bg=self.colors['bg_primary'])
        info_frame.pack(anchor='e' if is_sent else 'w', pady=(2, 0))
        
        info_text = f"{timestamp} • Line {line_num}"
        info_label = tk.Label(info_frame,
                             text=info_text,
                             bg=self.colors['bg_primary'],
                             fg=self.colors['text_secondary'],
                             font=self.fonts['timestamp'])
        info_label.pack()
    
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

            # --- Title ---
            participants = ' & '.join(self.current_conversation.participants)
            title_style = styles['h1']
            title_style.fontName = self.pdf_font_family
            title_style.fontSize = self.fonts['header'].cget('size')
            title = Paragraph(f"Conversation: {participants}", title_style)
            story.append(title)
            story.append(Spacer(1, 0.2 * inch))

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
                
                # Create the message paragraph
                text = message.text.replace('\n', '<br/>')
                p = Paragraph(text, message_text_style)

                # Create the bubble for the paragraph using a nested Table
                bubble_color = hex_to_color(self.colors['bubble_sent'] if is_sent else self.colors['bubble_received'])
                
                bubble_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), bubble_color),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    # --- THIS IS THE PADDING THAT WILL NOW WORK ---
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    # Use 'ROUND' for rounded corners, a custom feature of some ReportLab versions/extensions
                    # If it causes an error, it can be removed.
                    ('ROUND', (0, 0), (-1, -1), 8), 
                    ('LINEABOVE', (0,0), (-1,0), 1, bubble_color),
                    ('LINEBELOW', (0,-1), (-1,-1), 1, bubble_color),
                    ('LINEBEFORE', (0,0), (0,-1), 1, bubble_color),
                    ('LINEAFTER', (-1,0), (-1,-1), 1, bubble_color),
                ])
                
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
                # No padding needed here anymore, it's handled by the bubbles
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
