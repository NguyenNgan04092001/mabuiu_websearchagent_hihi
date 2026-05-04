# Web Research Agent

LLM-powered researcher kết hợp **OpenAI-compatible models** (qua OpenRouter) với **Tavily Search**. Agent chia câu hỏi thành nhiều search song song, tổng hợp kết quả, và trả về danh sách bài viết liên quan dạng JSON. Có sẵn **CLI** và **Streamlit UI**.

---

## 📖 Guides & Documentation

> **🚀 Muốn deploy ngay lên Streamlit Cloud?** Xem [QUICK_START_CLOUD.md](./QUICK_START_CLOUD.md) (5 phút)

| Document                                             | Purpose                                       |
| ---------------------------------------------------- | --------------------------------------------- |
| [QUICK_START_CLOUD.md](./QUICK_START_CLOUD.md)       | ⚡ Deploy nhanh lên Streamlit Cloud (5 min)   |
| [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) | ✅ Bảng checklist chi tiết từng bước          |
| [SECURITY.md](./SECURITY.md)                         | 🔒 Hướng dẫn bảo mật API keys & secrets       |
| [CHANGES.md](./CHANGES.md)                           | 📋 Những thay đổi để hỗ trợ Streamlit Secrets |

---

## ✨ Features

- OpenAI Chat Completions với function calling (tương thích OpenRouter / OpenAI)
- Batch 2–8 `search_web` tool calls trong một lượt LLM
- Concurrent search qua **Tavily API** (free 1,000 search/tháng)
- Streamlit UI realtime (live progress + cards kết quả)
- CLI với JSON trace tuỳ chọn (`--outfile`)

---

## 📋 Requirements

- Python 3.9+ (3.10+ recommended)
- `OPENROUTER_API_KEY` hoặc `OPENAI_API_KEY`
- `TAVILY_API_KEY`

---

## 🚀 Install

```bash
cd web-research-agent
python -m venv search_env
source search_env/bin/activate
pip install -r requirements.txt
```

---

## 🔑 Setup API keys

### Local development (máy bạn)

Lấy keys:

- **Tavily** → https://app.tavily.com/ (free 1,000 search/tháng, key dạng `tvly-...`)
- **OpenRouter** → https://openrouter.ai/keys (có nhiều model `:free`, key dạng `sk-or-...`)

Tạo file `.env` từ mẫu rồi điền key:

```bash
cp .env.example .env
```

Nội dung `.env`:

```bash
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

> ⚠️ **Bảo mật:** Không commit `.env` lên Git (đã có trong `.gitignore`). Không share key với ai.

### Production (Streamlit Cloud)

Xem phần **Deploy public** → **Option B** bên dưới để setup secrets trên Streamlit Cloud.

---

## ⚡ Quick start

### Streamlit UI (khuyên dùng)

```bash
streamlit run app.py
```

Mở http://localhost:8501 trong trình duyệt. Nhập câu hỏi, chọn model, nhấn **Run**.

### CLI

```bash
# Chạy cơ bản
python research_agent.py -q "What are the latest approaches to RAG in 2025?" -m openai/gpt-4o

# Model free trên OpenRouter
python research_agent.py -q "..." -m openai/gpt-oss-120b:free

# Lưu JSON trace
python research_agent.py -q "State of LLM reasoning benchmarks in 2025" \
    -m anthropic/claude-sonnet-4.5 \
    --outfile trace.json
```

---

## 🛠️ CLI reference

```
usage: research_agent.py [-h] -q QUERY [-m MODEL] [-n TOPN] [-o OUTFILE] [-d]

  -q, --query     Research question (required)
  -m, --model     Model name (default: openai/gpt-4o)
  -n, --topn      Tavily results per search (default: 10)
  -o, --outfile   Write full JSON trace to file
  -d, --debug     Print debug logs
