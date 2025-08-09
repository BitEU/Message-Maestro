#!/usr/bin/env python3
"""
Statistics Exporter

Handles exporting statistics data to various formats including PDF and JSON.
Uses the existing ReportLab integration for consistent PDF generation.
"""

import json
import os
from typing import Dict, List, Any
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.colors import Color, black, blue, gray
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .stats_calculator import MessageStats


class StatsExporter:
    """Exports message statistics to various formats"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for PDF export"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=black,
            alignment=TA_CENTER
        )
        
        # Heading style
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=black
        )
        
        # Subheading style
        self.subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=black
        )
        
        # Normal text style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            textColor=black
        )
        
        # Table text style
        self.table_style = ParagraphStyle(
            'TableText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=black
        )
    
    def export_to_pdf(self, stats: MessageStats, file_path: str) -> None:
        """
        Export statistics to a PDF report
        
        Args:
            stats: MessageStats object containing calculated statistics
            file_path: Path where the PDF should be saved
        """
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build the story (content)
        story = []
        
        # Title page
        story.extend(self._create_title_page(stats))
        story.append(PageBreak())
        
        # Overview section
        story.extend(self._create_overview_section(stats))
        
        # Temporal patterns section
        story.extend(self._create_temporal_section(stats))
        
        # User analytics section
        story.extend(self._create_users_section(stats))
        
        # Response analysis section
        story.extend(self._create_response_section(stats))
        
        # Sentiment analysis section (if available)
        if stats.sentiment_enabled and stats.sentiment_data:
            story.extend(self._create_sentiment_section(stats))
        
        # Build PDF
        doc.build(story)
    
    def _create_title_page(self, stats: MessageStats) -> List[Any]:
        """Create the title page content"""
        content = []
        
        # Main title
        content.append(Paragraph("Message Statistics Report", self.title_style))
        content.append(Spacer(1, 0.5 * inch))
        
        # Summary stats
        if stats.date_range[0] and stats.date_range[1]:
            date_range = f"{stats.date_range[0].strftime('%B %d, %Y')} - {stats.date_range[1].strftime('%B %d, %Y')}"
        else:
            date_range = "Unknown"
        
        summary_data = [
            ["Total Messages:", f"{stats.total_messages:,}"],
            ["Conversations:", f"{stats.conversation_count:,}"],
            ["Date Range:", date_range],
            ["Average Message Length:", f"{stats.overall_average_length:.0f} characters"],
            ["Most Active User:", stats.most_prolific_sender or "Unknown"],
            ["Report Generated:", datetime.now().strftime("%B %d, %Y at %I:%M %p")]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 3 * inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [Color(0.95, 0.95, 0.95), Color(1, 1, 1)]),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(summary_table)
        
        return content
    
    def _create_overview_section(self, stats: MessageStats) -> List[Any]:
        """Create the overview section"""
        content = []
        
        content.append(Paragraph("Overview", self.heading_style))
        
        # Key metrics
        content.append(Paragraph("Key Metrics", self.subheading_style))
        
        overview_text = f"""
        This report analyzes {stats.total_messages:,} messages across {stats.conversation_count:,} conversations. 
        The average message length is {stats.overall_average_length:.0f} characters.
        """
        
        if stats.date_range[0] and stats.date_range[1]:
            duration = stats.date_range[1] - stats.date_range[0]
            messages_per_day = stats.total_messages / max(duration.days, 1)
            overview_text += f"""
            The conversations span {duration.days} days, with an average of {messages_per_day:.1f} messages per day.
            """
        
        content.append(Paragraph(overview_text, self.normal_style))
        
        # Top senders table
        content.append(Paragraph("Top Message Senders", self.subheading_style))
        
        sender_data = [["Rank", "Sender", "Messages", "Percentage"]]
        total_messages = stats.total_messages
        
        for i, (sender, count) in enumerate(sorted(stats.messages_per_sender.items(), 
                                                  key=lambda x: x[1], reverse=True)[:10], 1):
            percentage = (count / total_messages) * 100 if total_messages > 0 else 0
            sender_data.append([
                str(i),
                sender,
                f"{count:,}",
                f"{percentage:.1f}%"
            ])
        
        sender_table = Table(sender_data, colWidths=[0.5 * inch, 2.5 * inch, 1 * inch, 1 * inch])
        sender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), Color(0.95, 0.95, 0.95)),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))
        
        content.append(sender_table)
        content.append(Spacer(1, 0.2 * inch))
        
        return content
    
    def _create_temporal_section(self, stats: MessageStats) -> List[Any]:
        """Create the temporal patterns section"""
        content = []
        
        content.append(Paragraph("Temporal Patterns", self.heading_style))
        
        # Most active times
        hour_names = ["12AM", "1AM", "2AM", "3AM", "4AM", "5AM", "6AM", "7AM", "8AM", "9AM", "10AM", "11AM",
                     "12PM", "1PM", "2PM", "3PM", "4PM", "5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM"]
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        temporal_text = f"""
        Most active hour: {hour_names[stats.most_active_hour]} with {stats.messages_by_hour.get(stats.most_active_hour, 0):,} messages
        <br/>
        Most active day: {day_names[stats.most_active_day]} with {stats.messages_by_day_of_week.get(stats.most_active_day, 0):,} messages
        """
        
        content.append(Paragraph(temporal_text, self.normal_style))
        
        # Hourly distribution table
        content.append(Paragraph("Hourly Distribution", self.subheading_style))
        
        hourly_data = [["Time Period", "Messages", "Percentage"]]
        total_messages = stats.total_messages
        
        # Group hours into periods for readability
        periods = [
            ("Late Night (12AM-6AM)", list(range(0, 6))),
            ("Morning (6AM-12PM)", list(range(6, 12))),
            ("Afternoon (12PM-6PM)", list(range(12, 18))),
            ("Evening (6PM-12AM)", list(range(18, 24)))
        ]
        
        for period_name, hours in periods:
            period_count = sum(stats.messages_by_hour.get(hour, 0) for hour in hours)
            percentage = (period_count / total_messages) * 100 if total_messages > 0 else 0
            hourly_data.append([period_name, f"{period_count:,}", f"{percentage:.1f}%"])
        
        hourly_table = Table(hourly_data, colWidths=[2 * inch, 1 * inch, 1 * inch])
        hourly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), Color(0.95, 0.95, 0.95)),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))
        
        content.append(hourly_table)
        content.append(Spacer(1, 0.2 * inch))
        
        # Weekly distribution
        content.append(Paragraph("Weekly Distribution", self.subheading_style))
        
        weekly_data = [["Day", "Messages", "Percentage"]]
        for day, name in enumerate(day_names):
            count = stats.messages_by_day_of_week.get(day, 0)
            percentage = (count / total_messages) * 100 if total_messages > 0 else 0
            weekly_data.append([name, f"{count:,}", f"{percentage:.1f}%"])
        
        weekly_table = Table(weekly_data, colWidths=[1.5 * inch, 1 * inch, 1 * inch])
        weekly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), Color(0.95, 0.95, 0.95)),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))
        
        content.append(weekly_table)
        content.append(Spacer(1, 0.2 * inch))
        
        return content
    
    def _create_users_section(self, stats: MessageStats) -> List[Any]:
        """Create the user analytics section"""
        content = []
        
        content.append(Paragraph("User Analytics", self.heading_style))
        
        # Message length analysis
        content.append(Paragraph("Average Message Length by User", self.subheading_style))
        
        length_data = [["User", "Average Length", "Relative to Overall"]]
        overall_avg = stats.overall_average_length
        
        for sender, avg_length in sorted(stats.average_message_length.items(), 
                                       key=lambda x: x[1], reverse=True)[:10]:
            relative = (avg_length / overall_avg) * 100 if overall_avg > 0 else 0
            length_data.append([
                sender,
                f"{avg_length:.0f} chars",
                f"{relative:.0f}%"
            ])
        
        length_table = Table(length_data, colWidths=[2.5 * inch, 1.25 * inch, 1.25 * inch])
        length_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), Color(0.95, 0.95, 0.95)),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))
        
        content.append(length_table)
        content.append(Spacer(1, 0.2 * inch))
        
        return content
    
    def _create_response_section(self, stats: MessageStats) -> List[Any]:
        """Create the response analysis section"""
        content = []
        
        content.append(Paragraph("Response Analysis", self.heading_style))
        
        if not stats.response_times:
            content.append(Paragraph("No response time data available.", self.normal_style))
            return content
        
        # Response time summary
        content.append(Paragraph("Average Response Times", self.subheading_style))
        
        response_data = [["User", "Avg Response Time", "Total Responses", "Fastest", "Slowest"]]
        
        for sender in sorted(stats.response_times.keys()):
            times = stats.response_times[sender]
            if not times:
                continue
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            response_data.append([
                sender,
                self._format_time(avg_time),
                str(len(times)),
                self._format_time(min_time),
                self._format_time(max_time)
            ])
        
        response_table = Table(response_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        response_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), Color(0.95, 0.95, 0.95)),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))
        
        content.append(response_table)
        content.append(Spacer(1, 0.2 * inch))
        
        # Fastest responder info
        if stats.fastest_responder:
            fastest_time = stats.average_response_times.get(stats.fastest_responder, 0)
            fastest_text = f"""
            <b>Fastest Responder:</b> {stats.fastest_responder}<br/>
            <b>Average Response Time:</b> {self._format_time(fastest_time)}
            """
            content.append(Paragraph(fastest_text, self.normal_style))
        
        return content
    
    def _format_time(self, minutes: float) -> str:
        """Format time duration for display"""
        if minutes < 1:
            return f"{minutes*60:.0f}s"
        elif minutes < 60:
            return f"{minutes:.1f}m"
        elif minutes < 1440:
            return f"{minutes/60:.1f}h"
        else:
            return f"{minutes/1440:.1f}d"
    
    def export_to_json(self, stats: MessageStats, file_path: str) -> None:
        """
        Export statistics to JSON format
        
        Args:
            stats: MessageStats object containing calculated statistics
            file_path: Path where the JSON should be saved
        """
        # Convert stats to serializable dictionary
        stats_dict = {
            'export_timestamp': datetime.now().isoformat(),
            'total_messages': stats.total_messages,
            'conversation_count': stats.conversation_count,
            'messages_per_sender': stats.messages_per_sender,
            'messages_by_hour': stats.messages_by_hour,
            'messages_by_day_of_week': stats.messages_by_day_of_week,
            'average_message_length': stats.average_message_length,
            'overall_average_length': stats.overall_average_length,
            'average_response_times': stats.average_response_times,
            'most_active_hour': stats.most_active_hour,
            'most_active_day': stats.most_active_day,
            'most_prolific_sender': stats.most_prolific_sender,
            'fastest_responder': stats.fastest_responder,
            'date_range': {
                'start': stats.date_range[0].isoformat() if stats.date_range[0] else None,
                'end': stats.date_range[1].isoformat() if stats.date_range[1] else None
            }
        }
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stats_dict, f, indent=2, ensure_ascii=False)
    
    def _create_sentiment_section(self, stats: MessageStats) -> List[Any]:
        """Create the sentiment analysis section"""
        content = []
        
        sentiment = stats.sentiment_data
        if not sentiment:
            return content
        
        content.append(Paragraph("Sentiment Analysis", self.heading_style))
        
        # Overall sentiment summary
        content.append(Paragraph("Overall Sentiment", self.subheading_style))
        
        overall_score = sentiment.overall_sentiment
        sentiment_label = self._get_sentiment_label(overall_score.compound)
        confidence_pct = overall_score.confidence * 100
        
        sentiment_text = f"""
        The overall sentiment of this conversation is <b>{sentiment_label}</b> with a sentiment score of 
        {overall_score.compound:.3f} (confidence: {confidence_pct:.1f}%).
        
        Sentiment breakdown:
        • Positive: {overall_score.positive:.1%}
        • Negative: {overall_score.negative:.1%}
        • Neutral: {overall_score.neutral:.1%}
        
        Analysis method: {overall_score.method}
        """
        
        content.append(Paragraph(sentiment_text, self.normal_style))
        
        # Sentiment by sender
        if sentiment.sentiment_by_sender:
            content.append(Paragraph("Sentiment by Sender", self.subheading_style))
            
            sender_data = [["Sender", "Sentiment", "Score", "Positive", "Negative", "Neutral"]]
            
            for sender, sender_sentiment in sentiment.sentiment_by_sender.items():
                sender_label = self._get_sentiment_label(sender_sentiment.compound)
                sender_data.append([
                    sender,
                    sender_label,
                    f"{sender_sentiment.compound:.3f}",
                    f"{sender_sentiment.positive:.1%}",
                    f"{sender_sentiment.negative:.1%}",
                    f"{sender_sentiment.neutral:.1%}"
                ])
            
            sender_table = Table(sender_data, colWidths=[1.5*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            sender_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), Color(0.98, 0.98, 0.98)),
                ('GRID', (0, 0), (-1, -1), 1, black),
            ]))
            
            content.append(sender_table)
            content.append(Spacer(1, 0.2 * inch))
        
        # Top keywords
        if sentiment.keywords:
            content.append(Paragraph("Key Topics", self.subheading_style))
            
            keyword_text = "Most frequently mentioned topics: "
            top_keywords = sentiment.keywords[:10]  # Top 10 keywords
            keyword_list = [f"{word} ({count})" for word, count in top_keywords]
            keyword_text += ", ".join(keyword_list)
            
            content.append(Paragraph(keyword_text, self.normal_style))
            content.append(Spacer(1, 0.1 * inch))
        
        # Emotional peaks
        if sentiment.emotional_peaks:
            content.append(Paragraph("Most Emotional Messages", self.subheading_style))
            
            peaks_text = "The following messages had the strongest emotional content:\n\n"
            
            for i, (message, peak_sentiment) in enumerate(sentiment.emotional_peaks[:5], 1):
                emotion_type = "Positive" if peak_sentiment.compound > 0 else "Negative"
                text_preview = message.text[:150] + "..." if len(message.text) > 150 else message.text
                
                peaks_text += f"<b>{i}. [{emotion_type} - Score: {peak_sentiment.compound:.3f}]</b><br/>"
                peaks_text += f"{text_preview}<br/>"
                peaks_text += f"<i>- {message.sender_id} at {message.timestamp.strftime('%Y-%m-%d %H:%M')}</i><br/><br/>"
            
            content.append(Paragraph(peaks_text, self.normal_style))
        
        # Summary insights
        if sentiment.summary:
            content.append(Paragraph("Analysis Summary", self.subheading_style))
            content.append(Paragraph(sentiment.summary, self.normal_style))
        
        return content
    
    def _get_sentiment_label(self, compound_score: float) -> str:
        """Convert compound sentiment score to human-readable label"""
        if compound_score >= 0.5:
            return "Very Positive"
        elif compound_score >= 0.1:
            return "Positive"
        elif compound_score >= -0.1:
            return "Neutral"
        elif compound_score >= -0.5:
            return "Negative"
        else:
            return "Very Negative"
