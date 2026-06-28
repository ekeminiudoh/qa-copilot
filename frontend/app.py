"""QA Copilot — Production Streamlit Web Application."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import streamlit as st

# ─── Configuration ────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
LOGO = "🤖"

st.set_page_config(
    page_title="QA Copilot",
    page_icon=LOGO,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "QA Copilot v1.0 — AI-Powered QA Assistant"},
)

# ─── Styles ───────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { background: #0f172a; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%; background: #1e293b; color: #e2e8f0 !important;
        border: 1px solid #334155; border-radius: 0.5rem; padding: 0.5rem 1rem;
        text-align: left; margin-bottom: 0.25rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover { background: #334155; }
    .chat-user { background: #1e3a5f; border-radius: 0.75rem; padding: 0.75rem;
                 margin: 0.5rem 0; border-left: 3px solid #3b82f6; }
    .chat-assistant { background: #1e293b; border-radius: 0.75rem; padding: 0.75rem;
                      margin: 0.5rem 0; border-left: 3px solid #22c55e; }
    </style>
    """, unsafe_allow_html=True)


inject_css()

# ─── Session State ────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "token": None,
        "user": None,
        "page": "Dashboard",
        "chat_history": [],
        "execution_results": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─── API Helpers ──────────────────────────────────────────────────────────────

def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if st.session_state.token:
        h["Authorization"] = f"Bearer {st.session_state.token}"
    return h


def api_get(path: str, params: dict = None) -> Optional[Dict]:
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_headers(), params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        st.error(f"API error {r.status_code}: {r.text[:200]}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is it running on port 8000?")
    except Exception as exc:
        st.error(f"Request error: {exc}")
    return None


def api_post(path: str, data: dict = None, files=None) -> Optional[Dict]:
    try:
        if files:
            headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
            r = requests.post(f"{API_BASE}{path}", headers=headers, files=files, timeout=60)
        else:
            r = requests.post(f"{API_BASE}{path}", headers=_headers(), json=data, timeout=60)
        if r.status_code in (200, 201):
            return r.json()
        st.error(f"API error {r.status_code}: {r.text[:300]}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is it running on port 8000?")
    except Exception as exc:
        st.error(f"Request error: {exc}")
    return None


