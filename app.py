import json
import queue
import threading
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from research_agent import ResearchAgent, SOURCE_PRESETS, _extract_articles

load_dotenv()

st.set_page_config(page_title="Web Research Agent", page_icon="🔎", layout="wide")

PRESET_MODELS = [
    "openai/gpt-oss-120b:free",
]

with st.sidebar:
    st.header("⚙️ Settings")

    model_choice = st.selectbox("Model", PRESET_MODELS, index=0)
    model = model_choice

    st.divider()
    st.subheader("📚 Sources")

    preset = st.selectbox(
        "Source preset",
        list(SOURCE_PRESETS.keys()),
        index=1,  # default to IR Mixed
        help="Restrict web searches to a curated whitelist of academic + IR domains.",
    )
    include_domains = SOURCE_PRESETS[preset]
    if include_domains:
        with st.expander(f"Whitelist ({len(include_domains)} domains)"):
            st.write(", ".join(include_domains))

    enable_academic = st.checkbox(
        "Enable academic search (Semantic Scholar + OpenAlex)",
        value=True,
        help="Adds two extra tools that hit free academic APIs and return full abstracts.",
    )

    st.divider()
    st.subheader("🔧 Search params")

    depth = st.radio(
        "Tavily depth",
        ["basic", "advanced"],
        index=0,
        horizontal=True,
        help="`basic` is 2-3× faster; `advanced` extracts more content per page.",
    )
    topn = st.slider("Results / search", 3, 20, 5)

st.title("🔎 Web Research Agent")
st.caption("LLM tự chia nhỏ câu hỏi → search Tavily + Semantic Scholar + OpenAlex → tổng hợp danh sách bài viết liên quan.")

query = st.text_area(
    "Câu hỏi nghiên cứu",
    value="What are the latest approaches to retrieval-augmented generation in 2025?",
    height=80,
)

col1, col2 = st.columns([1, 5])
run = col1.button("▶ Run research", type="primary", use_container_width=True)


def run_agent(q: str, ev_queue: "queue.Queue", store: dict) -> None:
    try:
        agent = ResearchAgent(
            model=model,
            topn=topn,
            on_event=lambda e: ev_queue.put(e),
            include_domains=include_domains,
            enable_academic_tools=enable_academic,
            search_depth=depth,
        )
        result = agent.run(q)
        store["result"] = result
    except Exception as e:
        store["error"] = str(e)
    finally:
        ev_queue.put({"type": "__done__"})


ENGINE_ICON = {
    "web": "🔍",
    "semantic_scholar": "📖",
    "openalex": "📚",
}


if run:
    if not query.strip():
        st.warning("Nhập câu hỏi trước đã.")
        st.stop()

    ev_queue: "queue.Queue" = queue.Queue()
    store: dict = {}
    worker = threading.Thread(target=run_agent, args=(query, ev_queue, store), daemon=True)
    worker.start()

    log_lines: list[str] = []
    with st.status("Đang nghiên cứu…", expanded=True) as status:
        log_box = st.empty()
        while True:
            ev = ev_queue.get()
            ts = datetime.now().strftime("%H:%M:%S")
            t = ev.get("type")
            if t == "__done__":
                break
            elif t == "turn_start":
                log_lines.append(f"`{ts}` 🧠 **Turn {ev['turn']}** — gọi LLM ({ev['model']})…")
            elif t == "turn_done":
                log_lines.append(
                    f"`{ts}` ✅ Turn {ev['turn']} xong sau {ev['elapsed']:.1f}s "
                    f"(tool_calls={ev['tool_calls']})"
                )
            elif t == "search_start":
                icon = ENGINE_ICON.get(ev.get("engine", "web"), "🔍")
                engine = ev.get("engine", "web")
                log_lines.append(f"`{ts}` {icon} {engine}: `{ev['query']}`")
            elif t == "search_done":
                err = ev.get("error")
                if err:
                    log_lines.append(
                        f"`{ts}` ⚠️ {ev.get('engine','?')} error trong {ev['elapsed']:.1f}s: {err}"
                    )
                else:
                    log_lines.append(
                        f"`{ts}` 📥 {ev.get('engine','?')} — {ev['count']} results trong {ev['elapsed']:.1f}s"
                    )
            log_box.markdown("\n\n".join(log_lines))

        if "error" in store:
            err = store["error"]
            status.update(label=f"❌ Lỗi: {err}", state="error")
            if "tool use" in err.lower() or "404" in err:
                st.error(
                    f"Model **{model}** không hỗ trợ tool calling (function calling). "
                    "Agent này cần tool calling để gọi search. Hãy chọn model khác ở sidebar — "
                    "ví dụ `google/gemini-2.0-flash-exp:free`, `openai/gpt-4o-mini`, "
                    "hoặc `anthropic/claude-haiku-4-5`. "
                    "Xem danh sách model có tool use tại "
                    "https://openrouter.ai/models?supported_parameters=tools"
                )
            st.stop()
        status.update(label="✅ Hoàn tất", state="complete")

    result = store["result"]
    articles = _extract_articles(result["answer"])

    st.subheader(f"📚 {len(articles)} bài viết liên quan")

    if not articles:
        st.warning("Không parse được JSON. Hiển thị raw:")
        st.code(result["answer"])
    else:
        for i, a in enumerate(articles, 1):
            with st.container(border=True):
                st.markdown(f"### [{i}. {a.get('title', '(no title)')}]({a.get('url', '#')})")
                meta = []
                if a.get("source_type"):
                    meta.append(f"`{a['source_type']}`")
                if a.get("url"):
                    meta.append(a["url"])
                if meta:
                    st.caption(" · ".join(meta))
                if a.get("summary"):
                    st.markdown(f"**Tóm tắt:** {a['summary']}")
                if a.get("why_relevant"):
                    st.markdown(f"**Vì sao liên quan:** {a['why_relevant']}")

    st.divider()
    payload = json.dumps(
        {**result, "articles": articles}, indent=2, ensure_ascii=False,
    )
    st.download_button(
        "⬇ Tải JSON đầy đủ (trace + articles)",
        data=payload,
        file_name="research_result.json",
        mime="application/json",
    )

    with st.expander("🪵 Raw LLM output"):
        st.code(result["answer"])
