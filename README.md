# Message Maestro

Message Maestro is a modern, GPU-accelerated desktop application for viewing, tagging, and exporting conversations from various messaging platforms. It features a beautiful, responsive UI built with PyQt6, advanced message parsing, customizable tagging, and high-quality PDF export. The application is designed for both casual users and professionals who need to analyze, archive, or present chat data.

## Features

- **Multi-Platform Support:**
  - Import and view conversations from Kik Messenger, Snapchat, and Twitter DMs (with extensible parser support).
- **Modern UI:**
  - GPU-accelerated scrolling and animated widgets for a smooth, visually appealing experience.
- **Tagging System:**
  - Tag messages with custom labels and colors for organization, review, or analysis.
- **PDF Export:**
  - Export entire conversations to beautifully formatted PDFs, including tag legends and color-coded message bubbles.
- **Media & Link Detection:**
  - Messages with media or links are automatically highlighted.
- **Keyboard Shortcuts:**
  - Efficient navigation and tagging with keyboard shortcuts (see TODO for planned enhancements).
- **Extensible Architecture:**
  - Easily add new message parsers for other platforms by implementing the `BaseParser` interface.

## Installation

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd Message-Maestro
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

## Usage

Run the application:

```sh
python message_viewer.py
```

- Use the file dialog to open exported message files from supported platforms.
- Tag messages, search, and export conversations as PDF.

## Supported Platforms

- **Kik Messenger** (`.csv`)
- **Snapchat** (`.csv`)
- **Twitter DM** (`.txt`)

## Search Bars Explained

Message Maestro features two powerful and distinct search bars to help you quickly find conversations and messages:

### 1. Global Conversation Search (Sidebar Search Bar)

- **Location:** At the top of the left sidebar, always visible.
- **Purpose:** Search across all loaded conversations for keywords in conversation titles, participant names, or message content.
- **How it works:**
  - Type a keyword or phrase and press Enter (or click the search icon).
  - Results instantly filter the conversation list below, showing only conversations that match your search.
  - You can refine your search using radio buttons:
    - **All:** Search both conversation titles and message content.
    - **Titles:** Only search conversation titles and participant names.
    - **Content:** Only search within the text of messages.
  - Click the clear (✕) button to reset the search and show all conversations again.
- **Use case:** Quickly locate a conversation by a participant's name, group title, or a word/phrase mentioned anywhere in the chat history.

### 2. In-Conversation Search (Header Search Bar)

- **Location:** At the top of the main chat view, appears after you open a conversation and click the '🔍 Search' button in the header.
- **Purpose:** Search for specific words or phrases within the currently open conversation.
- **How it works:**
  - Type your search term and press Enter.
  - All matching messages are highlighted in the chat view.
  - Use the **Next ↓** and **↑ Prev** buttons to jump between matches.
  - The search bar displays the number of matches and your current position (e.g., "3 of 7").
  - Click the close (✕) button to exit in-conversation search and clear highlights.
- **Use case:** Find every instance of a word, phrase, or name within a single conversation, and quickly navigate between them for review or tagging.

**Tip:** The two search bars are independent; use the sidebar search to find the right conversation, then use the in-conversation search to drill down to the exact messages you need.

## Directory Structure

- `message_viewer.py` — Main application (PyQt6 GUI)
- `parsers/` — Platform-specific message parsers
- `templates/` — Example export templates and sample data
- `requirements.txt` — Python dependencies

## Dependencies

- PyQt6
- reportlab
- weasyprint

Install with `pip install -r requirements.txt`.

## Roadmap / TODO

See `todo.txt` for planned features, including:
- Enhanced keyboard shortcuts
- Project save/load and autosave
- Local sentiment analysis and summary
- HTML export
- Message statistics dashboard

## Contributing

Contributions are welcome! To add support for a new platform, implement a new parser in `parsers/` by subclassing `BaseParser`.

## License

[MIT License](LICENSE)