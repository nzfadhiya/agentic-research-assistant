import os
import re
import sys
from datetime import datetime
sys.path.insert(0, '.')
from app.config import OUTPUTS_DIR

os.makedirs(OUTPUTS_DIR, exist_ok=True)


def clean_text(text: str) -> str:
    """
    Removes markdown symbols and cleans text for export.
    Keeps the actual content, removes formatting characters.
    """
    # Remove bold/italic markers
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)

    # Remove headers markers but keep text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove code block markers
    text = re.sub(r'```[\w]*\n?', '', text)
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Remove blockquote markers
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Clean bullet points — keep as readable dashes
    text = re.sub(r'^[\*\-\+]\s+', '- ', text, flags=re.MULTILINE)

    # Remove link markdown but keep text and URL readable
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', text)

    # Remove image markdown
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'[\1]', text)

    # Remove [Agent A] and [Agent B] labels
    text = re.sub(r'\[Agent [AB]\]\s*', '', text)

    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)

    # Clean multiple blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def export_chat_to_pdf(messages: list, session_id: str) -> str:
    """
    Converts conversation messages to a clean HTML report.
    All markdown symbols removed — plain readable text only.
    Returns the file path of the saved HTML file.
    """
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_{session_id[:8]}_{timestamp}.html"
    filepath = os.path.join(OUTPUTS_DIR, filename)

    html_parts = ["""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Research Report</title>
<style>
  body {
    font-family: Arial, sans-serif;
    max-width: 900px;
    margin: 40px auto;
    padding: 20px;
    color: #1a1a1a;
    line-height: 1.7;
  }
  h1 { color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 10px; }
  .meta { color: #666; font-size: 13px; margin-bottom: 30px; }
  .message { margin-bottom: 24px; padding: 16px 20px; border-radius: 8px; }
  .user { background: #f0f4ff; border-left: 4px solid #4361ee; }
  .assistant { background: #f0fff4; border-left: 4px solid #2d6a4f; }
  .role {
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    color: #444;
  }
  .content {
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  .footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #ddd;
    color: #999;
    font-size: 12px;
    text-align: center;
  }
</style>
</head>
<body>
"""]

    html_parts.append("<h1>Research Report</h1>")
    html_parts.append(
        "<div class='meta'>Generated: " +
        datetime.now().strftime('%B %d, %Y at %H:%M') +
        " | Session: " + session_id[:8] +
        " | Agentic Research Assistant</div>"
    )

    for msg in messages:
        role = msg.get("role", "user")
        raw_content = msg.get("content", "")

        # Clean all markdown and symbols
        clean_content = clean_text(raw_content)

        # Escape HTML special chars
        clean_content = (clean_content
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        role_label = "You" if role == "user" else "Assistant"

        html_parts.append(
            "<div class='message " + role + "'>"
            "<div class='role'>" + role_label + "</div>"
            "<div class='content'>" + clean_content + "</div>"
            "</div>"
        )

    html_parts.append(
        "<div class='footer'>Agentic Research Assistant — LangGraph + Groq + MCP</div>"
        "</body></html>"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"[pdf_export] Clean report saved: {filepath}")
    return filepath