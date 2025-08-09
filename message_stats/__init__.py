#!/usr/bin/env python3
"""
Message Statistics Dashboard Module

This module provides comprehensive statistics analysis and visualization
for message data parsed by the Message-Maestro application.
"""

# Import main components
try:
    from .stats_calculator import StatisticsCalculator
    from .stats_dashboard import StatsDashboard
    from .chart_widgets import ChartWidget, BarChart, PieChart, LineChart
    from .stats_exporter import StatsExporter
except ImportError:
    # Graceful degradation if some modules aren't available
    StatisticsCalculator = None
    StatsDashboard = None
    ChartWidget = None
    BarChart = None
    PieChart = None
    LineChart = None
    StatsExporter = None

__all__ = [
    'StatisticsCalculator',
    'StatsDashboard', 
    'ChartWidget',
    'BarChart',
    'PieChart',
    'LineChart',
    'StatsExporter'
]

__version__ = '1.0.0'