# ─── Authentication ───────────────────────────────────────────────────────────

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align:center;font-size:3rem'>{LOGO}</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center'>QA Copilot</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#94a3b8'>AI-Powered QA Assistant</p>", unsafe_allow_html=True)
        st.divider()

        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", value="admin")
                password = st.text_input("Password", type="password", value="admin")
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

            if submitted:
                result = api_post("/auth/login", {"username": username, "password": password})
                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result.get("user", {})
                    st.success("Logged in!")
                    time.sleep(0.5)
                    st.rerun()

        with tab_register:
            with st.form("register_form"):
                new_username = st.text_input("Username", key="reg_user")
                new_email = st.text_input("Email", key="reg_email")
                new_password = st.text_input("Password", type="password", key="reg_pass")
                new_full_name = st.text_input("Full Name", key="reg_name")
                submitted_reg = st.form_submit_button("Register", use_container_width=True)

            if submitted_reg:
                result = api_post("/auth/register", {
                    "username": new_username,
                    "email": new_email,
                    "password": new_password,
                    "full_name": new_full_name,
                })
                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result.get("user", {})
                    st.success("Account created!")
                    time.sleep(0.5)
                    st.rerun()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown(f"## {LOGO} QA Copilot")
        user = st.session_state.get("user", {})
        roles = user.get("roles", [])
        st.markdown(f"**{user.get('full_name', user.get('username', 'User'))}**")
        st.caption(", ".join(roles) if roles else "viewer")
        st.divider()

        pages = {
            "Dashboard": "📊",
            "Chat": "💬",
            "Gaming Tests": "🎮",
            "Fintech Tests": "💳",
            "Train AI": "🧠",
            "Test Cases": "🧪",
            "SQL Review": "🗄️",
            "Security Review": "🔒",
            "Bug Investigation": "🐛",
            "Knowledge Base": "📚",
            "Documents": "📄",
            "Execution": "▶️",
            "Reports": "📈",
            "Settings": "⚙️",
        }
        if "admin" in roles:
            pages["User Management"] = "👥"

        for page, icon in pages.items():
            if st.button(f"{icon} {page}", key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()

        st.divider()
        if st.button("🚪 Logout"):
            for k in ["token", "user", "chat_history"]:
                st.session_state[k] = None if k != "chat_history" else []
            st.rerun()

        health = api_get("/health")
        if health:
            db_ok = health.get("database") == "ok"
            st.success(f"Backend: {health.get('status', 'unknown')}")
            if not db_ok:
                st.warning(f"DB: {health.get('database', 'unknown')}")
        else:
            st.error("Backend: offline")


# ─── Pages ────────────────────────────────────────────────────────────────────

def page_dashboard():
    st.title("📊 Dashboard")
    st.caption("QA Copilot overview and quick actions")

    c1, c2, c3, c4 = st.columns(4)
    health = api_get("/health") or {}
    knowledge = api_get("/api/knowledge/stats") or {}
    exec_summary = api_get("/api/reports/summary") or {}

    c1.metric("Documents Indexed", knowledge.get("indexed_documents", 0))
    c2.metric("Total Test Runs", exec_summary.get("total_runs", 0))
    avg = exec_summary.get("average_success_rate", 0)
    c3.metric("Avg Success Rate", f"{avg:.1f}%")
    status = "🟢 Online" if health.get("status") == "ok" else "🔴 Offline"
    c4.metric("Backend Status", status)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Quick Actions")
        if st.button("💬 Start New Chat", use_container_width=True):
            st.session_state.page = "Chat"
            st.rerun()
        if st.button("🧪 Generate Test Cases", use_container_width=True):
            st.session_state.page = "Test Cases"
            st.rerun()
        if st.button("📄 Upload Document", use_container_width=True):
            st.session_state.page = "Documents"
            st.rerun()
        if st.button("▶️ Run Tests", use_container_width=True):
            st.session_state.page = "Execution"
            st.rerun()

    with col_b:
        st.subheader("Available Agents")
        agents = [
            ("🔍 Analyst", "Requirements & risk analysis"),
            ("🧪 Tester", "Test case design"),
            ("💻 Developer", "API & code review"),
            ("⚙️ Automation", "Karate, Playwright, Cypress"),
            ("🗄️ SQL", "Query optimization"),
            ("📝 Documentation", "Docs & Swagger"),
            ("🐛 Bug Investigator", "Root cause analysis"),
            ("🔒 Security Reviewer", "OWASP & vulnerabilities"),
            ("📈 Performance Engineer", "Load & scalability"),
        ]
        for name, desc in agents:
            st.markdown(f"**{name}** — {desc}")


def page_chat():
    st.title("💬 AI Chat")

    col1, col2 = st.columns([3, 1])
    with col2:
        agent = st.selectbox("Agent", [
            "Auto-Route", "analyst", "tester", "developer", "automation",
            "sql", "documentation", "bug_investigator", "security_reviewer", "performance_engineer"
        ])
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        if st.button("🧠 Save Chat as Training"):
            if st.session_state.chat_history:
                label = f"chat-{len(st.session_state.chat_history)}-msgs"
                result = api_post("/api/knowledge/save-chat-training", {
                    "messages": st.session_state.chat_history,
                    "label": label,
                })
                if result:
                    st.success(result.get("message", "Chat saved for AI training!"))

    # Display history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">👤 **You:** {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            agent_name = msg.get("agent", "AI")
            conf = msg.get("confidence")
            conf_str = f" *(confidence: {conf:.0%})*" if conf else ""
            st.markdown(
                f'<div class="chat-assistant">🤖 **{agent_name.replace("_"," ").title()}{conf_str}:**\n\n{msg["content"]}</div>',
                unsafe_allow_html=True
            )

    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("Your message", placeholder="Ask anything about QA, testing, APIs...", height=80)
        context = st.text_input("Context (optional)", placeholder="Paste code, spec, or requirements...")
        sent = st.form_submit_button("Send ➤", use_container_width=True, type="primary")

    if sent and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        payload = {"query": user_input, "context": context or None}
        if agent != "Auto-Route":
            payload["agent"] = agent

        with st.spinner("Thinking..."):
            result = api_post("/api/query", payload)

        if result:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result.get("response", ""),
                "agent": result.get("agent", agent),
                "confidence": result.get("confidence"),
            })
        st.rerun()


