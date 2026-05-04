# 🔒 Security Guide — API Keys & Secrets

## Vấn đề

Khi deploy app lên Streamlit Cloud, bạn gặp hai tình huống:

1. ❌ **Không có `.env` trên Cloud** → App bị lỗi thiếu API keys
2. ❌ **Commit `.env` lên GitHub** → API keys lộ công khai → AI khác dùng, tốn tiền của bạn

## ✅ Giải pháp: Streamlit Secrets Management

### Cách hoạt động

```
Local Development                Production (Streamlit Cloud)
┌──────────────────┐             ┌──────────────────┐
│   .env file      │    vs       │  st.secrets      │
│  (git ignored)   │             │  (encrypted)     │
└──────────────────┘             └──────────────────┘
         ↓                                ↓
   os.getenv()                    st.secrets[key]
         ↓                                ↓
   ┌──────────────────────────────────────────┐
   │  get_secret(key)  # Auto-detect & fallback
   └──────────────────────────────────────────┘
```

**Code (research_agent.py):**

```python
def get_secret(key: str, default: str = None) -> str:
    """Get từ Streamlit secrets (prod) hoặc .env (local)"""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except ImportError:
        pass
    return os.getenv(key, default)
```

### Step 1: Local Development

#### a) Tạo `.env` từ template

```bash
cd web-research-agent
cp .env.example .env
```

#### b) Điền API keys

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

#### c) Test local

```bash
streamlit run app.py
```

✅ App hoạt động bình thường, `.env` được ignore (không commit).

### Step 2: Deploy lên Streamlit Cloud

#### a) Push code (không .env!)

```bash
git status  # .env không nên xuất hiện
git add .
git commit -m "Deploy v1"
git push origin main
```

#### b) Vào Streamlit Cloud

- Mở https://share.streamlit.io
- Đăng nhập GitHub
- Chọn **New app** → chọn repo → `main` branch → file `app.py`

#### c) Setup Secrets (quan trọng!)

- Trong deploy settings, chọn **Settings** → **Secrets**
- Dán nội dung (TOML format):
  ```toml
  OPENROUTER_API_KEY = "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx"
  TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxxxx"
  OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
  ```
- **Lưu** → App tự redeploy

✅ Secrets được encrypt + inject vào container. Không lộ trong logs, code, hay URL.

### Step 3: Monitor & Update

- **Check status:** https://share.streamlit.io → xem logs
- **Update secrets:** Settings → Secrets → sửa → Save (redeploy tự động)
- **View app logs:** App sẽ show `✅ Loaded from secrets`

## 🚨 Security Best Practices

### ✅ DO

- [ ] Keep `.env` in `.gitignore`
- [ ] Use separate keys for dev/prod nếu có thể
- [ ] Rotate keys periodically (mỗi 3-6 tháng)
- [ ] Monitor quota (OpenRouter, Tavily) để detect abuse
- [ ] Use strong keys (40+ chars random)

### ❌ DON'T

- [ ] Commit `.env` hoặc `secrets.toml` lên Git
- [ ] Share API keys qua Slack, Email, hay code comments
- [ ] Hardcode keys trong source code
- [ ] Use dev keys cho production
- [ ] Restart app mà không reload secrets (Streamlit auto-inject)

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"

**Local:**

```bash
cp .env.example .env  # Tạo .env
# Sửa .env, điền keys
streamlit run app.py  # Test
```

**Cloud:**

- Vào Settings → Secrets → kiểm tra có key không
- Kiểm tra tên key chính xác: `OPENROUTER_API_KEY` (không phải `OPENAI_API_KEY`)
- Save → app auto-redeploy

### "Secrets loaded but key is None"

- Streamlit chỉ load secrets lúc app restart
- Nếu sửa `.env` local: Ctrl+C + `streamlit run app.py`
- Nếu sửa secrets trên Cloud: Auto-reload (1-2 phút)

### "Key still visible in logs"

- ✅ Streamlit **không bao giờ** log secret values
- Nếu bạn print/log key → lỗi code, xóa ngay
- Revoke key tại OpenRouter/Tavily rồi generate key mới

## 📚 References

- [Streamlit Secrets Documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [OpenRouter API Docs](https://openrouter.ai/docs)
- [Tavily Search Docs](https://docs.tavily.com/)
- [Best Practices for Secrets Management](https://12factor.net/config)
