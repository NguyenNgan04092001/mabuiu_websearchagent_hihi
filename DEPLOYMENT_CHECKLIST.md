# ✅ Deployment Checklist

Hướng dẫn từng bước để deploy app lên Streamlit Cloud mà không lộ API keys.

## 📝 Before Deployment

### Local Setup

- [ ] `cp .env.example .env` — tạo file .env local
- [ ] Điền 3 keys vào `.env`:
  - [ ] `OPENROUTER_API_KEY=sk-or-...`
  - [ ] `TAVILY_API_KEY=tvly-...`
  - [ ] `OPENAI_BASE_URL=https://openrouter.ai/api/v1`
- [ ] `streamlit run app.py` — test local (kiểm tra không có lỗi API)
- [ ] Ctrl+C để dừng

### Git Setup

- [ ] `git status` — đảm bảo `.env` không xuất hiện
- [ ] `.gitignore` chứa `.env` (đã có sẵn)
- [ ] `git add .` → `git commit -m "Deploy to Streamlit"` → `git push`

## 🚀 Deployment Steps

### 1️⃣ Push code to GitHub

```bash
git status                    # Verify .env is NOT listed
git add .
git commit -m "Deploy v1.0"
git push origin main
```

### 2️⃣ Create app trên Streamlit Cloud

- Mở https://share.streamlit.io
- Đăng nhập GitHub (nếu chưa)
- **New app** → chọn:
  - Repository: `your-username/web-research-agent`
  - Branch: `main`
  - File: `app.py`
- Nhấn **Deploy**

### 3️⃣ Setup Secrets (quan trọng!)

Khi deploy, Streamlit sẽ yêu cầu secrets hoặc bạn có thể vào Settings sau:

**Settings → Secrets:**

```toml
OPENROUTER_API_KEY = "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx"
TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxxxx"
OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
```

Nhấn **Save** → app auto-redeploy với secrets.

### 4️⃣ Test on Cloud

- Chờ app deploy (~2-3 phút)
- Nhập câu hỏi → chạy research
- ✅ Nếu thành công → DONE!
- ❌ Nếu lỗi → kiểm tra logs

## 🔍 Verify Security

### Local

```bash
cat .env                # Đảm bảo có keys
cat .gitignore          # Đảm bảo có .env
git log -p .env         # Nên trống (không history)
```

### Cloud

- https://share.streamlit.io → chọn app → Logs
- Kiểm tra không có API key nào in ra
- Secrets được load (sẽ see "✅ Loaded from secrets")

## 🐛 Troubleshooting

| Lỗi                       | Fix                                                     |
| ------------------------- | ------------------------------------------------------- |
| `OPENAI_API_KEY not set`  | Vào Settings → Secrets → kiểm tra key đúng chưa → Save  |
| App stuck on loading      | Chờ 2-3 phút, refresh browser                           |
| "Can't import streamlit"  | Ensure `requirements.txt` có `streamlit`, push lại code |
| Key still visible in logs | ⚠️ BUG! Revoke key tại OpenRouter/Tavily, tạo key mới   |

## 🔄 Updates & Maintenance

### Cập nhật code

```bash
# Local dev
git add .
git commit -m "Fix bug X"
git push
# Cloud auto-redeploy trong 1-2 phút
```

### Update secrets

- Settings → Secrets → sửa → Save
- App auto-redeploy (1-2 phút)
- ✅ Không cần push code

### Rotate keys

Mỗi 3-6 tháng:

1. Generate key mới tại OpenRouter / Tavily
2. Cloud: Settings → Secrets → update key
3. Local: sửa `.env` (git ignore)
4. Revoke key cũ tại service

## 📚 References

- [Security Guide](./SECURITY.md) — chi tiết về secrets management
- [Streamlit Docs](https://docs.streamlit.io/) — deployment docs
- [README.md](./README.md) — feature & usage guide
