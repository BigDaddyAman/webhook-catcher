# Contributing to Webhook Catcher

Thanks for your interest in contributing to **Webhook Catcher** 🎉  
All kinds of contributions are welcome — bug reports, documentation improvements, and code changes.

---

## 🧭 Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch from `main`:
   ```bash
   git checkout -b feature/my-change
   ```

---

## 🛠 Development Setup

### Requirements
- Python 3.9+
- pip
- (Optional) Docker

### Local setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The app will be available at:
```
http://localhost:8000
```

---

## 🧪 Testing Changes

Before opening a PR, please ensure:

- The app starts without errors
- `/healthz` returns `200 OK`
- Webhooks can be received via `/webhook`
- UI pages load correctly

For Railway-related changes, please test:
- Deployment without a volume
- Deployment **with** a volume mounted at `/app/data`

---

## 🧩 Database & Volumes (Important)

Webhook Catcher uses SQLite.

- The database path is `/app/data/webhooks.db`
- On Railway, contributors must manually attach a volume at:
  ```
  /app/data
  ```
- Without a volume, data loss on redeploy is expected

Please do not introduce hardcoded paths outside `/app/data`.

---

## 📦 Pull Request Guidelines

When opening a PR:

- Keep changes focused and small
- Explain **why** the change is needed
- Update documentation if behavior changes
- Reference related issues when applicable

### Good PR titles
- `Fix: handle empty webhook payloads`
- `Docs: clarify Railway volume setup`
- `Feature: protect UI with optional password`

---

## 🧹 Code Style

- Follow existing code patterns
- Prefer readability over cleverness
- Avoid introducing new dependencies unless necessary

---

## 🐞 Reporting Issues

If you find a bug:
- Include steps to reproduce
- Include logs or screenshots if relevant
- Mention your platform (local, Railway, Docker)

---

## 🤝 Code of Conduct

Be respectful and constructive.  
Harassment or toxic behavior will not be tolerated.

---

Thanks again for contributing — every improvement helps 🚀
