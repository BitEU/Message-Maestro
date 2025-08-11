@echo off
echo Building Message-Maestro with optional Sentiment Analysis Support...
echo.

python -m PyInstaller --onefile --windowed ^
--hidden-import="weasyprint" ^
--hidden-import="reportlab" ^
--hidden-import="parsers.base_parser" ^
--hidden-import="parsers.kik_messenger_parser" ^
--hidden-import="parsers.parser_manager" ^
--hidden-import="parsers.twitter_dm_parser" ^
--hidden-import="parsers.snapchat_parser" ^
--hidden-import="message_stats.stats_calculator" ^
--hidden-import="message_stats.stats_dashboard" ^
--hidden-import="message_stats.stats_exporter" ^
--hidden-import="message_stats.chart_widgets" ^
--hidden-import="message_stats.sentiment_analyzer" ^
--hidden-import="message_stats.sentiment_dashboard_tab" ^
--hidden-import="nltk" ^
--hidden-import="nltk.sentiment" ^
--hidden-import="nltk.sentiment.vader" ^
--hidden-import="nltk.tokenize" ^
--hidden-import="nltk.corpus" ^
--hidden-import="nltk.probability" ^
--hidden-import="textblob" ^
--hidden-import="numpy" ^
--exclude-module="transformers" ^
--exclude-module="torch" ^
--exclude-module="torchvision" ^
--exclude-module="torchaudio" ^
--exclude-module="sentencepiece" ^
--exclude-module="sklearn" ^
--exclude-module="scipy" ^
--add-data "parsers;parsers" ^
--add-data "message_stats;message_stats" ^
--add-data "templates;templates" ^
--collect-data nltk ^
--collect-data textblob ^
message_viewer.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
) else (
    echo Build completed successfully!
    echo.
    pause
)