"""
main.py -- Steam Free Games Claimer - Entry Point
Maintained by ahmad3a4 - https://github.com/ahmad3a4/steam-free-claimer

Usage:
    python main.py               # Find and claim all free games
    python main.py --check-only  # List free games without claiming
"""

import os
import sys
import time
import io

# Force UTF-8 output on Windows so box-drawing chars print correctly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from colorama import init, Fore, Style

init(autoreset=True)
load_dotenv()

# ─────────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────────

CYAN   = Fore.CYAN
GREEN  = Fore.GREEN
YELLOW = Fore.YELLOW
RED    = Fore.RED
WHITE  = Fore.WHITE
DIM    = Style.DIM
RESET  = Style.RESET_ALL

BANNER = f"""
{CYAN}+==================================================+
|                                                  |
|  {GREEN}[*]  Steam Free Games Claimer{CYAN}                    |
|  {WHITE}     Automatically claim free Steam games{CYAN}        |
|                                                  |
|  {DIM}by ahmad3a4 - github.com/ahmad3a4{CYAN}              |
+==================================================+{RESET}
"""

def print_banner() -> None:
    print(BANNER)


def divider(char: str = "─", width: int = 56, color: str = YELLOW) -> str:
    return f"{color}{char * width}{RESET}"


def status(msg: str, icon: str = "•") -> None:
    print(f"  {CYAN}{icon}{RESET}  {WHITE}{msg}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}[+]{RESET}  {WHITE}{msg}{RESET}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}[!]{RESET}  {WHITE}{msg}{RESET}")


def err(msg: str) -> None:
    print(f"  {RED}[-]{RESET}  {WHITE}{msg}{RESET}")


# ─────────────────────────────────────────────────────────────────
# Cookie / credential helpers
# ─────────────────────────────────────────────────────────────────

def _how_to_get_cookies() -> None:
    print(f"\n{YELLOW}  How to get your Steam cookies:{RESET}")
    print(f"    1. Open {CYAN}store.steampowered.com{RESET} and log in")
    print(f"    2. Press {CYAN}F12{RESET} → {CYAN}Application{RESET} tab → {CYAN}Cookies{RESET}")
    print(f"       → {CYAN}https://store.steampowered.com{RESET}")
    print(f"    3. Copy the values of:")
    print(f"       • {YELLOW}sessionid{RESET}")
    print(f"       • {YELLOW}steamLoginSecure{RESET}")
    print()


def get_credentials() -> tuple[str, str]:
    """Return (session_id, login_secure) from .env or interactive prompt."""
    session_id   = os.getenv("STEAM_SESSION_ID", "").strip()
    login_secure = os.getenv("STEAM_LOGIN_SECURE", "").strip()

    if session_id and login_secure:
        ok("Loaded Steam cookies from .env")
        return session_id, login_secure

    warn("Steam cookies not found in .env")
    _how_to_get_cookies()

    session_id   = input(f"  {CYAN}sessionid        >{RESET} ").strip()
    login_secure = input(f"  {CYAN}steamLoginSecure >{RESET} ").strip()

    if not session_id or not login_secure:
        err("Both cookies are required. Exiting.")
        sys.exit(1)

    save = input(f"\n  {YELLOW}Save to .env for next time? [y/N]:{RESET} ").strip().lower()
    if save == "y":
        with open(".env", "w") as fh:
            fh.write(f"STEAM_SESSION_ID={session_id}\n")
            fh.write(f"STEAM_LOGIN_SECURE={login_secure}\n")
        ok("Saved to .env")

    return session_id, login_secure


# ─────────────────────────────────────────────────────────────────
# Check-only mode
# ─────────────────────────────────────────────────────────────────

def print_games_table(games: list[dict]) -> None:
    col_w = 46
    print(divider())
    print(f"  {YELLOW}{'Game Name':<{col_w}} {'App ID':>8}{RESET}")
    print(divider())
    for g in games:
        name = g["name"][:col_w - 1]
        print(f"  {WHITE}{name:<{col_w}}{RESET} {CYAN}{g['appid']:>8}{RESET}")
    print(divider())
    print(f"\n  {WHITE}Run without {CYAN}--check-only{RESET} to claim all of them.")


# ─────────────────────────────────────────────────────────────────
# Main flow
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    print_banner()

    check_only = "--check-only" in sys.argv

    # ── Credentials ──────────────────────────────────────────────
    session_id, login_secure = get_credentials()

    from steam_client import SteamClient
    client = SteamClient(session_id, login_secure)

    # ── Auth check ───────────────────────────────────────────────
    print()
    status("Verifying Steam session...", ">>")
    if not client.is_authenticated():
        err("Authentication failed. Your cookies may be expired or invalid.")
        err("Log out and back in to Steam, then copy fresh cookies.")
        sys.exit(1)
    ok("Authenticated successfully!")

    # ── Game discovery ───────────────────────────────────────────
    print()
    status("Searching Steam for free games...", ">>")
    games = client.get_free_games()

    if not games:
        warn("No free games found right now. Try again later!")
        sys.exit(0)

    print()
    ok(f"Found {GREEN}{len(games)}{RESET} free game(s)!")

    if check_only:
        print()
        print_games_table(games)
        return

    # ── Claiming ─────────────────────────────────────────────────
    print()
    print(divider("═"))
    claimed = already_owned = skipped = failed = 0

    for idx, game in enumerate(games, 1):
        label = f"[{idx:>2}/{len(games)}]"
        name  = game["name"][:40]
        print(f"\n  {DIM}{label}{RESET} {WHITE}{name}{RESET}")

        packages = client.get_free_packages(game["appid"])

        if not packages:
            warn("No free packages found (DLC or bundle — skipped)")
            skipped += 1
            time.sleep(0.3)
            continue

        for pkg_id in packages:
            time.sleep(1.2)  # be respectful to Steam's servers
            success, msg = client.claim_package(pkg_id)

            if success:
                ok(f"Claimed!  (sub #{pkg_id})")
                claimed += 1
            elif msg == "already_owned":
                status(f"Already in library  (sub #{pkg_id})", "**")
                already_owned += 1
            else:
                err(f"Could not claim  (sub #{pkg_id}  —  {msg})")
                failed += 1

    # ── Summary ──────────────────────────────────────────────────
    print()
    print(divider("═"))
    print(f"\n  {GREEN}[DONE] All done!{RESET}\n")
    print(f"    {GREEN}[+]  Claimed       : {claimed}{RESET}")
    print(f"    {CYAN}[*]  Already owned : {already_owned}{RESET}")
    print(f"    {YELLOW}[>]  Skipped       : {skipped}{RESET}")
    if failed:
        print(f"    {RED}[-]  Failed        : {failed}{RESET}")
    print()
    print(f"  {WHITE}Open your Steam library to see new additions!{RESET}")
    print(divider("═"))


if __name__ == "__main__":
    main()
