#!/usr/bin/env python3
"""
Custom Chart Widgets for Message Statistics Dashboard

Provides lightweight chart widgets using PyQt6 QPainter for visualization
without external dependencies. Matches the dark theme of the application.
"""

from typing import List, Tuple, Dict, Optional, Any
import math

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, 
    QPainterPath, QLinearGradient, QRadialGradient
)


class ChartWidget(QWidget):
    """Base class for all chart widgets with dark theme support"""
    
    # Signals
    dataPointClicked = pyqtSignal(str, object)  # label, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Dark theme colors
        self.bg_color = QColor(26, 26, 26)  # #1a1a1a
        self.grid_color = QColor(50, 50, 50)  # #323232
        self.text_color = QColor(220, 220, 220)  # #dcdcdc
        self.accent_color = QColor(0, 122, 255)  # #007aff
        self.secondary_color = QColor(255, 159, 10)  # #ff9f0a
        
        # Chart colors palette
        self.chart_colors = [
            QColor(0, 122, 255),    # Blue
            QColor(255, 159, 10),   # Orange
            QColor(52, 199, 89),    # Green
            QColor(255, 69, 58),    # Red
            QColor(191, 90, 242),   # Purple
            QColor(100, 210, 255),  # Light Blue
            QColor(255, 214, 10),   # Yellow
            QColor(175, 82, 222),   # Magenta
            QColor(162, 132, 94),   # Brown
            QColor(142, 142, 147),  # Gray
        ]
        
        # Data
        self.data: List[Tuple[str, float]] = []
        self.title = ""
        self.x_label = ""
        self.y_label = ""
        
        # Animation
        self.animation_progress = 1.0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.hover_index = -1
    
    def set_data(self, data: List[Tuple[str, float]], title: str = "", 
                 x_label: str = "", y_label: str = "") -> None:
        """Set chart data and labels"""
        self.data = data.copy()
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.start_animation()
        self.update()
    
    def start_animation(self) -> None:
        """Start entrance animation"""
        self.animation_progress = 0.0
        self.animation_timer.start(16)  # ~60 FPS
    
    def _animate(self) -> None:
        """Animation step"""
        self.animation_progress += 0.05
        if self.animation_progress >= 1.0:
            self.animation_progress = 1.0
            self.animation_timer.stop()
        self.update()
    
    def paintEvent(self, event):
        """Base paint event - draws background and title"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Draw title
        if self.title:
            painter.setPen(self.text_color)
            font = QFont("Segoe UI", 14, QFont.Weight.Bold)
            painter.setFont(font)
            
            title_rect = QRect(0, 10, self.width(), 30)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
    
    def get_chart_rect(self) -> QRect:
        """Get the rectangle available for chart drawing"""
        if hasattr(self, 'horizontal') and self.horizontal and self.data:
            # For horizontal charts, calculate needed space for labels
            max_label_width = 0
            if self.data:
                font = QFont("Segoe UI", 9)
                font_metrics = QFontMetrics(font)
                for label, _ in self.data:
                    label_width = font_metrics.horizontalAdvance(label)
                    max_label_width = max(max_label_width, label_width)
            
            # Use at least 80 pixels, but more if needed for labels
            left_margin = max(80, max_label_width + 20)
            right_margin = 60
        else:
            left_margin = 60
            right_margin = 60
        
        title_height = 40 if self.title else 10
        
        return QRect(
            left_margin, 
            title_height, 
            self.width() - left_margin - right_margin, 
            self.height() - title_height - 60
        )


class BarChart(ChartWidget):
    """Horizontal and vertical bar chart widget"""
    
    def __init__(self, parent=None, horizontal=False):
        super().__init__(parent)
        self.horizontal = horizontal
        self.bar_spacing = 0.1  # Spacing between bars as fraction of bar width
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.data:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        chart_rect = self.get_chart_rect()
        
        if self.horizontal:
            self._draw_horizontal_bars(painter, chart_rect)
        else:
            self._draw_vertical_bars(painter, chart_rect)
    
    def _draw_vertical_bars(self, painter: QPainter, rect: QRect) -> None:
        """Draw vertical bar chart"""
        if not self.data:
            return
        
        # Calculate bar dimensions
        bar_count = len(self.data)
        total_spacing = rect.width() * self.bar_spacing
        bar_width = (rect.width() - total_spacing) / bar_count
        spacing = total_spacing / (bar_count + 1)
        
        # Find max value for scaling
        max_value = max(value for _, value in self.data) if self.data else 1
        if max_value == 0:
            max_value = 1
        
        # Draw bars
        for i, (label, value) in enumerate(self.data):
            # Calculate bar position and height
            x = rect.x() + spacing + i * (bar_width + spacing / bar_count)
            bar_height = (value / max_value) * rect.height() * self.animation_progress
            y = rect.bottom() - bar_height
            
            # Color selection
            color = self.chart_colors[i % len(self.chart_colors)]
            
            # Hover effect
            if i == self.hover_index:
                color = color.lighter(120)
            
            # Draw bar with gradient
            gradient = QLinearGradient(0, y, 0, rect.bottom())
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, color.darker(140))
            
            painter.fillRect(int(x), int(y), int(bar_width), int(bar_height), gradient)
            
            # Draw value on top of bar
            if bar_height > 20:
                painter.setPen(self.text_color)
                font = QFont("Segoe UI", 9)
                painter.setFont(font)
                
                value_text = f"{value:.0f}" if value == int(value) else f"{value:.1f}"
                text_rect = QRect(int(x), int(y - 20), int(bar_width), 20)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, value_text)
            
            # Draw label below bar
            painter.setPen(self.text_color)
            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            
            # Rotate text for long labels
            if len(label) > 8:
                painter.save()
                painter.translate(x + bar_width / 2, rect.bottom() + 40)
                painter.rotate(-45)
                painter.drawText(0, 0, label)
                painter.restore()
            else:
                label_rect = QRect(int(x), rect.bottom() + 5, int(bar_width), 30)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)
    
    def _draw_horizontal_bars(self, painter: QPainter, rect: QRect) -> None:
        """Draw horizontal bar chart"""
        if not self.data:
            return
        
        # Calculate bar dimensions
        bar_count = len(self.data)
        total_spacing = rect.height() * self.bar_spacing
        bar_height = (rect.height() - total_spacing) / bar_count
        spacing = total_spacing / (bar_count + 1)
        
        # Find max value for scaling
        max_value = max(value for _, value in self.data) if self.data else 1
        if max_value == 0:
            max_value = 1
        
        # Draw bars
        for i, (label, value) in enumerate(self.data):
            # Calculate bar position and width
            y = rect.y() + spacing + i * (bar_height + spacing / bar_count)
            bar_width = (value / max_value) * rect.width() * self.animation_progress
            
            # Color selection
            color = self.chart_colors[i % len(self.chart_colors)]
            
            # Hover effect
            if i == self.hover_index:
                color = color.lighter(120)
            
            # Draw bar with gradient
            gradient = QLinearGradient(rect.x(), 0, rect.x() + bar_width, 0)
            gradient.setColorAt(0, color.darker(140))
            gradient.setColorAt(1, color)
            
            painter.fillRect(rect.x(), int(y), int(bar_width), int(bar_height), gradient)
            
            # Draw value at end of bar
            painter.setPen(self.text_color)
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            
            value_text = f"{value:.0f}" if value == int(value) else f"{value:.1f}"
            painter.drawText(int(rect.x() + bar_width + 5), int(y + bar_height / 2), value_text)
            
            # Draw label
            label_rect = QRect(10, int(y), rect.x() - 15, int(bar_height))
            
            # Truncate label if it's too long
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)
            available_width = label_rect.width()
            
            display_label = label
            if font_metrics.horizontalAdvance(label) > available_width:
                # Truncate and add ellipsis
                while len(display_label) > 3 and font_metrics.horizontalAdvance(display_label + "...") > available_width:
                    display_label = display_label[:-1]
                display_label += "..."
            
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, display_label)
    
    def mouseMoveEvent(self, event):
        """Handle mouse hover for highlighting"""
        if not self.data:
            return
        
        chart_rect = self.get_chart_rect()
        pos = event.position().toPoint()
        
        # Check if mouse is over a bar
        old_hover = self.hover_index
        self.hover_index = -1
        
        if self.horizontal:
            # Horizontal bars
            if chart_rect.contains(pos):
                bar_count = len(self.data)
                total_spacing = chart_rect.height() * self.bar_spacing
                bar_height = (chart_rect.height() - total_spacing) / bar_count
                spacing = total_spacing / (bar_count + 1)
                
                for i in range(bar_count):
                    y = chart_rect.y() + spacing + i * (bar_height + spacing / bar_count)
                    if y <= pos.y() <= y + bar_height:
                        self.hover_index = i
                        break
        else:
            # Vertical bars
            if chart_rect.contains(pos):
                bar_count = len(self.data)
                total_spacing = chart_rect.width() * self.bar_spacing
                bar_width = (chart_rect.width() - total_spacing) / bar_count
                spacing = total_spacing / (bar_count + 1)
                
                for i in range(bar_count):
                    x = chart_rect.x() + spacing + i * (bar_width + spacing / bar_count)
                    if x <= pos.x() <= x + bar_width:
                        self.hover_index = i
                        break
        
        if old_hover != self.hover_index:
            self.update()
    
    def mousePressEvent(self, event):
        """Handle bar clicks"""
        if self.hover_index >= 0 and self.hover_index < len(self.data):
            label, value = self.data[self.hover_index]
            self.dataPointClicked.emit(label, value)


class PieChart(ChartWidget):
    """Pie chart widget with labels and percentages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_percentages = True
        self.show_labels = True
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.data:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        chart_rect = self.get_chart_rect()
        
        # Calculate pie chart dimensions - leave space for legend on the right
        legend_width = 150  # Reserve space for legend
        available_width = chart_rect.width() - legend_width
        available_height = chart_rect.height()
        
        size = min(available_width, available_height) - 40
        pie_rect = QRect(
            chart_rect.x() + (available_width - size) // 2,
            chart_rect.y() + (available_height - size) // 2,
            size,
            size
        )
        
        self._draw_pie(painter, pie_rect)
        self._draw_legend(painter, chart_rect, pie_rect)
    
    def _draw_pie(self, painter: QPainter, rect: QRect) -> None:
        """Draw the pie chart"""
        if not self.data:
            return
        
        total_value = sum(value for _, value in self.data)
        if total_value == 0:
            return
        
        start_angle = 0
        
        for i, (label, value) in enumerate(self.data):
            # Calculate slice angle
            angle = (value / total_value) * 360 * self.animation_progress
            
            # Color selection
            color = self.chart_colors[i % len(self.chart_colors)]
            
            # Hover effect
            if i == self.hover_index:
                color = color.lighter(120)
                # Slightly expand hovered slice
                expanded_rect = rect.adjusted(-5, -5, 5, 5)
                painter.setBrush(color)
                painter.setPen(QPen(self.bg_color, 2))
                painter.drawPie(expanded_rect, int(start_angle * 16), int(angle * 16))
            else:
                painter.setBrush(color)
                painter.setPen(QPen(self.bg_color, 2))
                painter.drawPie(rect, int(start_angle * 16), int(angle * 16))
            
            start_angle += angle
    
    def _draw_legend(self, painter: QPainter, chart_rect: QRect, pie_rect: QRect) -> None:
        """Draw legend with labels and percentages"""
        if not self.data:
            return
        
        total_value = sum(value for _, value in self.data)
        if total_value == 0:
            return
        
        # Legend position (right side of pie)
        legend_x = pie_rect.right() + 20
        legend_y = pie_rect.y()
        legend_width = chart_rect.right() - legend_x
        
        painter.setPen(self.text_color)
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        
        line_height = 25
        
        for i, (label, value) in enumerate(self.data):
            y = legend_y + i * line_height
            
            # Draw color indicator
            color = self.chart_colors[i % len(self.chart_colors)]
            painter.fillRect(legend_x, y + 5, 15, 15, color)
            
            # Draw label and percentage
            percentage = (value / total_value) * 100
            text = f"{label}"
            if self.show_percentages:
                text += f" ({percentage:.1f}%)"
            
            # Truncate text if it's too long for the available space
            available_width = legend_width - 25  # Account for color indicator and padding
            font_metrics = QFontMetrics(font)
            
            display_text = text
            if font_metrics.horizontalAdvance(text) > available_width:
                # Try to truncate just the label part, keeping the percentage
                if self.show_percentages:
                    percentage_text = f" ({percentage:.1f}%)"
                    percentage_width = font_metrics.horizontalAdvance(percentage_text)
                    available_for_label = available_width - percentage_width
                    
                    truncated_label = label
                    while len(truncated_label) > 3 and font_metrics.horizontalAdvance(truncated_label + "...") > available_for_label:
                        truncated_label = truncated_label[:-1]
                    
                    if len(truncated_label) > 3:
                        display_text = truncated_label + "..." + percentage_text
                    else:
                        display_text = truncated_label + percentage_text
                else:
                    # Just truncate the label
                    while len(display_text) > 3 and font_metrics.horizontalAdvance(display_text + "...") > available_width:
                        display_text = display_text[:-1]
                    display_text += "..."
            
            painter.drawText(legend_x + 20, y + 17, display_text)
    
    def mouseMoveEvent(self, event):
        """Handle mouse hover for highlighting"""
        if not self.data:
            return
        
        chart_rect = self.get_chart_rect()
        
        # Calculate pie chart dimensions - same as in paintEvent
        legend_width = 150  # Reserve space for legend
        available_width = chart_rect.width() - legend_width
        available_height = chart_rect.height()
        
        size = min(available_width, available_height) - 40
        pie_rect = QRect(
            chart_rect.x() + (available_width - size) // 2,
            chart_rect.y() + (available_height - size) // 2,
            size,
            size
        )
        
        pos = event.position().toPoint()
        center = pie_rect.center()
        
        # Calculate distance from center
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        distance = math.sqrt(dx * dx + dy * dy)
        radius = size / 2
        
        old_hover = self.hover_index
        self.hover_index = -1
        
        if distance <= radius:
            # Calculate angle
            angle = math.atan2(dy, dx)
            if angle < 0:
                angle += 2 * math.pi
            angle_degrees = math.degrees(angle)
            
            # Find which slice this angle belongs to
            total_value = sum(value for _, value in self.data)
            if total_value > 0:
                current_angle = 0
                for i, (_, value) in enumerate(self.data):
                    slice_angle = (value / total_value) * 360
                    if current_angle <= angle_degrees <= current_angle + slice_angle:
                        self.hover_index = i
                        break
                    current_angle += slice_angle
        
        if old_hover != self.hover_index:
            self.update()
    
    def mousePressEvent(self, event):
        """Handle slice clicks"""
        if self.hover_index >= 0 and self.hover_index < len(self.data):
            label, value = self.data[self.hover_index]
            self.dataPointClicked.emit(label, value)


