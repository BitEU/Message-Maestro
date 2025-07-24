#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
import os
from tkinter import Canvas, Frame, Scrollbar
import math

class ModernChatViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitter DM Viewer")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Modern color scheme
        self.colors = {
            'bg_primary': '#0f0f0f',
            'bg_secondary': '#1a1a1a',
            'bg_tertiary': '#252525',
            'accent': '#1d9bf0',  # Twitter blue
            'text_primary': '#ffffff',
            'text_secondary': '#8b8b8b',
            'bubble_sent': '#1d9bf0',
            'bubble_received': '#2f3336',
            'border': '#2f3336',
            'hover': '#353535',
            'selected': '#1d9bf0'
        }
        
        self.conversations = {}
        self.current_conversation = None
        self.file_lines = []
        self.current_file = None
        self.selected_conv_item = None  # Track selected conversation item
        self.conv_items = []  # List of conversation items for keyboard navigation
        
        # Configure root window
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Setup UI
        self.setup_fonts()
        self.setup_styles()
        self.create_ui()
        
        # Bind keyboard events
        self.setup_keyboard_navigation()
        
        # Load default file if exists
        if os.path.exists('template.txt'):
            self.load_dm_file('template.txt')
    
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
        
        # Configure styles
        style.configure('Header.TLabel',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_primary'],
                       font=self.fonts['header'])
        
        style.configure('Status.TLabel',
                       background=self.colors['bg_tertiary'],
                       foreground=self.colors['text_secondary'],
                       font=self.fonts['status'])
    
    def setup_keyboard_navigation(self):
        """Setup keyboard navigation for conversation list"""
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
                    conv_id = self.selected_conv_item.conv_id
                    self.select_conversation(conv_id, self.selected_conv_item)
                return 'break'
        
        # Bind to root window so it works globally
        self.root.bind('<Key>', on_key_press)
        self.root.focus_set()  # Make sure root can receive focus
    
    def navigate_conversations(self, direction):
        """Navigate conversations with arrow keys"""
        if not self.conv_items:
            return
        
        current_index = 0
        if self.selected_conv_item:
            try:
                current_index = self.conv_items.index(self.selected_conv_item)
            except ValueError:
                current_index = 0
        
        # Calculate new index
        new_index = current_index + direction
        new_index = max(0, min(len(self.conv_items) - 1, new_index))
        
        # Select new conversation
        new_item = self.conv_items[new_index]
        conv_id = new_item.conv_id
        self.select_conversation(conv_id, new_item)
        
        # Scroll to make sure selected item is visible
        self.scroll_to_conversation(new_item)
    
    def scroll_to_conversation(self, conv_item):
        """Scroll conversation list to make the selected item visible"""
        # Get the position of the conversation item
        canvas_height = self.conv_canvas.winfo_height()
        scroll_region = self.conv_canvas.bbox("all")
        
        if not scroll_region:
            return
        
        # Get item position relative to the scrollable frame
        item_y = conv_item.winfo_y()
        item_height = conv_item.winfo_height()
        
        # Get current view
        view_top = self.conv_canvas.canvasy(0)
        view_bottom = view_top + canvas_height
        
        # Check if item is visible
        if item_y < view_top:
            # Item is above view, scroll up
            fraction = item_y / scroll_region[3]
            self.conv_canvas.yview_moveto(fraction)
        elif item_y + item_height > view_bottom:
            # Item is below view, scroll down
            fraction = (item_y + item_height - canvas_height) / scroll_region[3]
            self.conv_canvas.yview_moveto(fraction)
    
    def create_ui(self):
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar
        self.create_sidebar(main_container)
        
        # Chat area
        self.create_chat_area(main_container)
        
        # Status bar
        self.create_status_bar()
    
    def create_sidebar(self, parent):
        # Sidebar container
        sidebar = tk.Frame(parent, bg=self.colors['bg_secondary'], width=350)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # Header
        header_frame = tk.Frame(sidebar, bg=self.colors['bg_secondary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Title and button container
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
        
        # Search bar (placeholder)
        search_frame = tk.Frame(sidebar, bg=self.colors['bg_secondary'])
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        search_entry = tk.Entry(search_frame,
                               bg=self.colors['bg_tertiary'],
                               fg=self.colors['text_secondary'],
                               font=('Segoe UI', 10),
                               bd=0,
                               insertbackground=self.colors['text_primary'])
        search_entry.pack(fill=tk.X, ipady=8)
        search_entry.insert(0, "🔍 Search conversations...")
        search_entry.bind('<FocusIn>', lambda e: search_entry.delete(0, tk.END) if search_entry.get() == "🔍 Search conversations..." else None)
        
        # Conversations list container
        list_container = tk.Frame(sidebar, bg=self.colors['bg_secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Create scrollable frame properly
        self.create_scrollable_frame(list_container)
    
    def create_scrollable_frame(self, parent):
        # Canvas for scrolling
        self.conv_canvas = Canvas(parent, bg=self.colors['bg_secondary'], highlightthickness=0, bd=0)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.conv_canvas.yview)
        
        # Frame inside canvas
        self.conv_frame = tk.Frame(self.conv_canvas, bg=self.colors['bg_secondary'])
        
        # Create window in canvas
        self.canvas_window = self.conv_canvas.create_window((0, 0), window=self.conv_frame, anchor="nw")
        
        # Configure canvas
        self.conv_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Update scroll region when frame changes
        def configure_scroll_region(event=None):
            self.conv_canvas.configure(scrollregion=self.conv_canvas.bbox("all"))
            # Update window width to match canvas
            canvas_width = self.conv_canvas.winfo_width()
            self.conv_canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.conv_frame.bind("<Configure>", configure_scroll_region)
        self.conv_canvas.bind("<Configure>", lambda e: self.conv_canvas.itemconfig(self.canvas_window, width=e.width))
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            if self.conv_canvas.winfo_exists():
                self.conv_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to canvas and all children
        self.conv_canvas.bind("<MouseWheel>", on_mousewheel)
        self.conv_canvas.bind("<Button-4>", lambda e: self.conv_canvas.yview_scroll(-1, "units"))
        self.conv_canvas.bind("<Button-5>", lambda e: self.conv_canvas.yview_scroll(1, "units"))
        
        # Pack widgets
        self.conv_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_chat_area(self, parent):
        # Chat container
        chat_container = tk.Frame(parent, bg=self.colors['bg_primary'])
        chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Chat header
        self.chat_header = tk.Frame(chat_container, bg=self.colors['bg_tertiary'], height=60)
        self.chat_header.pack(fill=tk.X)
        self.chat_header.pack_propagate(False)
        
        self.header_label = tk.Label(self.chat_header,
                                    text="Select a conversation",
                                    bg=self.colors['bg_tertiary'],
                                    fg=self.colors['text_primary'],
                                    font=self.fonts['header'])
        self.header_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Messages container
        self.msg_container = tk.Frame(chat_container, bg=self.colors['bg_primary'])
        self.msg_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create scrollable message area
        self.msg_canvas = Canvas(self.msg_container, bg=self.colors['bg_primary'], highlightthickness=0)
        msg_scrollbar = ttk.Scrollbar(self.msg_container, orient="vertical", command=self.msg_canvas.yview)
        self.msg_frame = tk.Frame(self.msg_canvas, bg=self.colors['bg_primary'])
        
        self.msg_window = self.msg_canvas.create_window((0, 0), window=self.msg_frame, anchor="nw")
        
        def configure_msg_scroll(event=None):
            self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))
            # Update window width
            canvas_width = self.msg_canvas.winfo_width()
            self.msg_canvas.itemconfig(self.msg_window, width=canvas_width)
        
        self.msg_frame.bind("<Configure>", configure_msg_scroll)
        self.msg_canvas.bind("<Configure>", lambda e: self.msg_canvas.itemconfig(self.msg_window, width=e.width))
        
        self.msg_canvas.configure(yscrollcommand=msg_scrollbar.set)
        
        # Mouse wheel for messages
        def on_msg_mousewheel(event):
            if self.msg_canvas.winfo_exists():
                self.msg_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.msg_canvas.bind("<MouseWheel>", on_msg_mousewheel)
        
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        msg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initial empty state
        self.show_empty_state()
    
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
                              text="Select a conversation to start reading",
                              bg=self.colors['bg_primary'],
                              fg=self.colors['text_secondary'],
                              font=('Segoe UI', 12))
        empty_label.pack(expand=True, pady=100)
    
    def create_conversation_item(self, conv_id, participants, line_num):
        # Conversation item container
        conv_item = tk.Frame(self.conv_frame, bg=self.colors['bg_secondary'], cursor='hand2')
        conv_item.pack(fill=tk.X, padx=5, pady=2)
        
        # Store reference to conversation ID
        conv_item.conv_id = conv_id
        
        # Inner frame for padding and hover effect
        inner_frame = tk.Frame(conv_item, bg=self.colors['bg_secondary'])
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Participants
        participants_text = ' ↔ '.join(participants[:2])
        if len(participants_text) > 30:
            participants_text = participants_text[:30] + '...'
        
        participants_label = tk.Label(inner_frame,
                                     text=participants_text,
                                     bg=self.colors['bg_secondary'],
                                     fg=self.colors['text_primary'],
                                     font=self.fonts['conversation'])
        participants_label.pack(anchor='w')
        
        # Conversation ID (smaller, secondary text)
        id_text = conv_id if len(conv_id) < 40 else conv_id[:40] + '...'
        id_label = tk.Label(inner_frame,
                           text=id_text,
                           bg=self.colors['bg_secondary'],
                           fg=self.colors['text_secondary'],
                           font=('Segoe UI', 9))
        id_label.pack(anchor='w', pady=(2, 0))
        
        # Line number
        line_label = tk.Label(inner_frame,
                             text=f"Line {line_num}",
                             bg=self.colors['bg_secondary'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 8))
        line_label.pack(anchor='w')
        
        # Bind hover effects
        def on_enter(e):
            if conv_item != self.selected_conv_item:
                conv_item.configure(bg=self.colors['hover'])
                inner_frame.configure(bg=self.colors['hover'])
                for widget in inner_frame.winfo_children():
                    widget.configure(bg=self.colors['hover'])
        
        def on_leave(e):
            if conv_item != self.selected_conv_item:
                conv_item.configure(bg=self.colors['bg_secondary'])
                inner_frame.configure(bg=self.colors['bg_secondary'])
                for widget in inner_frame.winfo_children():
                    widget.configure(bg=self.colors['bg_secondary'])
        
        def on_click(e):
            self.select_conversation(conv_id, conv_item)
        
        for widget in [conv_item, inner_frame] + list(inner_frame.winfo_children()):
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_click)
        
        # Add to navigation list
        self.conv_items.append(conv_item)
        
        return conv_item
    
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
        
        # Create rounded corner effect with custom padding
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
                                  text="📎 Media attached",
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
    
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Open Twitter DM Export",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.load_dm_file(file_path)
    
    def load_dm_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.file_lines = content.split('\n')
            
            self.current_file = file_path
            self.conversations.clear()
            
            # Clear conversation list
            for widget in self.conv_frame.winfo_children():
                widget.destroy()
            
            # Reset selected conversation and items list
            self.selected_conv_item = None
            self.current_conversation = None
            self.conv_items = []
            
            # Parse conversations
            pgp_start = None
            pgp_end = None
            
            for i, line in enumerate(self.file_lines):
                if '-----BEGIN PGP SIGNED MESSAGE-----' in line:
                    pgp_start = i
                elif '-----BEGIN PGP SIGNATURE-----' in line:
                    pgp_end = i
                    break
            
            if pgp_start is not None and pgp_end is not None:
                dm_content = '\n'.join(self.file_lines[pgp_start:pgp_end])
                self.parse_conversations(dm_content, pgp_start)
                self.populate_conversation_list()
                
                # Update status
                filename = os.path.basename(file_path)
                self.status_label.config(text=f"Loaded: {filename} • {len(self.conversations)} conversations")
            else:
                messagebox.showerror("Error", "No PGP signed content found in file!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
    
    def parse_conversations(self, content: str, start_line: int):
        conv_pattern = r'\*\*\*\* conversationId: ([^\s]+) \*\*\*\*'
        conversations = re.finditer(conv_pattern, content)
        
        for match in conversations:
            conv_id = match.group(1)
            conv_start = match.start()
            
            lines_before = content[:conv_start].count('\n')
            line_num = start_line + lines_before + 1
            
            try:
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
                json_str = self.clean_json_string(json_str)
                
                conv_data = json.loads(json_str)
                
                self.conversations[conv_id] = {
                    'data': conv_data,
                    'line_num': line_num,
                    'participants': self.get_participants(conv_data)
                }
                
            except Exception as e:
                self.conversations[conv_id] = {
                    'data': {'error': str(e)},
                    'line_num': line_num,
                    'participants': ['Error parsing']
                }
    
    def clean_json_string(self, json_str: str) -> str:
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
        return json_str
    
    def get_participants(self, conv_data: Dict) -> List[str]:
        participants = set()
        if 'dmConversation' in conv_data and 'messages' in conv_data['dmConversation']:
            for msg in conv_data['dmConversation']['messages']:
                if 'messageCreate' in msg:
                    participants.add(msg['messageCreate'].get('senderId', ''))
                    participants.add(msg['messageCreate'].get('recipientId', ''))
        return list(participants)
    
    def populate_conversation_list(self):
        for conv_id, conv_info in self.conversations.items():
            self.create_conversation_item(
                conv_id,
                conv_info['participants'],
                conv_info['line_num']
            )
        
        # Update scroll region after adding all items
        self.conv_canvas.configure(scrollregion=self.conv_canvas.bbox("all"))
    
    def select_conversation(self, conv_id, conv_item):
        # Update selected item visual state
        if self.selected_conv_item:
            # Reset previous selection
            self.selected_conv_item.configure(bg=self.colors['bg_secondary'])
            inner = self.selected_conv_item.winfo_children()[0]
            inner.configure(bg=self.colors['bg_secondary'])
            for widget in inner.winfo_children():
                widget.configure(bg=self.colors['bg_secondary'])
        
        # Highlight new selection
        self.selected_conv_item = conv_item
        conv_item.configure(bg=self.colors['selected'])
        inner = conv_item.winfo_children()[0]
        inner.configure(bg=self.colors['selected'])
        for widget in inner.winfo_children():
            widget.configure(bg=self.colors['selected'])
        
        if conv_id in self.conversations:
            self.current_conversation = conv_id
            self.display_conversation()
    
    def display_conversation(self):
        if not self.current_conversation:
            return
        
        # Clear messages
        for widget in self.msg_frame.winfo_children():
            widget.destroy()
        
        conv_info = self.conversations[self.current_conversation]
        conv_data = conv_info['data']
        
        # Update header
        participants = ' ↔ '.join(conv_info['participants'][:2])
        self.header_label.config(text=participants)
        
        if 'error' in conv_data:
            error_label = tk.Label(self.msg_frame,
                                  text=f"Error loading conversation: {conv_data['error']}",
                                  bg=self.colors['bg_primary'],
                                  fg='red',
                                  font=('Segoe UI', 10))
            error_label.pack(pady=20)
            return
        
        # Display messages
        if 'dmConversation' in conv_data and 'messages' in conv_data['dmConversation']:
            messages = conv_data['dmConversation']['messages']
            
            # Determine primary sender
            sender_counts = {}
            for msg in messages:
                if 'messageCreate' in msg:
                    sender = msg['messageCreate'].get('senderId', '')
                    sender_counts[sender] = sender_counts.get(sender, 0) + 1
            
            primary_sender = max(sender_counts.keys(), key=lambda x: sender_counts[x]) if sender_counts else None
            
            # Add date separator at start
            if messages:
                self.add_date_separator()
            
            for msg in messages:
                if 'messageCreate' in msg:
                    msg_create = msg['messageCreate']
                    
                    # Get message details
                    msg_id = msg_create.get('id', '')
                    timestamp = msg_create.get('createdAt', '')
                    sender = msg_create.get('senderId', '')
                    text = msg_create.get('text', '')
                    
                    # Find line number
                    msg_line = self.find_message_line(msg_id)
                    
                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%I:%M %p')
                    except:
                        formatted_time = 'Unknown'
                    
                    # Check for media
                    has_media = bool(msg_create.get('mediaUrls') or msg_create.get('urls'))
                    
                    # Create message bubble
                    is_sent = (sender == primary_sender)
                    self.create_message_bubble(text, formatted_time, msg_line, is_sent, has_media)
        
        # Update scroll region and scroll to bottom
        self.msg_canvas.update_idletasks()
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))
        self.msg_canvas.yview_moveto(1.0)
    
    def add_date_separator(self):
        separator_frame = tk.Frame(self.msg_frame, bg=self.colors['bg_primary'])
        separator_frame.pack(fill=tk.X, pady=20)
        
        # Line
        line_left = tk.Frame(separator_frame, bg=self.colors['border'], height=1)
        line_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Date
        date_label = tk.Label(separator_frame,
                             text="Today",
                             bg=self.colors['bg_primary'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 9))
        date_label.pack(side=tk.LEFT, padx=10)
        
        # Line
        line_right = tk.Frame(separator_frame, bg=self.colors['border'], height=1)
        line_right.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def find_message_line(self, msg_id: str) -> int:
        for i, line in enumerate(self.file_lines):
            if msg_id in line:
                return i + 1
        return 0

def main():
    root = tk.Tk()
    app = ModernChatViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()