def page_test_cases():
    st.title("🧪 Test Case Generation")

    tab1, tab2 = st.tabs(["Generate Test Cases", "Generate Automation"])

    with tab1:
        with st.form("tc_form"):
            requirement = st.text_area(
                "Requirement / User Story",
                placeholder="As a user, I want to login with email and password...",
                height=120
            )
            col1, col2 = st.columns(2)
            with col1:
                test_types = st.multiselect(
                    "Test Types",
                    ["positive", "negative", "boundary", "edge", "security", "performance"],
                    default=["positive", "negative", "boundary", "edge"]
                )
                include_automation = st.checkbox("Include automation snippets")
            with col2:
                framework = st.selectbox("Framework (optional)", [
                    "None", "karate", "playwright", "cypress", "selenium", "rest_assured"
                ])
            submitted = st.form_submit_button("Generate", type="primary", use_container_width=True)

        if submitted and requirement:
            with st.spinner("Generating test cases..."):
                result = api_post("/api/qa/test-cases/generate", {
                    "requirement": requirement,
                    "test_types": test_types,
                    "framework": None if framework == "None" else framework,
                    "include_automation": include_automation,
                })
            if result:
                c1, c2 = st.columns(2)
                c1.metric("Agent", result.get("agent", "tester").replace("_", " ").title())
                c2.metric("Confidence", f"{result.get('confidence', 0):.0%}")
                st.divider()
                st.markdown(result.get("test_cases", ""))
                st.download_button("💾 Download", data=result.get("test_cases", ""), file_name="test_cases.md")

    with tab2:
        with st.form("auto_form"):
            req = st.text_area("What to automate", placeholder="Login endpoint tests...", height=100)
            col1, col2 = st.columns(2)
            with col1:
                fw = st.selectbox("Framework", ["karate", "playwright", "cypress", "selenium", "rest_assured", "postman"])
                base_url = st.text_input("Base URL (optional)")
            with col2:
                endpoints = st.text_area("Endpoints (one per line)", height=80)
            submitted2 = st.form_submit_button("Generate Code", type="primary", use_container_width=True)

        if submitted2 and req:
            with st.spinner("Generating automation scripts..."):
                result = api_post("/api/qa/automation/generate", {
                    "requirement": req,
                    "framework": fw,
                    "base_url": base_url or None,
                    "endpoints": [e.strip() for e in endpoints.splitlines() if e.strip()] or None,
                })
            if result:
                st.metric("Confidence", f"{result.get('confidence', 0):.0%}")
                lang_map = {"karate": "gherkin", "playwright": "typescript", "cypress": "javascript", "selenium": "java", "rest_assured": "java", "postman": "json"}
                st.code(result.get("automation_code", ""), language=lang_map.get(fw, "text"))
                ext = "feature" if fw == "karate" else "ts" if fw == "playwright" else "json" if fw == "postman" else "java"
                st.download_button("💾 Download Script", data=result.get("automation_code", ""), file_name=f"test_{fw}.{ext}")


def page_sql_review():
    st.title("🗄️ SQL Review")

    with st.form("sql_form"):
        sql = st.text_area("SQL Query", height=200, placeholder="SELECT * FROM users WHERE id = ?")
        col1, _ = st.columns(2)
        dialect = col1.selectbox("Dialect", ["generic", "postgresql", "mysql", "oracle", "mssql"])
        submitted = st.form_submit_button("Review SQL", type="primary", use_container_width=True)

    if submitted and sql:
        with st.spinner("Analyzing SQL..."):
            result = api_post("/api/qa/sql/review", {"sql_query": sql, "dialect": dialect})
        if result:
            st.metric("Confidence", f"{result.get('confidence', 0):.0%}")
            st.divider()
            st.markdown(result.get("review", ""))


def page_security_review():
    st.title("🔒 Security Review")

    with st.form("sec_form"):
        code = st.text_area("Code to Review", height=250, placeholder="Paste code here...")
        col1, col2 = st.columns(2)
        language = col1.selectbox("Language", ["python", "java", "javascript", "typescript", "go", "php", "csharp"])
        focus = col2.multiselect("Focus Areas", ["owasp", "injection", "auth", "exposure", "xss", "csrf"], default=["owasp", "injection"])
        submitted = st.form_submit_button("Review Security", type="primary", use_container_width=True)

    if submitted and code:
        with st.spinner("Analyzing..."):
            result = api_post("/api/qa/security/review", {"code": code, "language": language, "focus": focus})
        if result:
            st.metric("Confidence", f"{result.get('confidence', 0):.0%}")
            st.markdown(result.get("review", ""))


def page_bug_investigation():
    st.title("🐛 Bug Investigation")

    with st.form("bug_form"):
        desc = st.text_area("Bug Description", height=100, placeholder="Describe the bug...")
        col1, col2 = st.columns(2)
        with col1:
            logs = st.text_area("Log Output", height=120)
            stack_trace = st.text_area("Stack Trace", height=120)
        with col2:
            sql_queries = st.text_area("SQL Queries", height=120)
            api_response = st.text_area("API Response", height=120)
        submitted = st.form_submit_button("Investigate", type="primary", use_container_width=True)

    if submitted and desc:
        with st.spinner("Investigating..."):
            result = api_post("/api/qa/bug/investigate", {
                "description": desc,
                "logs": logs or "",
                "stack_trace": stack_trace or "",
                "sql_queries": sql_queries or "",
                "api_response": api_response or "",
            })
        if result:
            st.metric("Confidence", f"{result.get('confidence', 0):.0%}")
            st.markdown(result.get("investigation", ""))