class LineChart(ChartWidget):
    """Line chart widget for time series data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_points = True
        self.show_grid = True
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.data:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        chart_rect = self.get_chart_rect()
        self._draw_grid(painter, chart_rect)
        self._draw_line(painter, chart_rect)
        self._draw_axes(painter, chart_rect)
    
    def _draw_grid(self, painter: QPainter, rect: QRect) -> None:
        """Draw grid lines"""
        if not self.show_grid:
            return
        
        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DotLine))
        
        # Vertical grid lines
        grid_count = min(len(self.data), 10)
        for i in range(grid_count + 1):
            x = rect.x() + (i / grid_count) * rect.width()
            painter.drawLine(int(x), rect.y(), int(x), rect.bottom())
        
        # Horizontal grid lines
        for i in range(6):
            y = rect.y() + (i / 5) * rect.height()
            painter.drawLine(rect.x(), int(y), rect.right(), int(y))
    
    def _draw_line(self, painter: QPainter, rect: QRect) -> None:
        """Draw the line and data points"""
        if len(self.data) < 2:
            return
        
        # Find min/max values for scaling
        values = [value for _, value in self.data]
        min_value = min(values)
        max_value = max(values)
        
        if max_value == min_value:
            max_value = min_value + 1
        
        # Calculate points
        points = []
        for i, (_, value) in enumerate(self.data):
            x = rect.x() + (i / (len(self.data) - 1)) * rect.width()
            y = rect.bottom() - ((value - min_value) / (max_value - min_value)) * rect.height()
            y *= self.animation_progress
            y += rect.bottom() * (1 - self.animation_progress)
            points.append((x, y))
        
        # Draw line
        painter.setPen(QPen(self.accent_color, 3))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Draw points
        if self.show_points:
            painter.setBrush(self.accent_color)
            painter.setPen(QPen(self.bg_color, 2))
            
            for i, (x, y) in enumerate(points):
                radius = 6
                if i == self.hover_index:
                    radius = 8
                
                painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)
    
    def _draw_axes(self, painter: QPainter, rect: QRect) -> None:
        """Draw axis labels"""
        painter.setPen(self.text_color)
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        
        # X-axis labels
        label_count = min(len(self.data), 8)
        for i in range(0, len(self.data), max(1, len(self.data) // label_count)):
            label, _ = self.data[i]
            x = rect.x() + (i / (len(self.data) - 1)) * rect.width()
            
            # Rotate long labels
            if len(label) > 6:
                painter.save()
                painter.translate(x, rect.bottom() + 30)
                painter.rotate(-45)
                painter.drawText(0, 0, label)
                painter.restore()
            else:
                painter.drawText(int(x - 30), rect.bottom() + 20, 60, 20, 
                               Qt.AlignmentFlag.AlignCenter, label)
    
    def mouseMoveEvent(self, event):
        """Handle mouse hover for highlighting points"""
        if not self.data:
            return
        
        chart_rect = self.get_chart_rect()
        pos = event.position().toPoint()
        
        old_hover = self.hover_index
        self.hover_index = -1
        
        if chart_rect.contains(pos):
            # Find closest point
            min_distance = float('inf')
            values = [value for _, value in self.data]
            min_value = min(values)
            max_value = max(values)
            
            if max_value == min_value:
                max_value = min_value + 1
            
            for i, (_, value) in enumerate(self.data):
                x = chart_rect.x() + (i / (len(self.data) - 1)) * chart_rect.width()
                y = chart_rect.bottom() - ((value - min_value) / (max_value - min_value)) * chart_rect.height()
                
                distance = math.sqrt((pos.x() - x) ** 2 + (pos.y() - y) ** 2)
                if distance < min_distance and distance < 20:  # 20 pixel threshold
                    min_distance = distance
                    self.hover_index = i
        
        if old_hover != self.hover_index:
            self.update()
    
    def mousePressEvent(self, event):
        """Handle point clicks"""
        if self.hover_index >= 0 and self.hover_index < len(self.data):
            label, value = self.data[self.hover_index]
            self.dataPointClicked.emit(label, value)
