# InternSafe — Verify Before You Apply

A Streamlit prototype with:
- Student Portal: submit internship offer verification requests
- Placement Cell Portal: college-specific officer login and request review
- Admin Portal: register multiple colleges and create officer accounts
- Track Request: student reference + email status lookup
- Smart Scan: rule-based caution indicators
- Dashboard and About & Safety

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Demo admin access
Default demo password: `InternSafeDemo2026!`

Before public deployment, set `ADMIN_PASSWORD` in Streamlit Secrets and change/remove the demo fallback in `app.py`. Use dummy data only for this prototype.

## Important limitations
This prototype uses local SQLite storage. Local app storage may not be durable on hosted platforms. For production, migrate to managed PostgreSQL, configure backups, secure secrets, audit logging, and proper authentication. Email notifications are not configured. Smart Scan is a basic checklist, not a fraud detection model.
