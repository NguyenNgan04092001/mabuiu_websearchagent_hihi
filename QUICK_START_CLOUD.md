# 🚀 Quick Start — Deploy to Streamlit Cloud (5 min)

Bạn muốn deploy app lên Streamlit Cloud ngay mà không lộ API keys? Làm theo đúng 4 bước này:

## 1️⃣ Local Setup (máy bạn)

```bash
# Copy template .env
cp .env.example .env

# Mở .env, điền 3 keys của bạn:
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

**Test:**

```bash
streamlit run app.py
# Đơn nhập câu hỏi, click Run. Nếu OK → Next step
```

## 2️⃣ Push Code (GitHub)

```bash
# Kiểm tra .env không bị commit
git status  # .env không nên xuất hiện ✓

# Commit & push
git add .
git commit -m "Ready for Streamlit deployment"
git push origin main
```

## 3️⃣ Deploy (Streamlit Cloud)

1. Vào https://share.streamlit.io
2. **New app** → chọn:
   - **Repository:** your-github/web-research-agent
   - **Branch:** main
   - **File:** app.py
3. Nhấn **Deploy**

> Chờ 2-3 phút, sau đó bạn thấy giao diện app loading...

## 4️⃣ Setup Secrets (QUAN TRỌNG!)

Sau khi deploy xong:

1. **Click ⋮ menu** ở góc trên phải
2. **Settings** → **Secrets**
3. **Dán nội dung này (copy-paste):**
   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxxxx"
   OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
   ```
4. **Save** → App tự restart

> ✅ Xong! App của bạn giờ sẽ hoạt động trên `https://your-app.streamlit.app`

## 🎯 Verify

- [ ] App load được
- [ ] Gõ câu hỏi → Click **Run**
- [ ] Thấy kết quả → **THÀNH CÔNG! 🎉**

## ⚠️ Nếu lỗi

### "OPENAI_API_KEY not set"

→ Chưa setup Secrets. Làm lại bước 4

### "Can't connect to Tavily"

→ Check key Tavily tại https://app.tavily.com/ (có bị hết quota không?)

### "ModuleNotFoundError"

→ Chạy `pip install -r requirements.txt` local, sau đó push lại

## 📚 Tài liệu chi tiết

- **Hiểu rõ hơn:** [SECURITY.md](./SECURITY.md)
- **Checklist chi tiết:** [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- **Troubleshooting:** [README.md#-troubleshooting](./README.md#-troubleshooting)

## 🔒 Bảo mật

- ✅ `.env` nằm trong `.gitignore` (không bị push)
- ✅ Secrets được encrypt trên Streamlit Cloud
- ✅ Keys không bao giờ lộ trong logs

> **Never share `.env` or API keys!** 🚫
