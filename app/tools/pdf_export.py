import os
import sys
sys.path.insert(0, '.')
from app.config import OUTPUTS_DIR

def export_chat_to_pdf(history: list, session_id: str) -> str:
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUTS_DIR, f"report_{session_id[:8]}.html")
    lines = ["<html><body style='font-family:sans-serif;max-width:800px;margin:40px auto'>"]
    lines.append("<h1>Research Report</h1>")
    lines.append(f"<p style='color:#888'>Session: {session_id[:8]}</p><hr>")
    for msg in history:
        role = msg['role']
        content = msg['content'].replace('\n', '<br>')
        if role == 'user':
            lines.append(f"<div style='background:#f0f0f0;padding:12px;border-radius:6px;margin:10px 0'><b>You:</b><br>{content}</div>")
        else:
            lines.append(f"<div style='background:#e8f4fd;padding:12px;border-radius:6px;margin:10px 0'><b>Assistant:</b><br>{content}</div>")
    lines.append("</body></html>")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return filepath