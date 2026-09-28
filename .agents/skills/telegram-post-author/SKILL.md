---
name: telegram-post-author
description: >-
  Provides guidelines, visual hierarchy, formatting best practices, and rendering rules
  for authoring Telegram posts, channel announcements, digests, and bot messages.
  Use when writing content intended for Telegram, formatting bot responses, or creating channel publications.
---

# Telegram Post Authoring & Formatting Skill

This skill guides the preparation and formatting of text for Telegram bots, channels, and group chats. Telegram renders text differently from browsers and IDEs; adherence to these rules ensures messages look professional, readable, and clean on mobile screens.

---

## 1. Core Telegram Formatting Rules

### A. Headers and Visual Hierarchy
- **NEVER** use Markdown heading tags (`#`, `##`, `###`) directly as Telegram does not render them as headings.
- Use bold text preceded by relevant emoji for sections:
  - `🚀 **Заголовок раздела**`
  - `📦 **Созданные компоненты:**`
  - `⚠️ **Важные замечания:**`

### B. File Paths and Links
- **NEVER** output unopenable local file URIs like `[filename](file:///path/to/file)`. Mobile Telegram clients cannot open local file URLs.
- Always format file names and paths as inline code:
  - ✅ `src/app/main.py`
  - ❌ `[src/app/main.py](file:///opt/project/src/app/main.py)`
- For external web links, use standard markdown: `[Google](https://google.com)`.

### C. Code Blocks & Identifiers
- Format all identifiers, commands, variables, and package names in inline code: `` `FastAPI` ``, `` `pytest` ``.
- Format code blocks with language identifiers:
  ```python
  def example():
      return True
  ```

### D. Lists, Bullets & Spacing
- **NEVER** use heavy black checkmarks (`✔️`). They render as bulky dark glyphs on mobile screens.
- Use neat, elegant bullet characters: clean round bullets `•` (recommended), `🔹` for emphasis, or standard numbered lists `1.`, `2.`.
- **NEVER** use horizontal rules (`---`, `***`, `___`) or strings of dashes (`--------`). Telegram renders them as ugly visual clutter. Separate logical sections purely with clean empty lines (`\n\n`).

---

## 2. Telegram Length & Chunking Limits
- Maximum single message: **4096 UTF-16 code units**.
- If output exceeds 3500 characters, break it into logical parts or attach the full report as a `.md` document.

---

## 3. Libraries for Telegram Message Conversion
When implementing Python bots or bridges:
- **`telegramify-markdown`**: Converts standard GitHub Flavored Markdown into Telegram `MarkdownV2` or Telegram `MessageEntity` objects with automatic character escaping and message chunking (`split_markdownv2`).
- **`chatgpt-md-converter`**: Alternative converter for Telegram HTML mode.
