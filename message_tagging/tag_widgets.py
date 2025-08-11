"""
UI widgets and components for the tagging system
"""

from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QWidget, QColorDialog, QComboBox, QCheckBox, QGroupBox,
    QSizePolicy, QSpacerItem, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QPainter, QBrush, QPen, QIcon

from .tag_manager import TagManager
from .keyboard_shortcuts import TagShortcutManager


class TagDisplay(QLabel):
    """A widget to display a tag with color and text"""
    
    def __init__(self, tag_info: Dict, show_shortcut: bool = True, parent=None):
        super().__init__(parent)
        self.tag_info = tag_info
        self.show_shortcut = show_shortcut
        self.update_display()
    
    def update_display(self):
        """Update the tag display"""
        name = self.tag_info.get('name', 'Unknown')
        shortcut = self.tag_info.get('shortcut', '')
        
        # Build display text
        display_text = f"🏷️ {name}"
        if self.show_shortcut and shortcut:
            shortcut_display = self._format_shortcut(shortcut)
            display_text += f" ({shortcut_display})"
        
        self.setText(display_text)
        self.setObjectName("tagLabel")
        
        # Apply styling
        color = self.tag_info.get('color', '#888888')
        self.setStyleSheet(f"""
            QLabel#tagLabel {{
                background-color: {color};
                color: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        """)
    
    def _format_shortcut(self, shortcut: str) -> str:
        """Format shortcut for display"""
        if shortcut.lower() == 'space':
            return 'Space'
        return shortcut.replace('Ctrl+', '⌃')