```

---

## 🌐 Deploy public

### ⚡ Giải pháp nhanh: Streamlit Cloud + Secrets

### Option A — Tunnel tạm (cloudflared / ngrok)

App chạy trên máy bạn, share link công khai trong vài giờ:

```bash
streamlit run app.py --server.port 8501 &
cloudflared tunnel --url http://localhost:8501
```

### Option B — Streamlit Community Cloud (free, host vĩnh viễn) ⭐

1. **Đảm bảo `.env` không bị commit** — file `.gitignore` đã chứa `.env`, kiểm tra:

   ```bash
   git status  # .env không nên xuất hiện
   ```

2. **Push code lên GitHub** — chỉ push mã nguồn, bỏ `.env`:

   ```bash
   git add .
   git commit -m "Deploy to Streamlit Cloud"
   git push
   ```

3. **Vào https://share.streamlit.io** → đăng nhập GitHub → **New app**
   - Chọn repo
   - Branch: `main`
   - File path: `app.py`

4. **Setup Secrets** (thay thế API keys):
   - Khi deploy, Streamlit sẽ yêu cầu nhập Secrets
   - Hoặc vào **Settings** → **Secrets** → dán vào:

   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxxxxx"
   OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
   ```

   - **Không cần thêm .env file!** Streamlit tự inject secrets vào `st.secrets`

5. **Redeploy** → URL `https://your-app.streamlit.app`

> 💡 **Cách hoạt động:** Code auto detect secrets từ `st.secrets` (Streamlit Cloud) hoặc `.env` (local dev). Không cần sửa code!

> ⚠️ **Bảo mật:** Secrets được encrypt và không bao giờ lộ trong logs hay UI. Mỗi request chạy trong container riêng.

---

## 🧠 How it works

1. System prompt yêu cầu LLM emit nhiều `search_web` calls cùng lúc
2. Agent chạy tất cả search Tavily song song (`ThreadPoolExecutor`)
3. Snippets được feed lại cho LLM dưới dạng tool messages
4. LLM trả về JSON với danh sách bài viết: `title`, `url`, `summary`, `why_relevant`

> **Note:** Reasoning models (o3, o4-mini) thường chỉ emit 1 tool call mỗi turn — `gpt-4o` hoặc `claude-sonnet` cho kết quả tốt hơn khi cần nhiều search.

---

## 📦 Programmatic use

```python
from research_agent import ResearchAgent

agent = ResearchAgent(model="openai/gpt-4o", topn=10)
result = agent.run("Summarize the most cited papers on RAG.")

print(result["answer"])      # raw JSON từ LLM
print(len(result["steps"]))  # số bước (tool_call, tool_result, answer)
```

Với callback realtime (dùng cho UI):

```python
agent = ResearchAgent(
    model="openai/gpt-4o",
    on_event=lambda e: print(e),  # nhận turn_start, search_start, search_done, …
)
```

---

## 📄 JSON trace example

```json
{
  "question": "...",
  "answer": "{\"articles\": [...]}",
  "steps": [
    { "type": "tool_call", "query": "first search" },
    { "type": "tool_result", "content": "- Title: snippet ..." },
    { "type": "assistant_answer", "content": "final answer text" }
  ]
}
```

---

## 🐛 Troubleshooting

### API Keys / Setup

| Lỗi                                                                     | Nguyên nhân & Cách xử lý                                                               |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY (or OPENROUTER_API_KEY) and TAVILY_API_KEY must be set` | **.env chưa setup** → Chạy `cp .env.example .env` rồi điền keys vào                    |
| Lỗi khi deploy lên Streamlit Cloud                                      | **Secrets chưa setup** → Vào Settings → Secrets → dán TOML từ phần "Option B" bên trên |
| Key hết quota (Tavily)                                                  | Check tại https://app.tavily.com/ → Upgrade plan hoặc đợi reset tháng sau              |
| Model not available                                                     | Xem danh sách OpenRouter models tại https://openrouter.ai/models                       |

### Lỗi chạy

| Lỗi                                    | Cách xử lý                                                                       |
| -------------------------------------- | -------------------------------------------------------------------------------- |
| `Could not parse article list`         | Model trả về output không đúng JSON — thử model mạnh hơn (gpt-4o, claude-sonnet) |
| Empty / failed searches                | Check Tavily key & quota tại https://app.tavily.com/                             |
| Streamlit error: `ModuleNotFoundError` | Chạy `pip install -r requirements.txt`                                           |

---

## 📜 License

MIT License — xem [LICENSE](LICENSE).
