# 📋 What's Changed — API Keys & Secrets Setup

Giải quyết vấn đề: **Cách deploy lên Streamlit Cloud mà không lộ API keys**

## 🔧 Code Changes

### research_agent.py

✅ **Thêm hàm `get_secret()`** để auto-detect API keys từ 2 nguồn:

- **Local:** Đọc từ `.env` (qua `os.getenv()`)
- **Cloud:** Đọc từ Streamlit `st.secrets` (encrypted)
- **Fallback:** Environment variables

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

✅ **Sửa dòng 121-124:** Dùng `get_secret()` thay vì `os.getenv()` trực tiếp

### app.py

✅ Không cần sửa — code đã tương thích (hỗ trợ cả .env và st.secrets)

## 📁 New Files Created

### 1. `.env.example`

Template để user copy & điền keys:

```bash
cp .env.example .env  # Local dev
```

### 2. `.streamlit/secrets.toml.example`

Reference format cho Streamlit secrets (local testing optional)

### 3. `SECURITY.md`

Hướng dẫn chi tiết về:

- Cách hoạt động của secrets management
- Best practices bảo mật
- Troubleshooting

### 4. `DEPLOYMENT_CHECKLIST.md`

Bảng checklist từng bước:

- Setup local dev
- Push code lên GitHub
- Deploy trên Streamlit Cloud
- Setup secrets
- Verify security

## 📝 Files Modified

### 1. `.gitignore`

✅ Thêm rules để ignore Streamlit secrets:

```
.streamlit/secrets.toml
.streamlit/cache/
```

### 2. `README.md`

✅ Sửa phần "🔑 Setup API keys":

- Phân chia: Local dev vs Production (Cloud)
- Chi tiết step-by-step setup secrets trên Streamlit Cloud

✅ Sửa phần "🌐 Deploy public" → "Option B":

- Hướng dẫn setup secrets trong Streamlit Cloud interface
- Giải thích cách hoạt động (auto-detect secrets)
- Cảnh báo bảo mật

✅ Cập nhật phần "🐛 Troubleshooting":

- Thêm nguyên nhân & cách xử lý lỗi API keys
- Hướng dẫn setup secrets

## ✅ How It Works Now

### Local Development (máy bạn)

```bash
cp .env.example .env
# Sửa .env, điền keys
streamlit run app.py
# Code đọc keys từ .env qua get_secret()
```

### Production (Streamlit Cloud)

```
1. Push code lên GitHub (không .env!)
2. Deploy lên Streamlit Cloud
3. Settings → Secrets → dán TOML
4. App auto-read từ st.secrets qua get_secret()
```

**Kết quả:**

- ✅ Local: Hoạt động bình thường với .env
- ✅ Cloud: Hoạt động bình thường với st.secrets
- ✅ Không lộ keys trên GitHub
- ✅ Không lộ keys trong logs

## 🚀 Next Steps

### Để deploy ngay:

1. Đọc [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
2. Thực hiện từng bước
3. Test lên Cloud

### Để hiểu chi tiết:

1. Đọc [SECURITY.md](./SECURITY.md)
2. Xem phần "🔑 Setup API keys" trong [README.md](./README.md)

### Nếu gặp lỗi:

1. Kiểm tra [Troubleshooting](./README.md#-troubleshooting)
2. Xem [SECURITY.md Troubleshooting](./SECURITY.md#-troubleshooting)

## ✨ Lợi ích

- ✅ **Bảo mật:** Keys không lộ trên GitHub
- ✅ **Tiện lợi:** Code tự detect local vs Cloud
- ✅ **Flexible:** Dễ update keys mà không push code
- ✅ **Standard:** Theo best practices của Streamlit