class ShortcutAssignmentWidget(QWidget):
    """Widget for assigning shortcuts to tags"""
    
    shortcut_changed = pyqtSignal(str, str)  # tag_id, new_shortcut
    
    def __init__(self, tag_id: str, tag_info: Dict, current_shortcut: str, 
                 available_shortcuts: List[str], parent=None):
        super().__init__(parent)
        self.tag_id = tag_id
        self.tag_info = tag_info
        self.current_shortcut = current_shortcut
        
        self.setup_ui(available_shortcuts)
    
    def setup_ui(self, available_shortcuts: List[str]):
        """Set up the UI for shortcut assignment"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Tag color indicator
        color_indicator = QLabel()
        color_indicator.setFixedSize(20, 20)
        color_indicator.setStyleSheet(f"""
            background-color: {self.tag_info['color']};
            border: 1px solid #555;
            border-radius: 3px;
        """)
        layout.addWidget(color_indicator)
        
        # Tag name
        name_label = QLabel(self.tag_info['name'])
        name_label.setMinimumWidth(150)
        layout.addWidget(name_label)
        
        # Shortcut combo box
        self.shortcut_combo = QComboBox()
        self.shortcut_combo.addItem("None", "")
        
        # Add available shortcuts
        for shortcut in available_shortcuts:
            display_text = self._format_shortcut_display(shortcut)
            self.shortcut_combo.addItem(display_text, shortcut)
        
        # Add current shortcut if it's not in available list
        if self.current_shortcut and self.current_shortcut not in available_shortcuts:
            display_text = self._format_shortcut_display(self.current_shortcut)
            self.shortcut_combo.addItem(f"{display_text} (current)", self.current_shortcut)
        
        # Set current selection
        if self.current_shortcut:
            index = self.shortcut_combo.findData(self.current_shortcut)
            if index >= 0:
                self.shortcut_combo.setCurrentIndex(index)
        
        self.shortcut_combo.currentTextChanged.connect(self.on_shortcut_changed)
        layout.addWidget(self.shortcut_combo)
        
        layout.addStretch()
    
    def _format_shortcut_display(self, shortcut: str) -> str:
        """Format shortcut for display in combo box"""
        if shortcut.lower() == 'space':
            return 'Spacebar'
        return shortcut
    
    def on_shortcut_changed(self):
        """Handle shortcut change"""
        new_shortcut = self.shortcut_combo.currentData()
        if new_shortcut != self.current_shortcut:
            self.current_shortcut = new_shortcut
            self.shortcut_changed.emit(self.tag_id, new_shortcut or "")


class SpacebarAssignmentWidget(QWidget):
    """Widget for assigning spacebar to a tag"""
    
    spacebar_changed = pyqtSignal(str)  # tag_id (empty string for none)
    
    def __init__(self, tags: Dict[str, Dict], current_spacebar_tag: str, parent=None):
        super().__init__(parent)
        self.tags = tags
        self.current_spacebar_tag = current_spacebar_tag
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI for spacebar assignment"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Spacebar Assignment")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; color: white;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Choose which tag to assign to the spacebar for quick tagging:")
        desc.setStyleSheet("color: #8b8b8b; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Combo box for tag selection
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("None (disable spacebar tagging)", "")
        
        # Add all tags
        for tag_id, tag_info in self.tags.items():
            self.tag_combo.addItem(f"🏷️ {tag_info['name']}", tag_id)
        
        # Set current selection
        if self.current_spacebar_tag:
            index = self.tag_combo.findData(self.current_spacebar_tag)
            if index >= 0:
                self.tag_combo.setCurrentIndex(index)
        
        self.tag_combo.currentTextChanged.connect(self.on_selection_changed)
        layout.addWidget(self.tag_combo)
        
        # Add some spacing
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    
    def on_selection_changed(self):
        """Handle selection change"""
        selected_tag_id = self.tag_combo.currentData()
        self.spacebar_changed.emit(selected_tag_id or "")


class TagManagerDialog(QDialog):
    """Enhanced tag management dialog with keyboard shortcuts"""
    
    def __init__(self, tag_manager: TagManager, shortcut_manager: TagShortcutManager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.shortcut_manager = shortcut_manager
        self.tag_widgets = {}
        self.shortcut_widgets = {}
        
        self.setWindowTitle("Manage Tags and Shortcuts")
        self.setModal(True)
        self.resize(700, 800)
        
        self.setup_ui()
        self.apply_dark_theme()
    
    def setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Manage Tags and Keyboard Shortcuts")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: white; margin-bottom: 20px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Combined tags and shortcuts section
        self.setup_combined_tags_section(layout)
        self.setup_spacebar_section(layout)
        
        # Buttons
        self.setup_buttons(layout)
    
    def setup_combined_tags_section(self, parent_layout):
        """Set up the combined tags management and shortcuts section"""
        # Combined tags and shortcuts section
        tags_group = QGroupBox("Tag Management")
        tags_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: white;
                border: 2px solid #2f3336;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        tags_layout = QVBoxLayout(tags_group)
        
        # Description
        desc = QLabel("Edit tag names, colors, and assign keyboard shortcuts (Ctrl+1 through Ctrl+9):")
        desc.setStyleSheet("color: #8b8b8b; margin-bottom: 15px;")
        desc.setWordWrap(True)
        tags_layout.addWidget(desc)
        
        # Tags list with integrated shortcuts
        tags_scroll = QScrollArea()
        tags_widget = QWidget()
        self.tags_layout = QVBoxLayout(tags_widget)
        
        # Available shortcuts for assignment
        available_shortcuts = ['Ctrl+1', 'Ctrl+2', 'Ctrl+3', 'Ctrl+4', 'Ctrl+5',
                             'Ctrl+6', 'Ctrl+7', 'Ctrl+8', 'Ctrl+9']
        
        for tag_id, tag_info in self.tag_manager.get_tags().items():
            tag_row = self.create_combined_tag_row(tag_id, tag_info, available_shortcuts)
            self.tags_layout.addWidget(tag_row)
        
        tags_scroll.setWidget(tags_widget)
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setMaximumHeight(400)
        tags_layout.addWidget(tags_scroll)
        
        parent_layout.addWidget(tags_group)
    
    def setup_spacebar_section(self, parent_layout):
        """Set up the spacebar assignment section"""
        spacebar_group = QGroupBox("Spacebar Quick Tag")
        spacebar_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: white;
                border: 2px solid #2f3336;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        current_spacebar_tag = self.shortcut_manager.get_spacebar_tag()
        self.spacebar_widget = SpacebarAssignmentWidget(
            self.tag_manager.get_tags(), current_spacebar_tag, self
        )
        self.spacebar_widget.spacebar_changed.connect(self.on_spacebar_assignment_changed)
        
        spacebar_layout = QVBoxLayout(spacebar_group)
        spacebar_layout.addWidget(self.spacebar_widget)
        
        parent_layout.addWidget(spacebar_group)
    
    def create_combined_tag_row(self, tag_id: str, tag_info: Dict, available_shortcuts: List[str]) -> QWidget:
        """Create a combined row widget for tag editing with shortcut assignment"""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 8, 0, 8)
        
        # Color button
        color_btn = QPushButton()
        color_btn.setFixedSize(35, 35)
        color_btn.setStyleSheet(f"""
            background-color: {tag_info['color']}; 
            border: 2px solid #2f3336; 
            border-radius: 6px;
        """)
        color_btn.clicked.connect(lambda checked, tid=tag_id: self.pick_color(tid))
        color_btn.setToolTip("Click to change color")
        row_layout.addWidget(color_btn)
        
        # Name entry
        name_entry = QLineEdit(tag_info['name'])
        name_entry.setStyleSheet("""
            background-color: #252525; 
            color: white; 
            border: 1px solid #2f3336; 
            padding: 8px;
            border-radius: 4px;
            font-size: 13px;
        """)
        name_entry.setMinimumWidth(150)
        row_layout.addWidget(name_entry)
        
        # Usage count
        usage_count = self.tag_manager.get_tag_usage_count(tag_id)
        usage_label = QLabel(f"{usage_count} messages")
        usage_label.setStyleSheet("color: #8b8b8b; font-size: 12px;")
        usage_label.setMinimumWidth(80)
        usage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(usage_label)
        
        # Shortcut assignment combo
        current_shortcut = self.shortcut_manager.get_shortcut_for_tag(tag_id)
        shortcut_combo = QComboBox()
        shortcut_combo.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                color: white;
                border: 1px solid #2f3336;
                padding: 6px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 100px;
            }
        """)
        
        # Add shortcut options
        shortcut_combo.addItem("No shortcut", "")
        for shortcut in available_shortcuts:
            shortcut_combo.addItem(shortcut, shortcut)
        
        # Set current selection
        if current_shortcut and current_shortcut in available_shortcuts:
            index = shortcut_combo.findData(current_shortcut)
            if index >= 0:
                shortcut_combo.setCurrentIndex(index)
        
        # Connect shortcut change handler
        shortcut_combo.currentTextChanged.connect(
            lambda: self.on_combined_shortcut_changed(tag_id, shortcut_combo)
        )
        
        row_layout.addWidget(shortcut_combo)
        
        self.tag_widgets[tag_id] = {
            'name_entry': name_entry,
            'color_btn': color_btn,
            'color': tag_info['color'],
            'usage_label': usage_label,
            'shortcut_combo': shortcut_combo
        }
        
        return row_widget
    
    def setup_buttons(self, parent_layout):
        """Set up dialog buttons"""
        parent_layout.addSpacing(20)
        
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to right-align buttons
        buttons_layout.addStretch()
        
        # Save/Cancel buttons
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(self.get_button_style("#1d9bf0"))
        save_btn.clicked.connect(self.save_changes)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self.get_button_style("#252525"))
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        
        parent_layout.addWidget(buttons_widget)
    
    def get_button_style(self, color: str) -> str:
        """Get button stylesheet"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: 500;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color_brightness(color, 0.1)};
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_color_brightness(color, -0.1)};
            }}
        """
    
    def adjust_color_brightness(self, color: str, factor: float) -> str:
        """Adjust color brightness"""
        try:
            color_obj = QColor(color)
            h, s, v, a = color_obj.getHsv()
            v = max(0, min(255, int(v * (1 + factor))))
            color_obj.setHsv(h, s, v, a)
            return color_obj.name()
        except:
            return color
    
    def pick_color(self, tag_id: str):
        """Open color picker for a tag"""
        current_color = QColor(self.tag_widgets[tag_id]['color'])
        color = QColorDialog.getColor(current_color, self, "Select Tag Color")
        
        if color.isValid():
            self.tag_widgets[tag_id]['color'] = color.name()
            self.tag_widgets[tag_id]['color_btn'].setStyleSheet(f"""
                background-color: {color.name()}; 
                border: 2px solid #2f3336; 
                border-radius: 6px;
            """)
    
    def on_combined_shortcut_changed(self, tag_id: str, combo_box: QComboBox):
        """Handle shortcut assignment change in combined view"""
        new_shortcut = combo_box.currentData()
        
        # Remove old shortcut assignment if any
        old_shortcut = self.shortcut_manager.get_shortcut_for_tag(tag_id)
        if old_shortcut and old_shortcut != new_shortcut:
            # Update other combos that had this shortcut to "No shortcut"
            for other_tag_id, widgets in self.tag_widgets.items():
                if other_tag_id != tag_id and 'shortcut_combo' in widgets:
                    if widgets['shortcut_combo'].currentData() == new_shortcut:
                        widgets['shortcut_combo'].setCurrentIndex(0)  # "No shortcut"
        
        # If assigning a shortcut that's already taken, remove it from the other tag
        if new_shortcut:
            for other_tag_id, widgets in self.tag_widgets.items():
                if other_tag_id != tag_id and 'shortcut_combo' in widgets:
                    if widgets['shortcut_combo'].currentData() == new_shortcut:
                        widgets['shortcut_combo'].setCurrentIndex(0)  # "No shortcut"
    
    def on_spacebar_assignment_changed(self, tag_id: str):
        """Handle spacebar assignment change"""
        # In the combined interface, spacebar assignment is handled separately
        # from the main shortcut combos, so no need to update them here
        pass
    
    def save_changes(self):
        """Save all changes"""
        try:
            # Save tag changes (name and color)
            for tag_id, widgets in self.tag_widgets.items():
                name = widgets['name_entry'].text().strip()
                color = widgets['color']
                
                if name:  # Only save if name is not empty
                    self.tag_manager.update_tag(tag_id, name, color)
            
            # Save shortcut changes from combined interface
            for tag_id, widgets in self.tag_widgets.items():
                if 'shortcut_combo' in widgets:
                    new_shortcut = widgets['shortcut_combo'].currentData()
                    old_shortcut = self.shortcut_manager.get_shortcut_for_tag(tag_id)
                    
                    # Remove old shortcut if it exists
                    if old_shortcut and old_shortcut != new_shortcut:
                        self.shortcut_manager.remove_shortcut(old_shortcut)
                    
                    # Assign new shortcut if one is selected
                    if new_shortcut:
                        self.shortcut_manager.assign_shortcut(new_shortcut, tag_id)
            
            # Save spacebar assignment
            selected_tag = self.spacebar_widget.tag_combo.currentData()
            self.shortcut_manager.assign_spacebar_tag(selected_tag)
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
    
    def apply_dark_theme(self):
        """Apply dark theme to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: white;
            }
            QLabel {
                color: white;
            }
            QScrollArea {
                border: 1px solid #2f3336;
                background-color: #1a1a1a;
            }
            QComboBox {
                background-color: #252525;
                color: white;
                border: 1px solid #2f3336;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
        """)
