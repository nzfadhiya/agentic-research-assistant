import re

files = [
    "app/main.py",
    "app/agents/chat_agent.py",
    "app/agents/dual_agent.py",
    "app/agents/multi_agent_graph.py",
]

NEW_LINE = ("MCP_URL = os.getenv(\"MCP_URL\", "
             "\"http://127.0.0.1:\" + os.environ.get(\"PORT\", \"8000\") + \"/mcp\")\n")

PATTERN = re.compile(
    r'MCP_URL\s*=\s*(?:os\.getenv\([^)]*\)|"[^"]*"|\x27[^\x27]*\x27)\s*\n?'
)

for f in files:
    with open(f, "r", encoding="utf-8") as fh:
        content = fh.read()

    new_content, n = PATTERN.subn(NEW_LINE, content, count=1)

    if n == 0:
        print(f"WARNING: no MCP_URL assignment found in {f} -- check manually")
        continue

    if "import os" not in new_content:
        new_content = "import os\n" + new_content

    with open(f, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    print(f"Fixed MCP_URL in {f}")
