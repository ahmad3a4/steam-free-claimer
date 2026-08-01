# Steam Free Games Claimer

> Maintained by **[ahmad3a4](https://github.com/ahmad3a4)**

A Python CLI tool that **automatically finds and claims free games on Steam** — including temporarily free (100% off sale) games. No third-party websites required; talks directly to Steam's own API.

---

## ✨ Features

- 🔍 **Finds free games** — scrapes Steam's search API for all 100%-off promotions
- 🎮 **Claims automatically** — adds free packages directly to your Steam library
- 💾 **Saves your session** — stores cookies in `.env` so you don't retype them
- 📋 **Check-only mode** — list free games without claiming anything (`--check-only`)
- 🎨 **Colored output** — clear, readable terminal UI with progress tracking
- ⏱️ **Rate-limited** — respectful delays between requests

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get your Steam cookies

1. Log into [store.steampowered.com](https://store.steampowered.com) in your browser
2. Press **F12** → **Application** tab → **Cookies** → `https://store.steampowered.com`
3. Copy the values of:
   - `sessionid`
   - `steamLoginSecure`

### 3. (Optional) Create a `.env` file

```bash
cp .env.example .env
# then fill in your cookie values
```

### 4. Run it

```bash
# Find and claim all free games
python main.py

# Just see what's free right now (no claiming)
python main.py --check-only
```

---

## 📋 Example Output

```
╔══════════════════════════════════════════════════╗
║                                                  ║
║  🎮  Steam Free Games Claimer                    ║
║      Automatically claim free Steam games        ║
║                                                  ║
║  by ahmad3a4 · github.com/ahmad3a4               ║
╚══════════════════════════════════════════════════╝

  ✅  Loaded Steam cookies from .env
  🔑  Verifying Steam session...
  ✅  Authenticated successfully!

  🔍  Searching Steam for free games...
  ✅  Found 3 free game(s)!

  ════════════════════════════════════════════════════════

  [ 1/ 3] Some Action Game
  ✅  Claimed!  (sub #123456)

  [ 2/ 3] Another Free RPG
  📚  Already in library  (sub #789012)

  [ 3/ 3] Indie Platformer Bundle
  ⏭   No free packages found (DLC or bundle — skipped)

  ════════════════════════════════════════════════════════

  🎮  All done!

    ✅  Claimed       : 1
    📚  Already owned : 1
    ⏭   Skipped       : 1
```

---

## ⚠️ Notes

- **Your cookies expire** when you log out of Steam. If auth fails, re-copy your cookies.
- The script only claims games that are **genuinely free** at the time of running — it doesn't bypass any paywalls.
- Use responsibly. Add delays if you plan to run this frequently.

---

## ❓ FAQ

**Q: Will I get banned?**  
A: The script mimics normal browser behavior and only claims games Steam makes legitimately free. Risk is very low, but no guarantees.

**Q: Where do I find my cookies?**  
A: F12 → Application → Cookies → store.steampowered.com. See step 2 above.

**Q: The script claims nothing. Why?**  
A: There may simply be no free games at this moment. Try `--check-only` to confirm, then try again later during a Steam sale or event.

**Q: Can I schedule this to run automatically?**  
A: Yes! Use Windows Task Scheduler or a cron job to run `python main.py` daily.

---

## 📄 License

[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)
