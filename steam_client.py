"""
steam_client.py — Steam HTTP client for Free Games Claimer
Maintained by ahmad3a4 · https://github.com/ahmad3a4/steam-free-claimer
"""

import re
import time
import requests
from bs4 import BeautifulSoup


class SteamClient:
    BASE_URL = "https://store.steampowered.com"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, session_id: str, login_secure: str):
        self.session_id = session_id
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        for name, value in [
            ("sessionid",            session_id),
            ("steamLoginSecure",     login_secure),
            ("wants_mature_content", "1"),
            ("birthtime",            "-2208988800"),
            ("lastagecheckage",      "1-0-2000"),
        ]:
            self.session.cookies.set(name, value, domain=".steampowered.com")

    # ─────────────────────────────────────────────────────────
    # Authentication check
    # ─────────────────────────────────────────────────────────

    def is_authenticated(self) -> bool:
        """Return True if the cookies belong to a logged-in account."""
        try:
            resp = self.session.get(f"{self.BASE_URL}/account/", timeout=10, allow_redirects=False)
            # Logged-in users reach /account/ directly (200).
            # Guests are redirected to the login page (302).
            return resp.status_code == 200
        except requests.RequestException:
            return False

    # ─────────────────────────────────────────────────────────
    # Free game discovery
    # ─────────────────────────────────────────────────────────

    def get_free_games(self) -> list[dict]:
        """
        Fetch all games currently on 100% discount (temporarily free) from
        the Steam store search API.

        Returns a list of dicts: [{"appid": int, "name": str}, ...]
        """
        games = []
        start = 0
        page_size = 50

        while True:
            try:
                resp = self.session.get(
                    f"{self.BASE_URL}/search/results/",
                    params={
                        "maxprice": "free",
                        "specials": 1,
                        "infinite": 1,
                        "count": page_size,
                        "start": start,
                        "cc": "us",
                        "l": "english",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
            except requests.RequestException:
                break

            data = resp.json()
            soup = BeautifulSoup(data.get("results_html", ""), "lxml")

            rows = soup.find_all("a", class_="search_result_row")
            if not rows:
                break

            for row in rows:
                raw_id = row.get("data-ds-appid", "")
                # data-ds-appid can be comma-separated for bundles; take the first
                appid_str = raw_id.split(",")[0].strip()
                title_el = row.find("span", class_="title")
                if appid_str.isdigit() and title_el:
                    games.append({
                        "appid": int(appid_str),
                        "name": title_el.get_text(strip=True),
                    })

            total = data.get("total_count", 0)
            start += page_size
            if start >= total:
                break

            time.sleep(0.5)  # polite rate-limiting

        return games

    # ─────────────────────────────────────────────────────────
    # Package (sub) resolution
    # ─────────────────────────────────────────────────────────

    def get_free_packages(self, appid: int) -> list[int]:
        """
        Return a list of free package (sub) IDs for the given appid.
        A package is considered free if:
          - the 'is_free_license' flag is set, OR
          - the final discounted price is 0 cents.
        """
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/api/appdetails/",
                # NOTE: filters=package_groups is broken on Steam's end — it returns
                # "data": [] instead of {"package_groups": [...]}. Fetch unfiltered.
                params={"appids": appid, "cc": "us", "l": "english"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return []

        app_blob = data.get(str(appid), {})
        if not app_blob.get("success"):
            return []

        app_data = app_blob.get("data", {})
        if not isinstance(app_data, dict):
            return []

        free_pkg_ids = []
        for group in app_data.get("package_groups", []):
            for sub in group.get("subs", []):
                is_free_flag  = sub.get("is_free_license", False)
                price_cents   = sub.get("price_in_cents_with_discount", 1)
                if is_free_flag or price_cents == 0:
                    free_pkg_ids.append(sub["packageid"])

        return free_pkg_ids

    # ─────────────────────────────────────────────────────────
    # Claiming
    # ─────────────────────────────────────────────────────────

    def claim_package(self, sub_id: int) -> tuple[bool, str]:
        """
        Attempt to add a free package to the Steam account.

        This mirrors the exact form the "Add to Account" button submits on a
        live free-game store page: a plain cookie-authenticated POST to
        /freelicense/addfreelicense/ (found by inspecting the real page HTML —
        NOT /checkout/addfreelicense, which is a different, unrelated
        endpoint that just bounces around without ever processing anything).

        Returns (success: bool, message: str).
        Possible messages: "claimed", "already_owned", "error (...)"
        """
        try:
            resp = self.session.post(
                f"{self.BASE_URL}/freelicense/addfreelicense/",
                data={
                    "action":    "add_to_cart",
                    "sessionid": self.session_id,
                    "subid":     sub_id,
                },
                headers={
                    "Referer": f"{self.BASE_URL}/",
                    "Origin":  self.BASE_URL,
                },
                timeout=15,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return False, f"error ({exc})"

        if resp.status_code != 200:
            return False, f"error (HTTP {resp.status_code})"

        body = resp.text

        # Steam's generic error page for a rejected request (e.g. bad/expired
        # session) — shown as a normal 200 page, not a distinct status code.
        if "Site Error" in body or "Oops, sorry" in body:
            return False, "error (Steam rejected the request — session may be expired)"

        # Confirmed by an actual successful claim — Steam's real success page
        # (title "Purchase") contains this exact block:
        #   <h2>Success!</h2>
        #   <div class="add_free_content_success_area">
        #     <h3>{Game} is now registered to your account on Steam.</h3>
        if "add_free_content_success_area" in body:
            return True, "claimed"

        low = body.lower()
        if "already" in low and ("own" in low or "library" in low or "account" in low):
            return False, "already_owned"

        # Unrecognized shape — don't guess either way; surface something
        # diagnosable (the page's own heading, if it has one) instead of a
        # generic message.
        heading_match = re.search(r'<h2[^>]*class="pageheader"[^>]*>(.*?)</h2>', body, re.S)
        snippet = heading_match.group(1).strip() if heading_match else body[:120].replace("\n", " ").strip()
        return False, f"error (unrecognized response: {snippet!r})"
