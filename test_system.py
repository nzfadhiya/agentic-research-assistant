import requests
import time

API_URL = "https://agentic-research-assistant-zwwf.onrender.com"
results = []

def check(name, condition, extra=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}  {extra}")
    results.append(condition)

# 1. Health check
r = requests.get(API_URL + "/")
check("Health check", r.status_code == 200, r.json())

# 2. Register a fresh test user
test_user = "testuser_" + str(int(time.time()))
r = requests.post(API_URL + "/auth/register", json={
    "username": test_user, "email": test_user + "@test.com", "password": "test123"
})
check("Register", r.status_code == 200, r.json())

# 3. Login
r = requests.post(API_URL + "/auth/login", json={"username": test_user, "password": "test123"})
check("Login", r.status_code == 200)
token = r.json().get("token")
headers = {"Authorization": "Bearer " + token}

session_id = "test-session-" + str(int(time.time()))

# 4. Chat - casual
r = requests.post(API_URL + "/chat", json={"session_id": session_id, "message": "hi"},
    headers=headers, timeout=60)
check("Chat - casual", r.status_code == 200, r.json().get("mode_used"))

# 5. Chat - simple
r = requests.post(API_URL + "/chat", json={"session_id": session_id, "message": "what is photosynthesis"},
    headers=headers, timeout=60)
data = r.json()
check("Chat - simple", r.status_code == 200 and "Sources" in data.get("response", ""), data.get("mode_used"))

# 6. Chat - research
r = requests.post(API_URL + "/chat",
    json={"session_id": session_id, "message": "comprehensive report on AI in healthcare 2026"},
    headers=headers, timeout=120)
data = r.json()
check("Chat - research", r.status_code == 200 and "Executive Summary" in data.get("response", ""), data.get("mode_used"))

# 7. Chat history
r = requests.get(API_URL + f"/chat/{session_id}/history", headers=headers)
check("Chat history", r.status_code == 200 and len(r.json().get("messages", [])) >= 6)

# 8. Sessions list
r = requests.get(API_URL + "/sessions", headers=headers)
check("Sessions list", r.status_code == 200 and len(r.json().get("sessions", [])) > 0)

# 9. Cache stats (should have 1 entry from the research call above)
r = requests.get(API_URL + "/cache/stats", headers=headers)
data = r.json()
check("Cache stats has entry", r.status_code == 200 and data.get("total_entries", 0) > 0, data)

# 10. Cache clear
r = requests.delete(API_URL + "/cache", headers=headers)
check("Cache clear", r.status_code == 200)

# 11. Cache stats after clear (should be 0)
r = requests.get(API_URL + "/cache/stats", headers=headers)
data = r.json()
check("Cache stats after clear", data.get("total_entries", 0) == 0, data)

# 12. Dual mode
r = requests.post(API_URL + "/dual", json={"question": "what is blockchain"}, headers=headers, timeout=120)
data = r.json()
check("Dual mode", r.status_code == 200 and "agent_a" in data and "agent_b" in data)

# 13. Export chat
r = requests.post(API_URL + f"/export/{session_id}", headers=headers, timeout=30)
check("Export chat", r.status_code == 200)

# 14. Generate doc
r = requests.post(API_URL + "/generate-doc",
    json={"topic": "Solar Energy", "format": "pdf", "session_id": session_id},
    headers=headers, timeout=120)
check("Generate doc", r.status_code == 200)

# 15. Delete chat session
r = requests.delete(API_URL + f"/chat/{session_id}", headers=headers)
check("Delete session", r.status_code == 200)

print()
print(f"Passed {sum(results)}/{len(results)}")

print("\n===== MCP TESTS =====")

# MCP Root
r = requests.get(API_URL + "/mcp/")
print("MCP Root:", r.status_code)
print(r.text[:500])

# MCP Web Search
r = requests.post(
    API_URL + "/mcp/tools/web_search",
    json={
        "query": "what is artificial intelligence",
        "max_results": 2
    },
    timeout=60
)

print("\nMCP Web Search:", r.status_code)
print(r.text[:1000])

# MCP Wikipedia
r = requests.post(
    API_URL + "/mcp/tools/wikipedia_fetch",
    json={
        "topic": "Artificial Intelligence",
        "sentences": 2
    },
    timeout=60
)

print("\nMCP Wikipedia:", r.status_code)
print(r.text[:1000])

# MCP Save Memory
r = requests.post(
    API_URL + "/mcp/tools/save_memory",
    json={
        "query": "test query",
        "summary": "test summary"
    },
    timeout=60
)

print("\nMCP Save Memory:", r.status_code)
print(r.text[:1000])

# Multi Agent Research Test
try:
    r = requests.post(
        API_URL + "/research",
        json={
            "query": "how cotton is made",
            "mode": "multi"
        },
        headers=headers,
        timeout=180
    )

    print("\nMULTI MODE STATUS:", r.status_code)
    print("MULTI MODE RESPONSE:")
    print(r.text[:2000])

except Exception as e:
    print("\nMULTI MODE ERROR:")
    print(e)
