# 🔐 Streamlit Secrets Setup Guide

## For Local Development

1. **Create `.env` file** in project root:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   ```

2. **Run dashboard**:
   ```bash
   streamlit run dashboard.py
   ```

---

## For Streamlit Cloud Deployment

1. **Create `.streamlit/secrets.toml`** (this file is gitignored):
   ```toml
   [general]
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_KEY = "your-supabase-anon-key"
   ```

2. **Or use Streamlit Cloud UI**:
   - Go to your app settings
   - Click "Secrets"
   - Paste the TOML content above
   - Click "Save"

---

## Security Notes

⚠️ **NEVER commit these files to git**:
- `.env`
- `.streamlit/secrets.toml`

✅ **These are already in `.gitignore`**:
```
.env
.streamlit/secrets.toml
```

---

## Getting Your Supabase Credentials

1. Go to [supabase.com](https://supabase.com)
2. Open your project
3. Go to Settings → API
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_KEY`

---

## Testing Your Setup

```bash
# Test database connection
python verify_data.py

# Run dashboard
streamlit run dashboard.py
```

If you see "✅ Supabase 연결 성공!", you're all set! 🎉
