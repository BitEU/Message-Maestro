#!/usr/bin/env python3
"""
Sentiment Analysis Tab for Statistics Dashboard

Integrates sentiment analysis into the Message-Maestro statistics dashboard
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QRadioButton, QButtonGroup,
    QCheckBox, QMessageBox, QSplitter, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor

from parsers.base_parser import Conversation, Message
from message_stats.chart_widgets import LineChart, BarChart, PieChart
from message_stats.sentiment_analyzer import (
    SentimentAnalyzer, ConversationSentiment, SentimentScore,
    NLTK_AVAILABLE, TEXTBLOB_AVAILABLE
)

# Import sentiment analysis components


class SentimentAnalysisThread(QThread):
    """Background thread for sentiment analysis"""
    
    progressUpdate = pyqtSignal(int, str)  # progress percentage, status message
    analysisComplete = pyqtSignal(object)  # ConversationSentiment
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, conversation: Conversation, analyzer: SentimentAnalyzer):
        super().__init__()
        self.conversation = conversation
        self.analyzer = analyzer
        self.should_stop = False
    
    def run(self):
        try:
            total_messages = len(self.conversation.messages)
            
            # Start analysis
            self.progressUpdate.emit(0, "Starting sentiment analysis...")
            
            # Analyze conversation (the analyzer handles batching internally)
            sentiment_result = self.analyzer.analyze_conversation(self.conversation)
            
            self.progressUpdate.emit(100, "Analysis complete!")
            self.analysisComplete.emit(sentiment_result)
            
        except Exception as e:
            self.errorOccurred.emit(str(e))
    
    def stop(self):
        self.should_stop = True


class SentimentDashboardTab(QWidget):
    """Sentiment analysis tab for the statistics dashboard"""
    
    def __init__(self, conversations: List[Conversation] = None, parent=None):
        super().__init__(parent)
        self.conversations = conversations or []
        self.analyzer = None
        self.current_sentiment = None
        self.analysis_thread = None
        
        self.setup_ui()
        self.check_availability()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Configuration section
        self.create_config_section(layout)
        
        # Progress section (initially hidden)
        self.create_progress_section(layout)
        self.progress_widget.hide()
        
        # Results section
        self.create_results_section(layout)
        
        # Initially show setup message
        self.show_setup_message()
    
    def create_config_section(self, parent_layout):
        """Create configuration section for sentiment analysis"""
        config_group = QGroupBox("Sentiment Analysis Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Method selection
        method_label = QLabel("Analysis Method:")
        method_label.setStyleSheet("font-weight: bold; color: #dcdcdc;")
        config_layout.addWidget(method_label)
        
        self.method_group = QButtonGroup()
        
        # Auto method
        self.auto_radio = QRadioButton("Auto (Recommended)")
        self.auto_radio.setChecked(True)
        self.method_group.addButton(self.auto_radio, 0)
        config_layout.addWidget(self.auto_radio)
        
        # NLTK method
        self.nltk_radio = QRadioButton("NLTK VADER (Fast, Lightweight)")
        self.method_group.addButton(self.nltk_radio, 1)
        config_layout.addWidget(self.nltk_radio)
        
        # TextBlob method
        self.textblob_radio = QRadioButton("TextBlob (Simple, Lightweight)")
        self.method_group.addButton(self.textblob_radio, 2)
        config_layout.addWidget(self.textblob_radio)
        
        # System info
        self.system_info_label = QLabel("Checking system capabilities...")
        self.system_info_label.setStyleSheet("color: #8b8b8b; font-size: 9pt;")
        config_layout.addWidget(self.system_info_label)
        
        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #ff9f0a; font-size: 9pt;")
        self.warning_label.setWordWrap(True)
        config_layout.addWidget(self.warning_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Start Analysis")
        self.analyze_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #404040;
                color: #8b8b8b;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.analyze_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.hide()
        button_layout.addWidget(self.stop_btn)
        
        button_layout.addStretch()
        config_layout.addLayout(button_layout)
        
        parent_layout.addWidget(config_group)
    
    def create_progress_section(self, parent_layout):
        """Create progress indicator section"""
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #2d2d2d;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #007aff;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Initializing...")
        self.progress_label.setStyleSheet("color: #8b8b8b; font-size: 9pt;")
        progress_layout.addWidget(self.progress_label)
        
        parent_layout.addWidget(self.progress_widget)
    
    def create_results_section(self, parent_layout):
        """Create results display section"""
        self.results_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section - Overview and timeline
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # Overall sentiment card
        self.sentiment_card = self.create_sentiment_card()
        top_layout.addWidget(self.sentiment_card)
        
        # Sentiment timeline chart
        timeline_group = QGroupBox("Sentiment Timeline")
        timeline_layout = QVBoxLayout(timeline_group)
        
        self.timeline_chart = LineChart()
        self.timeline_chart.setMinimumHeight(200)
        timeline_layout.addWidget(self.timeline_chart)
        
        top_layout.addWidget(timeline_group, 2)
        
        self.results_splitter.addWidget(top_widget)
        
        # Middle section - Distribution charts
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        
        # Sentiment distribution pie chart
        dist_group = QGroupBox("Sentiment Distribution")
        dist_layout = QVBoxLayout(dist_group)
        
        self.distribution_chart = PieChart()
        self.distribution_chart.setMinimumHeight(250)
        dist_layout.addWidget(self.distribution_chart)
        
        middle_layout.addWidget(dist_group)
        
        # Per-sender sentiment
        sender_group = QGroupBox("Sentiment by Participant")
        sender_layout = QVBoxLayout(sender_group)
        
        self.sender_chart = BarChart(horizontal=True)
        self.sender_chart.setMinimumHeight(250)
        sender_layout.addWidget(self.sender_chart)
        
        middle_layout.addWidget(sender_group)
        
        self.results_splitter.addWidget(middle_widget)
        
        # Bottom section - Details and insights
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        # Summary and keywords
        insights_group = QGroupBox("Analysis Insights")
        insights_layout = QVBoxLayout(insights_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 10px;
                color: #dcdcdc;
            }
        """)
        insights_layout.addWidget(self.summary_text)
        
        bottom_layout.addWidget(insights_group)
        
        # Emotional peaks
        peaks_group = QGroupBox("Emotional Peaks")
        peaks_layout = QVBoxLayout(peaks_group)
        
        self.peaks_text = QTextEdit()
        self.peaks_text.setReadOnly(True)
        self.peaks_text.setMaximumHeight(150)
        self.peaks_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 10px;
                color: #dcdcdc;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        peaks_layout.addWidget(self.peaks_text)
        
        bottom_layout.addWidget(peaks_group)
        
        self.results_splitter.addWidget(bottom_widget)
        
        parent_layout.addWidget(self.results_splitter)
        
        # Initially hide results
        self.results_splitter.hide()
    
    def create_sentiment_card(self) -> QWidget:
        """Create overall sentiment display card"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)
        card.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(card)
        
        title = QLabel("Overall Sentiment")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #dcdcdc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.sentiment_value_label = QLabel("—")
        self.sentiment_value_label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        self.sentiment_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sentiment_value_label)
        
        self.sentiment_desc_label = QLabel("No analysis yet")
        self.sentiment_desc_label.setStyleSheet("font-size: 10pt; color: #8b8b8b;")
        self.sentiment_desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sentiment_desc_label)
        
        # Confidence indicator
        self.confidence_label = QLabel("Confidence: —")
        self.confidence_label.setStyleSheet("font-size: 9pt; color: #8b8b8b;")
        self.confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.confidence_label)
        
        card.setMaximumWidth(250)
        card.setMinimumHeight(150)
        
        return card
    
    def check_availability(self):
        """Check which sentiment analysis methods are available"""
        info_parts = []
        
        if NLTK_AVAILABLE:
            info_parts.append("✓ NLTK")
        else:
            info_parts.append("✗ NLTK")
            self.nltk_radio.setEnabled(False)
        
        if TEXTBLOB_AVAILABLE:
            info_parts.append("✓ TextBlob")
        else:
            info_parts.append("✗ TextBlob")
            self.textblob_radio.setEnabled(False)
        
        self.system_info_label.setText("Available: " + " | ".join(info_parts))
        
        # Disable analyze button if no methods available
        if not any([NLTK_AVAILABLE, TEXTBLOB_AVAILABLE]):
            self.analyze_btn.setEnabled(False)
            self.warning_label.setText(
                "⚠️ No sentiment analysis methods available. "
                "Please install: pip install nltk textblob"
            )
        else:
            self.analyze_btn.setEnabled(True)
            if NLTK_AVAILABLE and TEXTBLOB_AVAILABLE:
                self.warning_label.setText("")
            elif NLTK_AVAILABLE:
                self.warning_label.setText("ℹ️ TextBlob not available. Using NLTK only.")
            elif TEXTBLOB_AVAILABLE:
                self.warning_label.setText("ℹ️ NLTK not available. Using TextBlob only.")
        self.analyze_btn.setEnabled(
            NLTK_AVAILABLE or TEXTBLOB_AVAILABLE or True  # Always allow AI attempt
        )
    
    def load_conversations(self, conversations: List[Conversation]):
        """Load conversations for sentiment analysis"""
        self.conversations = conversations
        # Reset any existing analysis
        self.current_sentiment = None
        if hasattr(self, 'analysis_thread') and self.analysis_thread is not None:
            self.stop_analysis()
        # Show setup message again if needed
        if not conversations:
            self.show_setup_message()
        else:
            # Update button state based on available data
            self.analyze_btn.setEnabled(bool(conversations))
    
    def show_setup_message(self):
        """Show initial setup message"""
        if not hasattr(self, 'setup_label'):
            self.setup_label = QLabel(
                "Configure sentiment analysis settings above and click 'Start Analysis' to begin.\n\n"
                "• NLTK VADER: Fast, good for social media text\n"
                "• TextBlob: Simple, general-purpose"
            )
            self.setup_label.setStyleSheet("color: #8b8b8b; font-size: 10pt; padding: 20px;")
            self.setup_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_splitter.hide()
            self.layout().addWidget(self.setup_label)
    
    def hide_setup_message(self):
        """Hide setup message when analysis starts"""
        if hasattr(self, 'setup_label'):
            self.setup_label.hide()
            self.results_splitter.show()
    
    def start_analysis(self):
        """Start sentiment analysis"""
        if not self.conversations:
            QMessageBox.warning(self, "No Data", "No conversations loaded for analysis.")
            return
        
        # Hide setup message
        self.hide_setup_message()
        
        # Determine method
        method_map = {0: "auto", 1: "nltk", 2: "textblob"}
        selected_method = method_map[self.method_group.checkedId()]
        
        try:
            # Initialize analyzer
            self.analyzer = SentimentAnalyzer(method=selected_method)
            
            # Check what method was actually initialized (may have fallen back)
            actual_method = getattr(self.analyzer, 'method', selected_method)
            if actual_method != selected_method:
                # Show info about fallback
                fallback_msg = f"Using {actual_method} instead of {selected_method}"
                
                reply = QMessageBox.question(
                    self, "Method Changed", 
                    fallback_msg + "\n\nContinue with available method?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Show progress
            self.progress_widget.show()
            self.analyze_btn.hide()
            self.stop_btn.show()
            
            # Estimate time
            total_messages = sum(len(conv.messages) for conv in self.conversations)
            if hasattr(self.analyzer, 'estimate_processing_time'):
                estimated_time = self.analyzer.estimate_processing_time(total_messages)
                
                if estimated_time > 60:
                    self.progress_label.setText(f"Analyzing {total_messages} messages... "
                                              f"Estimated time: {estimated_time/60:.1f} minutes")
                else:
                    self.progress_label.setText(f"Analyzing {total_messages} messages... "
                                              f"Estimated time: {estimated_time:.0f} seconds")
            else:
                self.progress_label.setText(f"Analyzing {total_messages} messages...")
            
            # Start analysis in background thread
            # For now, analyze first conversation (extend to multiple later)
            self.analysis_thread = SentimentAnalysisThread(
                self.conversations[0], self.analyzer
            )
            self.analysis_thread.progressUpdate.connect(self.update_progress)
            self.analysis_thread.analysisComplete.connect(self.on_analysis_complete)
            self.analysis_thread.errorOccurred.connect(self.on_analysis_error)
            self.analysis_thread.start()
            
        except Exception as e:
            error_msg = str(e)
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize analyzer:\n{error_msg}")
            self.reset_ui()
    
    def stop_analysis(self):
        """Stop ongoing analysis"""
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
            self.analysis_thread.wait()
        
        self.reset_ui()
        self.progress_label.setText("Analysis stopped by user")
    
    @pyqtSlot(int, str)
    def update_progress(self, percentage: int, message: str):
        """Update progress bar and message"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    @pyqtSlot(object)
    def on_analysis_complete(self, sentiment_result: ConversationSentiment):
        """Handle completed analysis"""
        self.current_sentiment = sentiment_result
        self.display_results(sentiment_result)
        self.reset_ui()
        
        # Show completion message
        QMessageBox.information(self, "Analysis Complete", 
                              "Sentiment analysis completed successfully!")
    
    @pyqtSlot(str)
    def on_analysis_error(self, error_msg: str):
        """Handle analysis error"""
        QMessageBox.critical(self, "Analysis Error", f"Error during analysis:\n{error_msg}")
        self.reset_ui()
    
    def reset_ui(self):
        """Reset UI after analysis"""
        self.progress_widget.hide()
        self.analyze_btn.show()
        self.stop_btn.hide()
        self.progress_bar.setValue(0)
    
    def display_results(self, sentiment: ConversationSentiment):
        """Display sentiment analysis results"""
        # Update overall sentiment card
        self.update_sentiment_card(sentiment.overall_sentiment)
        
        # Update timeline chart
        self.update_timeline_chart(sentiment.sentiment_timeline)
        
        # Update distribution chart
        self.update_distribution_chart(sentiment.message_sentiments)
        
        # Update sender sentiment chart
        self.update_sender_chart(sentiment.sentiment_by_sender)
        
        # Update summary
        self.summary_text.setPlainText(sentiment.summary)
        
        # Add keywords
        if sentiment.keywords:
            keywords_text = "\n\nTop Keywords:\n"
            for word, count in sentiment.keywords[:10]:
                keywords_text += f"• {word}: {count} occurrences\n"
            self.summary_text.append(keywords_text)
        
        # Update emotional peaks
        self.update_emotional_peaks(sentiment.emotional_peaks)
        
        # Show results
        self.results_splitter.show()
    
    def update_sentiment_card(self, sentiment: SentimentScore):
        """Update the overall sentiment display card"""
        # Determine color and description based on score
        if sentiment.compound > 0.5:
            color = "#44ff44"
            description = "Very Positive"
            emoji = "😊"
        elif sentiment.compound > 0.1:
            color = "#88ff88"
            description = "Positive"
            emoji = "🙂"
        elif sentiment.compound < -0.5:
            color = "#ff4444"
            description = "Very Negative"
            emoji = "😔"
        elif sentiment.compound < -0.1:
            color = "#ff8888"
            description = "Negative"
            emoji = "😐"
        else:
            color = "#ffff88"
            description = "Neutral"
            emoji = "😶"
        
        self.sentiment_value_label.setText(f"{emoji} {sentiment.compound:.2f}")
        self.sentiment_value_label.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {color};")
        
        self.sentiment_desc_label.setText(description)
        self.confidence_label.setText(f"Confidence: {sentiment.confidence:.0%}")
    
    def update_timeline_chart(self, timeline: List[tuple[datetime, float]]):
        """Update sentiment timeline chart"""
        if not timeline:
            return
        
        # Group by time periods for better visualization
        chart_data = []
        for i, (timestamp, score) in enumerate(timeline):
            # Use message index for x-axis, actual score for y-axis
            chart_data.append((str(i+1), score))
        
        # Limit to 50 points for readability
        if len(chart_data) > 50:
            step = len(chart_data) // 50
            chart_data = chart_data[::step]
        
        self.timeline_chart.set_data(chart_data, "Sentiment Over Time", "Message", "Sentiment")
    
    def update_distribution_chart(self, message_sentiments: List[tuple[Message, SentimentScore]]):
        """Update sentiment distribution pie chart"""
        if not message_sentiments:
            return
        
        # Count sentiments
        positive = sum(1 for _, s in message_sentiments if s.compound > 0.1)
        negative = sum(1 for _, s in message_sentiments if s.compound < -0.1)
        neutral = len(message_sentiments) - positive - negative
        
        chart_data = [
            ("Positive", positive),
            ("Negative", negative),
            ("Neutral", neutral)
        ]
        
        self.distribution_chart.set_data(chart_data, "Message Sentiment Distribution")
    
    def update_sender_chart(self, sender_sentiments: Dict[str, SentimentScore]):
        """Update per-sender sentiment chart"""
        if not sender_sentiments:
            return
        
        chart_data = []
        for sender, sentiment in sender_sentiments.items():
            # Truncate long sender names
            display_name = sender[:20] + "..." if len(sender) > 20 else sender
            chart_data.append((display_name, sentiment.compound))
        
        # Sort by sentiment score
        chart_data.sort(key=lambda x: x[1], reverse=True)
        
        self.sender_chart.set_data(chart_data, "Average Sentiment by Participant", 
                                  "Participant", "Sentiment Score")
    
    def update_emotional_peaks(self, peaks: List[tuple[Message, SentimentScore]]):
        """Update emotional peaks display"""
        if not peaks:
            self.peaks_text.setPlainText("No significant emotional peaks detected.")
            return
        
        peaks_text = "Most Emotionally Charged Messages:\n\n"
        
        for i, (message, sentiment) in enumerate(peaks[:5], 1):
            # Determine if positive or negative
            emotion = "Positive" if sentiment.compound > 0 else "Negative"
            
            # Truncate message text
            text_preview = message.text[:100] + "..." if len(message.text) > 100 else message.text
            
            peaks_text += f"{i}. [{emotion} - Score: {sentiment.compound:.2f}]\n"
            peaks_text += f"   {text_preview}\n"
            peaks_text += f"   - {message.sender_id} at {message.timestamp.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        self.peaks_text.setPlainText(peaks_text)
    
    def get_sentiment_data(self) -> Optional[Any]:
        """Get the current sentiment analysis data"""
        return self.current_sentiment
    
    def has_sentiment_data(self) -> bool:
        """Check if sentiment analysis data is available"""
        return self.current_sentiment is not None