#!/usr/bin/env python3
"""
Message Statistics Dashboard

Main dashboard widget for displaying comprehensive message statistics
with charts and analytics in a modern, dark-themed interface.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGroupBox, QGridLayout,
    QSplitter, QTabWidget, QTextEdit, QSizePolicy, QSpacerItem,
    QMessageBox, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QIcon

from parsers.base_parser import Conversation, Message
from .stats_calculator import StatisticsCalculator, MessageStats
from .chart_widgets import BarChart, PieChart, LineChart, ChartWidget
from .stats_exporter import StatsExporter
from .sentiment_dashboard_tab import SentimentDashboardTab


class StatsCalculationThread(QThread):
    """Background thread for calculating statistics"""
    
    statsCalculated = pyqtSignal(object)  # MessageStats
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, conversations: List[Conversation]):
        super().__init__()
        self.conversations = conversations
        self.calculator = StatisticsCalculator()
    
    def run(self):
        try:
            self.calculator.set_conversations(self.conversations)
            stats = self.calculator.calculate_stats()
            self.statsCalculated.emit(stats)
        except Exception as e:
            self.errorOccurred.emit(str(e))


class StatCard(QFrame):
    """Individual statistic card widget"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            StatCard {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 10px;
            }
            StatCard:hover {
                border-color: #007aff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #999; font-size: 12px; font-weight: normal;")
        layout.addWidget(self.title_label)
        
        # Value (store reference for easy updates)
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        layout.addWidget(self.value_label)
        
        # Subtitle
        self.subtitle_label = None
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet("color: #bbb; font-size: 11px;")
            layout.addWidget(self.subtitle_label)
        
        layout.addStretch()
        self.setFixedHeight(100)
    
    def update_value(self, value: str):
        """Update the value displayed on the card"""
        self.value_label.setText(value)
    
    def update_subtitle(self, subtitle: str):
        """Update the subtitle displayed on the card"""
        if self.subtitle_label:
            self.subtitle_label.setText(subtitle)
        elif subtitle:
            # Create subtitle if it doesn't exist
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet("color: #bbb; font-size: 11px;")
            self.layout().insertWidget(-1, self.subtitle_label)  # Insert before stretch


class StatsDashboard(QMainWindow):
    """Main statistics dashboard window"""
    
    # Signals
    exportRequested = pyqtSignal(str)  # format
    
    def __init__(self, conversations: List[Conversation] = None, parent=None):
        super().__init__(parent)
        self.conversations = conversations or []
        self.calculator = StatisticsCalculator()
        self.exporter = StatsExporter()
        self.stats: Optional[MessageStats] = None
        
        self.setWindowTitle("Message Statistics Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                color: #dcdcdc;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #2d2d2d;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #dcdcdc;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #007aff;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #4d4d4d;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #dcdcdc;
            }
            QPushButton {
                background-color: #007aff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
            QLabel {
                color: #dcdcdc;
            }
        """)
        
        self.setup_ui()
        
        # Load data if provided
        if self.conversations:
            self.load_conversations(self.conversations)
    
    def setup_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with title and controls
        self.setup_header(main_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #2d2d2d;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #007aff;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Main content area with tabs
        self.setup_content_area(main_layout)
    
    def setup_header(self, layout):
        """Setup the header area with title and controls"""
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("Message Statistics Dashboard")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #fff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Control buttons
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_stats)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export PDF")
        export_btn.clicked.connect(self.export_pdf)
        header_layout.addWidget(export_btn)
        
        layout.addWidget(header_frame)
    
    def setup_content_area(self, layout):
        """Setup the main content area with tabs"""
        self.tab_widget = QTabWidget()
        
        # Overview tab
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # Temporal patterns tab
        self.temporal_tab = self.create_temporal_tab()
        self.tab_widget.addTab(self.temporal_tab, "Time Patterns")
        
        # User analytics tab
        self.users_tab = self.create_users_tab()
        self.tab_widget.addTab(self.users_tab, "User Analytics")
        
        # Response analysis tab
        self.response_tab = self.create_response_tab()
        self.tab_widget.addTab(self.response_tab, "Response Analysis")
        
        # Sentiment analysis tab
        self.sentiment_tab = SentimentDashboardTab()
        self.tab_widget.addTab(self.sentiment_tab, "Sentiment Analysis")
        
        layout.addWidget(self.tab_widget)
    
    def create_overview_tab(self) -> QWidget:
        """Create the overview tab with key statistics"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Stats cards grid
        cards_frame = QFrame()
        cards_layout = QGridLayout(cards_frame)
        
        # Placeholder cards (will be populated with real data)
        self.total_messages_card = StatCard("Total Messages", "0")
        self.conversations_card = StatCard("Conversations", "0")
        self.date_range_card = StatCard("Date Range", "No data")
        self.avg_length_card = StatCard("Avg Message Length", "0 chars")
        
        cards_layout.addWidget(self.total_messages_card, 0, 0)
        cards_layout.addWidget(self.conversations_card, 0, 1)
        cards_layout.addWidget(self.date_range_card, 0, 2)
        cards_layout.addWidget(self.avg_length_card, 0, 3)
        
        layout.addWidget(cards_frame)
        
        # Summary text area
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 10px;
                color: #dcdcdc;
            }
        """)
        summary_layout.addWidget(self.summary_text)
        
        layout.addWidget(summary_group)
        
        # Messages per sender chart
        sender_group = QGroupBox("Messages per Sender")
        sender_layout = QVBoxLayout(sender_group)
        
        self.sender_chart = BarChart(horizontal=True)
        self.sender_chart.dataPointClicked.connect(self.on_chart_clicked)
        sender_layout.addWidget(self.sender_chart)
        
        layout.addWidget(sender_group)
        
        return tab
    
    def create_temporal_tab(self) -> QWidget:
        """Create the temporal patterns tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Split into two charts
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Hourly activity
        hourly_group = QGroupBox("Messages by Hour of Day")
        hourly_layout = QVBoxLayout(hourly_group)
        
        self.hourly_chart = BarChart()
        self.hourly_chart.dataPointClicked.connect(self.on_chart_clicked)
        hourly_layout.addWidget(self.hourly_chart)
        
        splitter.addWidget(hourly_group)
        
        # Weekly activity
        weekly_group = QGroupBox("Messages by Day of Week")
        weekly_layout = QVBoxLayout(weekly_group)
        
        self.weekly_chart = BarChart()
        self.weekly_chart.dataPointClicked.connect(self.on_chart_clicked)
        weekly_layout.addWidget(self.weekly_chart)
        
        splitter.addWidget(weekly_group)
        
        layout.addWidget(splitter)
        
        return tab
    
    def create_users_tab(self) -> QWidget:
        """Create the user analytics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Split view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - pie chart
        pie_group = QGroupBox("Message Distribution")
        pie_layout = QVBoxLayout(pie_group)
        
        self.message_pie_chart = PieChart()
        self.message_pie_chart.dataPointClicked.connect(self.on_chart_clicked)
        pie_layout.addWidget(self.message_pie_chart)
        
        splitter.addWidget(pie_group)
        
        # Right side - average message length
        length_group = QGroupBox("Average Message Length by User")
        length_layout = QVBoxLayout(length_group)
        
        self.length_chart = BarChart(horizontal=True)
        self.length_chart.dataPointClicked.connect(self.on_chart_clicked)
        length_layout.addWidget(self.length_chart)
        
        splitter.addWidget(length_group)
        
        layout.addWidget(splitter)
        
        return tab
    
    def create_response_tab(self) -> QWidget:
        """Create the response analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Response time statistics
        response_group = QGroupBox("Average Response Times")
        response_layout = QVBoxLayout(response_group)
        
        self.response_chart = BarChart(horizontal=True)
        self.response_chart.dataPointClicked.connect(self.on_chart_clicked)
        response_layout.addWidget(self.response_chart)
        
        layout.addWidget(response_group)
        
        # Response time details
        details_group = QGroupBox("Response Time Details")
        details_layout = QVBoxLayout(details_group)
        
        self.response_details_text = QTextEdit()
        self.response_details_text.setReadOnly(True)
        self.response_details_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 10px;
                color: #dcdcdc;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        details_layout.addWidget(self.response_details_text)
        
        layout.addWidget(details_group)
        
        return tab
    
    def load_conversations(self, conversations: List[Conversation]):
        """Load conversation data and calculate statistics"""
        self.conversations = conversations
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Load conversations into sentiment tab
        self.sentiment_tab.load_conversations(conversations)
        
        # Calculate stats in background thread
        self.calc_thread = StatsCalculationThread(conversations)
        self.calc_thread.statsCalculated.connect(self.on_stats_calculated)
        self.calc_thread.errorOccurred.connect(self.on_calc_error)
        self.calc_thread.start()
    
    @pyqtSlot(object)
    def on_stats_calculated(self, stats: MessageStats):
        """Handle completion of statistics calculation"""
        self.progress_bar.setVisible(False)
        self.stats = stats
        self.update_all_displays()
    
    @pyqtSlot(str)
    def on_calc_error(self, error_msg: str):
        """Handle calculation error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Calculation Error", f"Error calculating statistics:\n{error_msg}")
    
    def update_all_displays(self):
        """Update all charts and displays with current statistics"""
        if not self.stats:
            return
        
        try:
            self.update_overview_tab()
            self.update_temporal_tab()
            self.update_users_tab()
            self.update_response_tab()
        except Exception as e:
            QMessageBox.warning(self, "Display Error", f"Error updating displays:\n{str(e)}")
    
    def update_overview_tab(self):
        """Update the overview tab with current statistics"""
        if not self.stats:
            return
        
        # Update stat cards using the new methods
        self.total_messages_card.update_value(f"{self.stats.total_messages:,}")
        self.conversations_card.update_value(f"{self.stats.conversation_count:,}")
        
        # Date range
        if self.stats.date_range[0] and self.stats.date_range[1]:
            start_date = self.stats.date_range[0].strftime("%Y-%m-%d")
            end_date = self.stats.date_range[1].strftime("%Y-%m-%d")
            date_text = f"{start_date} to {end_date}"
        else:
            date_text = "No data"
        
        self.date_range_card.update_value(date_text)
        self.avg_length_card.update_value(f"{self.stats.overall_average_length:.0f} chars")
        
        # Update summary text
        summary = self.generate_summary()
        self.summary_text.setPlainText(summary)
        
        # Update sender chart
        sender_data = [(sender, count) for sender, count in 
                       sorted(self.stats.messages_per_sender.items(), 
                              key=lambda x: x[1], reverse=True)[:10]]
        self.sender_chart.set_data(sender_data, "Top Message Senders", "Users", "Messages")
    
    def update_temporal_tab(self):
        """Update the temporal patterns tab"""
        if not self.stats:
            return
        
        # Hourly activity
        hourly_data = []
        for hour in range(24):
            count = self.stats.messages_by_hour.get(hour, 0)
            time_label = f"{hour:02d}:00"
            hourly_data.append((time_label, count))
        
        self.hourly_chart.set_data(hourly_data, "Hourly Message Activity", "Hour", "Messages")
        
        # Weekly activity
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_data = []
        for day in range(7):
            count = self.stats.messages_by_day_of_week.get(day, 0)
            weekly_data.append((day_names[day], count))
        
        self.weekly_chart.set_data(weekly_data, "Weekly Message Activity", "Day", "Messages")
    
    def update_users_tab(self):
        """Update the user analytics tab"""
        if not self.stats:
            return
        
        # Message distribution pie chart
        pie_data = [(sender, count) for sender, count in 
                    sorted(self.stats.messages_per_sender.items(), 
                           key=lambda x: x[1], reverse=True)[:8]]
        self.message_pie_chart.set_data(pie_data, "Message Distribution by User")
        
        # Average message length
        length_data = [(sender, length) for sender, length in 
                       sorted(self.stats.average_message_length.items(), 
                              key=lambda x: x[1], reverse=True)[:10]]
        self.length_chart.set_data(length_data, "Average Message Length", "Users", "Characters")
    
    def update_response_tab(self):
        """Update the response analysis tab"""
        if not self.stats:
            return
        
        # Response times chart
        response_data = []
        for sender, avg_time in sorted(self.stats.average_response_times.items(), 
                                      key=lambda x: x[1]):
            # Convert minutes to more readable format
            if avg_time < 60:
                time_str = f"{avg_time:.1f}m"
            elif avg_time < 1440:  # Less than a day
                hours = avg_time / 60
                time_str = f"{hours:.1f}h"
            else:
                days = avg_time / 1440
                time_str = f"{days:.1f}d"
            
            response_data.append((sender, avg_time))
        
        self.response_chart.set_data(response_data, "Average Response Times", "Users", "Minutes")
        
        # Response details text
        details = self.generate_response_details()
        self.response_details_text.setPlainText(details)
    
    def generate_summary(self) -> str:
        """Generate a text summary of the statistics"""
        if not self.stats:
            return "No data available."
        
        summary_parts = []
        
        # Basic stats
        summary_parts.append(f"📊 CONVERSATION SUMMARY")
        summary_parts.append(f"Total Messages: {self.stats.total_messages:,}")
        summary_parts.append(f"Conversations: {self.stats.conversation_count:,}")
        summary_parts.append(f"Average Message Length: {self.stats.overall_average_length:.0f} characters")
        
        # Date range
        if self.stats.date_range[0] and self.stats.date_range[1]:
            duration = self.stats.date_range[1] - self.stats.date_range[0]
            summary_parts.append(f"Duration: {duration.days} days")
        
        # Most active
        if self.stats.most_prolific_sender:
            summary_parts.append(f"Most Active User: {self.stats.most_prolific_sender}")
        
        # Time patterns
        hour_names = ["12AM", "1AM", "2AM", "3AM", "4AM", "5AM", "6AM", "7AM", "8AM", "9AM", "10AM", "11AM",
                     "12PM", "1PM", "2PM", "3PM", "4PM", "5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM"]
        summary_parts.append(f"Most Active Hour: {hour_names[self.stats.most_active_hour]}")
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        summary_parts.append(f"Most Active Day: {day_names[self.stats.most_active_day]}")
        
        # Response times
        if self.stats.fastest_responder:
            avg_time = self.stats.average_response_times.get(self.stats.fastest_responder, 0)
            if avg_time < 60:
                time_str = f"{avg_time:.1f} minutes"
            elif avg_time < 1440:
                time_str = f"{avg_time/60:.1f} hours"
            else:
                time_str = f"{avg_time/1440:.1f} days"
            summary_parts.append(f"Fastest Responder: {self.stats.fastest_responder} ({time_str})")
        
        return "\n".join(summary_parts)
    
    def generate_response_details(self) -> str:
        """Generate detailed response time analysis"""
        if not self.stats or not self.stats.response_times:
            return "No response time data available."
        
        details = []
        details.append("RESPONSE TIME ANALYSIS")
        details.append("=" * 50)
        
        for sender in sorted(self.stats.response_times.keys()):
            times = self.stats.response_times[sender]
            if not times:
                continue
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            median_time = sorted(times)[len(times) // 2]
            
            details.append(f"\n{sender}:")
            details.append(f"  Responses: {len(times)}")
            details.append(f"  Average: {self.format_time(avg_time)}")
            details.append(f"  Median:  {self.format_time(median_time)}")
            details.append(f"  Fastest: {self.format_time(min_time)}")
            details.append(f"  Slowest: {self.format_time(max_time)}")
        
        return "\n".join(details)
    
    def format_time(self, minutes: float) -> str:
        """Format time duration for display"""
        if minutes < 1:
            return f"{minutes*60:.0f}s"
        elif minutes < 60:
            return f"{minutes:.1f}m"
        elif minutes < 1440:
            return f"{minutes/60:.1f}h"
        else:
            return f"{minutes/1440:.1f}d"
    
    def refresh_stats(self):
        """Refresh statistics calculation"""
        if self.conversations:
            self.load_conversations(self.conversations)
    
    def export_pdf(self):
        """Export statistics to PDF"""
        if not self.stats:
            QMessageBox.warning(self, "No Data", "No statistics to export.")
            return
        
        # Check if sentiment analysis should be included
        include_sentiment = False
        sentiment_data = None
        
        if hasattr(self, 'sentiment_tab') and self.sentiment_tab.current_sentiment:
            reply = QMessageBox.question(
                self, "Include Sentiment Analysis", 
                "Include sentiment analysis in the PDF report?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                include_sentiment = True
                sentiment_data = self.sentiment_tab.current_sentiment
        
        # Determine default filename based on participants
        if self.conversations and len(self.conversations) == 1:
            participants = self.conversations[0].participants
            default_filename = f"{'_'.join(participants)}_statistics.pdf"
        elif self.conversations and len(self.conversations) > 1:
            # Use up to 3 participants from the first conversation for the filename
            participants = self.conversations[0].participants[:3]
            default_filename = f"{'_'.join(participants)}_and_others_statistics.pdf"
        else:
            default_filename = "message_statistics.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Statistics", default_filename, "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                # Create a new stats object with sentiment data if needed
                export_stats = self.stats
                if include_sentiment and sentiment_data:
                    # Create a copy of stats with sentiment data
                    from dataclasses import replace
                    export_stats = replace(
                        self.stats,
                        sentiment_data=sentiment_data,
                        sentiment_enabled=True
                    )
                
                self.exporter.export_to_pdf(export_stats, file_path)
                QMessageBox.information(self, "Export Complete", f"Statistics exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting PDF:\n{str(e)}")
    
    def on_chart_clicked(self, label: str, value):
        """Handle chart data point clicks"""
        QMessageBox.information(self, "Chart Data", f"Label: {label}\nValue: {value}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up any running threads
        if hasattr(self, 'calc_thread') and self.calc_thread.isRunning():
            self.calc_thread.terminate()
            self.calc_thread.wait()
        
        event.accept()