def page_knowledge_base():
    st.title("📚 Knowledge Base")

    query = st.text_input("Search", placeholder="JWT authentication best practices...")
    col1, col2 = st.columns([3, 1])
    with col2:
        top_k = st.number_input("Results", 1, 20, 5)

    if query and st.button("🔍 Search", type="primary"):
        r = requests.post(
            f"{API_BASE}/api/knowledge/search",
            headers=_headers(),
            params={"query": query, "top_k": top_k},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            st.info(f"Found {len(results)} results")
            for i, chunk in enumerate(results, 1):
                with st.expander(f"Result {i}"):
                    st.markdown(chunk)

    st.divider()
    stats = api_get("/api/knowledge/stats")
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Documents", stats.get("total_documents", 0))
        c2.metric("Indexed", stats.get("indexed_documents", 0))
        c3.metric("Chunks", stats.get("total_chunks", 0))
        c4.metric("Vector Store", "✅" if stats.get("kb_in_memory_chunks", 0) > 0 else "Empty")


def page_documents():
    st.title("📄 Documents")

    uploaded = st.file_uploader(
        "Upload Document",
        type=["pdf", "docx", "txt", "md", "json", "yaml", "sql", "png", "jpg"],
    )
    if uploaded and st.button("📤 Upload & Index", type="primary"):
        with st.spinner(f"Uploading {uploaded.name}..."):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            result = api_post("/api/qa/files/upload", files=files)
        if result:
            st.success(f"✅ **{result['filename']}** — {result.get('status', 'uploaded')}")

    st.divider()
    st.subheader("Indexed Documents")
    docs = api_get("/api/knowledge/documents")
    if docs:
        for doc in docs:
            icon = {"indexed": "✅", "failed": "❌", "pending": "⏳"}.get(doc.get("status", ""), "📄")
            col1, col2, col3 = st.columns([4, 1, 1])
            col1.markdown(f"{icon} **{doc['filename']}**")
            col2.caption(f"{doc.get('chunk_count', 0)} chunks")
            col3.caption(f"{doc.get('file_size', 0) // 1024}KB")
    else:
        st.info("No documents uploaded yet.")


def page_execution():
    st.title("▶️ Test Execution")

    tab1, tab2 = st.tabs(["Run Tests", "Execution History"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        framework = col1.selectbox("Framework", ["generic", "pytest", "playwright", "karate", "postman"])
        timeout = col2.slider("Timeout (s)", 30, 600, 300)
        retry_failed = col3.slider("Retries", 0, 3, 1)

        num_tests = st.number_input("Number of test cases", 1, 100, 3)
        test_cases = []
        with st.expander("Configure Tests", expanded=True):
            for i in range(int(num_tests)):
                c1, c2, c3 = st.columns([2, 4, 1])
                tc_id = c1.text_input("ID", value=f"TC{i+1:03d}", key=f"id_{i}")
                tc_name = c2.text_input("Name", value=f"Test {i+1}", key=f"name_{i}")
                tc_fail = c3.checkbox("Fail", key=f"fail_{i}")
                test_cases.append({"id": tc_id, "name": tc_name, "simulate_failure": tc_fail})

        if st.button("▶️ Execute Tests", type="primary", use_container_width=True):
            with st.spinner("Running tests..."):
                result = api_post("/api/reports/execute", {
                    "test_cases": test_cases,
                    "framework": framework,
                    "timeout": timeout,
                    "retry_failed": retry_failed,
                })
            if result:
                run_id = result.get("run_id", "")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", result.get("total_tests", 0))
                c2.metric("Passed", result.get("passed", 0))
                c3.metric("Failed", result.get("failed", 0))
                c4.metric("Success", f"{result.get('success_rate', 0):.1f}%")

                for r in result.get("results", []):
                    icon = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭"}.get(r.get("status"), "❓")
                    with st.expander(f"{icon} {r.get('test_id')} — {r.get('test_name')}"):
                        st.write(f"Status: {r.get('status')} | Duration: {r.get('duration', 0):.3f}s")
                        if r.get("error_message"):
                            st.error(r["error_message"])

                # Export
                fmt = st.selectbox("Export Format", ["markdown", "html", "json", "csv", "excel", "pdf", "docx"])
                if st.button("📥 Export"):
                    r = requests.get(f"{API_BASE}/api/reports/execute/{run_id}/export/{fmt}", headers=_headers(), timeout=60)
                    if r.status_code == 200:
                        ext = {"excel": "xlsx", "markdown": "md"}.get(fmt, fmt)
                        st.download_button("💾 Download", data=r.content, file_name=f"report_{run_id}.{ext}")
                    else:
                        st.error(f"Export failed: {r.text[:200]}")

    with tab2:
        history = api_get("/api/reports/history")
        if history:
            for run in history:
                with st.expander(f"Run {run['run_id']} — {run.get('framework', '?')} — {str(run.get('created_at', ''))[:16]}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Tests", run.get("total_tests", 0))
                    c2.metric("Passed", run.get("passed", 0))
                    c3.metric("Success", f"{run.get('success_rate', 0):.1f}%")
        else:
            st.info("No execution history yet.")


def page_reports():
    st.title("📈 Reports")

    runs = api_get("/api/reports/history") or []
    if not runs:
        st.info("No reports available. Run tests first.")
        return

    run_ids = [r["run_id"] for r in runs]
    selected = st.selectbox("Select Run", run_ids)

    if selected:
        report = api_get(f"/api/reports/execute/{selected}")
        if report:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", report.get("total_tests", 0))
            c2.metric("Passed", report.get("passed", 0))
            c3.metric("Failed", report.get("failed", 0))
            c4.metric("Success", f"{report.get('success_rate', 0):.1f}%")

            fmt = st.selectbox("Export Format", ["markdown", "html", "json", "csv", "excel", "pdf", "docx", "confluence"])
            if st.button("📥 Export Report", type="primary"):
                r = requests.get(f"{API_BASE}/api/reports/execute/{selected}/export/{fmt}", headers=_headers(), timeout=60)
                if r.status_code == 200:
                    ext = {"excel": "xlsx", "markdown": "md", "confluence": "txt"}.get(fmt, fmt)
                    st.download_button("💾 Download", data=r.content, file_name=f"report_{selected}.{ext}")
                else:
                    st.error(f"Export failed: {r.text[:200]}")


def page_settings():
    st.title("⚙️ Settings")

    tab1, tab2, tab3 = st.tabs(["Profile", "API Keys", "System"])

    with tab1:
        user = st.session_state.get("user", {})
        st.text_input("Username", value=user.get("username", ""), disabled=True)
        st.text_input("Email", value=user.get("email", ""))
        st.text_input("New Password", type="password")
        if st.button("Update Profile"):
            st.info("Profile update feature coming soon")

    with tab2:
        st.subheader("API Keys")
        keys = api_get("/auth/api-keys") or []
        for k in keys:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{k['name']}** — `{k['prefix']}...` ({'active' if k.get('is_active') else 'revoked'})")
            if col2.button("Revoke", key=f"rev_{k['id']}"):
                r = requests.delete(f"{API_BASE}/auth/api-keys/{k['id']}", headers=_headers(), timeout=10)
                if r.status_code == 200:
                    st.success("Revoked")
                    st.rerun()

        with st.form("create_key"):
            key_name = st.text_input("Key Name")
            expires = st.number_input("Expires (days, 0=never)", min_value=0, value=0)
            if st.form_submit_button("Generate API Key", type="primary"):
                result = api_post("/auth/api-keys", {"name": key_name, "expires_days": expires or None})
                if result:
                    st.success("Key created! Save this now:")
                    st.code(result.get("key", ""))

    with tab3:
        st.subheader("System Health")
        health = api_get("/health") or {}
        st.json(health)


def page_user_management():
    st.title("👥 User Management")
    users = api_get("/auth/users") or []

    for u in users:
        with st.expander(f"👤 {u['username']} ({', '.join(u.get('roles', []))})"):
            c1, c2 = st.columns(2)
            c1.write(f"**Email:** {u.get('email', 'N/A')}")
            c2.write(f"**Active:** {'✅' if u.get('is_active') else '❌'}")

    st.divider()
    st.subheader("Create User")
    with st.form("create_user"):
        c1, c2 = st.columns(2)
        u = c1.text_input("Username")
        e = c2.text_input("Email")
        p = c1.text_input("Password", type="password")
        n = c2.text_input("Full Name")
        r = st.multiselect("Roles", ["admin", "analyst", "developer", "tester", "viewer"], default=["viewer"])
        if st.form_submit_button("Create User", type="primary"):
            result = api_post("/auth/register", {"username": u, "email": e, "password": p, "full_name": n, "roles": r})
            if result:
                st.success(f"User '{u}' created!")
                st.rerun()


def page_train_ai():
    st.title("🧠 Train AI")
    st.caption("Paste any document to teach the AI about your systems. It will use this context in all future answers.")

    st.info(
        "**What to paste here:** Test case sheets · Requirements · Acceptance criteria · "
        "Jira descriptions · API specs · Bug reports · Previous QA sessions · Moniepoint flow docs"
    )

    with st.form("train_form"):
        title = st.text_input("Document Title", placeholder="e.g. Moniepoint Outbound Transfer Requirements v2")
        category = st.selectbox(
            "Category",
            ["requirements", "test-cases", "jira", "fintech", "gaming", "acceptance-criteria", "bug-report", "api-spec", "general"],
        )
        content = st.text_area(
            "Paste content here",
            height=350,
            placeholder="Paste your test sheet, requirement doc, Jira ticket, acceptance criteria, API spec, or any other document...",
        )
        submitted = st.form_submit_button("📥 Train AI with this document", type="primary", use_container_width=True)

    if submitted:
        if not title.strip() or not content.strip():
            st.error("Title and content are required.")
        else:
            result = api_post("/api/knowledge/ingest-text", {
                "title": title,
                "content": content,
                "category": category,
            })
            if result:
                st.success(f"✅ {result['message']}")
                st.metric("Chunks indexed", result.get("chunks", 0))

    st.divider()
    st.subheader("📚 What the AI Has Learned")
    docs = api_get("/api/knowledge/documents") or []
    if docs:
        training_docs = [d for d in docs if d.get("file_type") not in ("pdf", "docx", "txt")]
        all_docs = docs

        tab1, tab2 = st.tabs([f"All Documents ({len(all_docs)})", f"Pasted Training ({len(training_docs)})"])

        with tab1:
            for d in all_docs:
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{d['filename']}**")
                col2.write(f"`{d['file_type']}` · {d['chunk_count']} chunks")
                col3.write("✅ Indexed" if d["status"] == "indexed" else d["status"])

        with tab2:
            if training_docs:
                for d in training_docs:
                    st.write(f"🧠 **{d['filename']}** · `{d['file_type']}` · {d['chunk_count']} chunks")
            else:
                st.info("No pasted training documents yet. Use the form above to add some.")
    else:
        st.info("No documents indexed yet.")


def page_fintech_tests():
    st.title("💳 Fintech Tests")
    st.caption("Moniepoint payment flow testing — inbound transfers, outbound transfers, validations, reversals")

    CHECKS = ["debit_correct", "credit_correct", "balance_updated", "transaction_recorded", "notification_received", "response_time_ok"]
    CHECK_LABELS = {
        "debit_correct": "Debit ✓",
        "credit_correct": "Credit ✓",
        "balance_updated": "Balance Updated",
        "transaction_recorded": "Transaction Recorded",
        "notification_received": "Notification",
        "response_time_ok": "Response Time",
    }

    # Session setup
    with st.expander("⚙️ Session Setup", expanded=True):
        c1, c2, c3 = st.columns(3)
        session_name = c1.text_input("Session Name", placeholder="e.g. Moniepoint Outbound June 28")
        environment  = c2.selectbox("Environment", ["Staging", "UAT", "Production"])
        currency     = c3.text_input("Currency", value="NGN")

    st.divider()

    # Quick test builder
    st.subheader("📋 Add Test Scenarios")
    st.caption("Add each payment scenario you want to test")

    if "fintech_tests" not in st.session_state:
        st.session_state.fintech_tests = []

    # Quick add form
    with st.expander("➕ Add Test Scenario", expanded=len(st.session_state.fintech_tests) == 0):
        with st.form("add_fintech_test"):
            fc1, fc2 = st.columns(2)
            test_type = fc1.selectbox("Test Type", ["outbound", "inbound", "validation", "reversal"])
            scenario  = fc2.text_input("Scenario", placeholder="e.g. Transfer ₦5,000 to GTBank account")
            fc3, fc4, fc5, fc6 = st.columns(4)
            amount          = fc3.text_input("Amount (NGN)", placeholder="5000")
            sender_account  = fc4.text_input("Sender Account", placeholder="0123456789")
            receiver_account = fc5.text_input("Receiver Account", placeholder="0987654321")
            bal_before      = fc6.text_input("Balance Before", placeholder="10000")

            if st.form_submit_button("Add Scenario", type="primary"):
                if scenario.strip():
                    st.session_state.fintech_tests.append({
                        "test_type": test_type,
                        "scenario": scenario,
                        "amount": amount,
                        "sender_account": sender_account,
                        "receiver_account": receiver_account,
                        "balance_before": bal_before,
                        "balance_after": "",
                        "debit_correct": "OK",
                        "credit_correct": "OK",
                        "balance_updated": "OK",
                        "transaction_recorded": "OK",
                        "notification_received": "OK",
                        "response_time_ok": "OK",
                        "issue_description": "",
                        "screenshot_url": "",
                    })
                    st.rerun()

    # Bulk paste option
    with st.expander("📋 Bulk Paste Scenarios"):
        bulk = st.text_area(
            "One scenario per line: type | scenario | amount",
            placeholder="outbound | Transfer ₦5000 to GTBank | 5000\ninbound | Receive ₦10000 from Zenith | 10000\nvalidation | Invalid account number | 0",
            height=120,
        )
        if st.button("Load Bulk Scenarios"):
            for line in bulk.strip().splitlines():
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    st.session_state.fintech_tests.append({
                        "test_type": parts[0] if parts[0] in ["outbound","inbound","validation","reversal"] else "outbound",
                        "scenario": parts[1] if len(parts) > 1 else "",
                        "amount": parts[2] if len(parts) > 2 else "",
                        "sender_account": "", "receiver_account": "",
                        "balance_before": "", "balance_after": "",
                        "debit_correct": "OK", "credit_correct": "OK",
                        "balance_updated": "OK", "transaction_recorded": "OK",
                        "notification_received": "OK", "response_time_ok": "OK",
                        "issue_description": "", "screenshot_url": "",
                    })
            st.rerun()

    # Results table
    if st.session_state.fintech_tests:
        st.divider()
        st.subheader(f"✅ Mark Results — {len(st.session_state.fintech_tests)} Scenarios")

        TYPE_EMOJI = {"outbound": "⬆️", "inbound": "⬇️", "validation": "🔍", "reversal": "↩️"}

        for idx, test in enumerate(st.session_state.fintech_tests):
            emoji = TYPE_EMOJI.get(test["test_type"], "🔵")
            with st.expander(f"{emoji} {idx+1}. [{test['test_type'].upper()}] {test['scenario']}", expanded=False):
                cols = st.columns(len(CHECKS))
                any_fail = False
                for ci, ck in enumerate(CHECKS):
                    current = test[ck] == "OK"
                    toggled = cols[ci].checkbox(CHECK_LABELS[ck], value=current, key=f"ft_{idx}_{ck}")
                    st.session_state.fintech_tests[idx][ck] = "OK" if toggled else "-"
                    if not toggled:
                        any_fail = True

                rc1, rc2, rc3 = st.columns(3)
                bal_after = rc1.text_input("Balance After", value=test.get("balance_after",""), key=f"baf_{idx}")
                st.session_state.fintech_tests[idx]["balance_after"] = bal_after

                if any_fail:
                    issue = rc2.text_input("Issue Description", value=test.get("issue_description",""), key=f"ft_issue_{idx}")
                    ss    = rc3.text_input("Screenshot URL", value=test.get("screenshot_url",""), key=f"ft_ss_{idx}")
                    st.session_state.fintech_tests[idx]["issue_description"] = issue
                    st.session_state.fintech_tests[idx]["screenshot_url"] = ss

                if st.button("🗑️ Remove", key=f"rm_ft_{idx}"):
                    st.session_state.fintech_tests.pop(idx)
                    st.rerun()

        # Summary
        st.divider()
        total  = len(st.session_state.fintech_tests)
        passed = sum(1 for t in st.session_state.fintech_tests if all(t[c] == "OK" for c in CHECKS))
        failed = total - passed

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total", total)
        s2.metric("✅ Passed", passed)
        s3.metric("❌ Failed", failed)
        s4.metric("Pass Rate", f"{passed/total*100:.0f}%" if total else "0%")

        st.divider()
        ec1, ec2 = st.columns(2)

        with ec1:
            if st.button("📊 Export Excel Report", type="primary", use_container_width=True):
                payload = {
                    "session_name": session_name,
                    "environment": environment,
                    "currency": currency,
                    "tests": st.session_state.fintech_tests,
                }
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/fintech/report/excel",
                        headers=_headers(), json=payload, timeout=30,
                    )
                    if resp.status_code == 200:
                        st.download_button(
                            "⬇️ Download Excel",
                            data=resp.content,
                            file_name=f"fintech_test_{session_name or 'report'}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    else:
                        st.error(f"Export failed: {resp.text[:200]}")
                except Exception as e:
                    st.error(f"Export error: {e}")

        with ec2:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.fintech_tests = []
                st.rerun()
    else:
        st.info("Add test scenarios above to get started.")


def page_gaming_tests():
    st.title("🎮 Gaming Tests")
    st.caption("Record game test results and export your QA report in one click")

    # ── Session Setup ─────────────────────────────────────────────────────────
    with st.expander("⚙️ Session Setup", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        session_name = c1.text_input("Session Name", placeholder="e.g. Booming Games June 28")
        min_bet = c2.text_input("Min Bet", value="1")
        max_bet = c3.text_input("Max Bet", value="5000")
        currency = c4.text_input("Currency", value="LSL")

    st.divider()

    # ── Game List Builder ─────────────────────────────────────────────────────
    st.subheader("📋 Game List")
    st.caption("Paste your game list below — one game per line as: Provider | Game Name")

    sample = "Booming | Cash Pig 2\nEvoplay | Cricket Duel\nOaks | Lord of Thunder\nScatterkings | 10 Sliding Wilds"
    raw_list = st.text_area("Paste game list", height=150, placeholder=sample)

    if "gaming_games" not in st.session_state:
        st.session_state.gaming_games = []

    if st.button("📥 Load Games", type="primary"):
        games = []
        for line in raw_list.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                parts = line.split("|", 1)
                provider = parts[0].strip().rstrip(":")
                name = parts[1].strip()
            else:
                provider = ""
                name = line.strip()
            games.append({
                "provider": provider, "game_name": name,
                "game_image": "OK", "launch_and_play": "OK",
                "debit": "OK", "credit": "OK", "min_max_bet": "OK",
                "issue_description": "", "screenshot_url": "",
            })
        st.session_state.gaming_games = games
        st.success(f"Loaded {len(games)} games. Mark results below.")
        st.rerun()

    # ── Result Entry ──────────────────────────────────────────────────────────
    if st.session_state.gaming_games:
        st.divider()
        st.subheader(f"✅ Mark Results — {len(st.session_state.gaming_games)} Games")
        st.caption("Toggle each check. Any FAIL will prompt for issue description.")

        CHECKS = ["game_image", "launch_and_play", "debit", "credit", "min_max_bet"]
        CHECK_LABELS = {
            "game_image": "Game Image",
            "launch_and_play": "Launch & Play",
            "debit": "Debit",
            "credit": "Credit",
            "min_max_bet": "Min/Max Bet",
        }

        # Column headers
        hdr = st.columns([1, 2, 3, 2, 2, 2, 2, 2])
        hdr[0].markdown("**#**")
        hdr[1].markdown("**Provider**")
        hdr[2].markdown("**Game Name**")
        for i, ck in enumerate(CHECKS):
            hdr[3 + i].markdown(f"**{CHECK_LABELS[ck]}**")

        for idx, game in enumerate(st.session_state.gaming_games):
            cols = st.columns([1, 2, 3, 2, 2, 2, 2, 2])
            cols[0].write(idx + 1)
            cols[1].write(game["provider"])
            cols[2].write(game["game_name"])

            any_fail = False
            for ci, ck in enumerate(CHECKS):
                current = game[ck] == "OK"
                toggled = cols[3 + ci].checkbox(
                    "OK", value=current,
                    key=f"g_{idx}_{ck}",
                    label_visibility="visible"
                )
                st.session_state.gaming_games[idx][ck] = "OK" if toggled else "-"
                if not toggled:
                    any_fail = True

            if any_fail:
                with st.expander(f"⚠️ Issue for {game['game_name']}", expanded=False):
                    issue = st.text_input(
                        "Bug Description",
                        value=game.get("issue_description", ""),
                        key=f"issue_{idx}",
                        placeholder="e.g. game launch fail with blank white screen",
                    )
                    screenshot = st.text_input(
                        "Screenshot URL",
                        value=game.get("screenshot_url", ""),
                        key=f"ss_{idx}",
                        placeholder="https://jam.dev/c/...",
                    )
                    st.session_state.gaming_games[idx]["issue_description"] = issue
                    st.session_state.gaming_games[idx]["screenshot_url"] = screenshot

        st.divider()

        # ── Live Summary ──────────────────────────────────────────────────────
        total = len(st.session_state.gaming_games)
        passed = sum(
            1 for g in st.session_state.gaming_games
            if all(g[c] == "OK" for c in CHECKS)
        )
        failed = total - passed

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total Games", total)
        s2.metric("✅ Tested OK", passed)
        s3.metric("❌ Open Issues", failed)
        s4.metric("Pass Rate", f"{passed/total*100:.0f}%" if total else "0%")

        st.divider()

        # ── Export ────────────────────────────────────────────────────────────
        col_exp, col_script = st.columns(2)

        with col_exp:
            if st.button("📊 Export Excel Report", type="primary", use_container_width=True):
                payload = {
                    "session_name": session_name,
                    "min_bet": min_bet,
                    "max_bet": max_bet,
                    "currency": currency,
                    "games": st.session_state.gaming_games,
                }
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/gaming/report/excel",
                        headers=_headers(),
                        json=payload,
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=resp.content,
                            file_name=f"gaming_test_{session_name or 'report'}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    elif resp.status_code == 501:
                        st.error("Install openpyxl: pip install openpyxl")
                    else:
                        st.error(f"Export failed: {resp.text[:200]}")
                except Exception as e:
                    st.error(f"Export error: {e}")

        with col_script:
            if st.button("🤖 Generate Playwright Script", use_container_width=True):
                payload = {
                    "session_name": session_name,
                    "min_bet": min_bet,
                    "max_bet": max_bet,
                    "currency": currency,
                    "games": st.session_state.gaming_games,
                }
                result = api_post("/api/gaming/playwright-script", payload)
                if result:
                    st.code(result["script"], language="javascript")
                    st.download_button(
                        "⬇️ Download Script",
                        result["script"],
                        file_name="gaming_test.js",
                        mime="text/javascript",
                    )

        if st.button("🗑️ Clear All Games", use_container_width=True):
            st.session_state.gaming_games = []
            st.rerun()
    else:
        st.info("Paste your game list above and click **Load Games** to start.")


# ─── Router ───────────────────────────────────────────────────────────────────

PAGE_MAP = {
    "Dashboard": page_dashboard,
    "Chat": page_chat,
    "Gaming Tests": page_gaming_tests,
    "Fintech Tests": page_fintech_tests,
    "Train AI": page_train_ai,
    "Test Cases": page_test_cases,
    "SQL Review": page_sql_review,
    "Security Review": page_security_review,
    "Bug Investigation": page_bug_investigation,
    "Knowledge Base": page_knowledge_base,
    "Documents": page_documents,
    "Execution": page_execution,
    "Reports": page_reports,
    "Settings": page_settings,
    "User Management": page_user_management,
}


def main():
    if not st.session_state.token:
        login_page()
        return

    sidebar()
    current = st.session_state.get("page", "Dashboard")
    PAGE_MAP.get(current, page_dashboard)()


if __name__ == "__main__":
    main()
