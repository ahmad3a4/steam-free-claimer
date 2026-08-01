# Steam Free Games Claimer

> Maintained by **[ahmad3a4](https://github.com/ahmad3a4)**

Automatically find and claim **free Steam games** — no manual cookie hunting needed. Sign in with your Steam account directly on the web interface or use the CLI tool.

---

## ✨ Features

- 🔐 **Real Steam login** — username + password, no manual cookie extraction
- 🛡️ **Steam Guard supported** — handles both email and mobile authenticator 2FA
- 🔍 **Smart game detection** — scans Steam store for all active 100%-off promotions
- 🎮 **One-click claiming** — adds all free packages directly to your Steam library
- 🌐 **Web interface** — beautiful dark UI anyone can use in a browser
- 💻 **CLI tool** — original terminal version with `--check-only` mode
- 🔒 **Privacy first** — credentials never stored or logged, RSA-encrypted before leaving your machine
- ⏱️ **Rate-limited** — respectful delays between requests

---

## 🌐 Web App (Recommended)

The easiest way to use it. Just run locally and open in your browser.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the web server

```bash
python app.py
```

### 3. Open your browser

```
http://127.0.0.1:5000
```

### 4. Sign in & claim

1. Enter your **Steam username and password**
2. Enter your **Steam Guard code** if prompted (email or mobile authenticator)
3. The app searches Steam automatically
4. Click **"Claim All"** — done! ✅

---

## 💻 CLI Tool

For those who prefer the terminal.

### Setup

```bash
pip install -r requirements.txt
```

### Run

```bash
# Find and claim all free games
python main.py

# Just see what's free right now (no claiming)
python main.py --check-only
```

The first run will ask for your Steam cookies and optionally save them to `.env`:

```
sessionid         > 26688c8a...
steamLoginSecure  > 76561199...
Save to .env? [y/N]: y
```

---

## 🗂️ Project Structure

```
steam-free-claimer/
├── app.py           — Flask web server (login + search + claim APIs)
├── steam_auth.py    — Steam login: RSA encryption, 2FA, token finalization
├── steam_client.py  — Steam store API: find free games, claim packages
├── main.py          — CLI entry point
├── templates/
│   └── index.html   — Web UI
├── static/
│   ├── style.css    — Dark glassmorphism theme
│   └── app.js       — Frontend logic
├── Procfile         — For Railway / Render deployment
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔐 How Login Works (No Data Leaks)

Your credentials go through Steam's **official authentication API** directly:

```
1. Password is RSA-encrypted locally (Steam's public key)
2. Encrypted password is sent to Steam — never in plain text
3. Steam Guard code (if needed) is submitted to Steam directly
4. Steam returns session tokens → exchanged for store cookies
5. Cookies used only for search + claim — then discarded
```

**Nothing is stored on any server.** The Flask server runs locally on your machine. All communication is directly between your machine and Steam's servers.

---

## 🚀 Deploy (Make it Public)

The app is ready for one-click deployment to **Railway** or **Render**:

### Railway (Recommended)

1. Go to [railway.app](https://railway.app)
2. Click **New Project → Deploy from GitHub repo**
3. Select **`ahmad3a4/steam-free-claimer`**
4. Railway auto-detects the `Procfile` and deploys
5. Go to **Settings → Networking → Generate Domain** for your public URL

### Render

1. Go to [render.com](https://render.com)
2. New → Web Service → Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`

---

## 📋 Example Output (CLI)

```
+==================================================+
|  [*]  Steam Free Games Claimer                   |
|       by ahmad3a4 - github.com/ahmad3a4          |
+==================================================+

  [+]  Loaded Steam cookies from .env
  >>   Verifying Steam session...
  [+]  Authenticated successfully!

  >>   Searching Steam for free games...
  [+]  Found 3 free game(s)!

  [ 1/ 3] Some Action Game
  [+]  Claimed!  (sub #123456)

  [ 2/ 3] Another Free RPG
  **   Already in library  (sub #789012)

  [ 3/ 3] Indie Platformer Bundle
  [!]  No free packages found — skipped

  [DONE] All done!
    [+]  Claimed       : 1
    [*]  Already owned : 1
    [>]  Skipped       : 1
```

---

## ❓ FAQ

**Q: Will I get banned?**
A: The tool only claims games Steam makes legitimately free and mimics normal browser behavior. Risk is very low, but no guarantees.

**Q: Is my password safe?**
A: Yes. It's RSA-encrypted on your machine using Steam's own public key before being transmitted — exactly the same as logging into the Steam website normally.

**Q: No free games found — why?**
A: Steam doesn't always have active 100%-off promotions. Try again during a Steam sale or major gaming event.

**Q: Can I schedule it to run automatically?**
A: Yes — use Windows Task Scheduler or a cron job to run `python main.py` daily.

**Q: Does it work with Family Sharing / limited accounts?**
A: It claims packages the same way Steam's own website does, so it should work on any standard account.

---

## 📄 License

[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)
