"""
steam_auth.py -- Steam username/password login via the official Steam Auth API
Maintained by ahmad3a4 - https://github.com/ahmad3a4/steam-free-claimer

Flow:
  1. GetPasswordRSAPublicKey  -> encrypt password
  2. BeginAuthSessionViaCredentials -> may need Steam Guard
  3. (optional) UpdateAuthSessionWithSteamGuardCode
  4. PollAuthSessionStatus -> get access_token + refresh_token
  5. finalizelogin -> exchange for store session cookies
"""

import base64
import os
import time
import urllib.parse

import requests
import rsa as rsa_lib


class SteamLoginError(Exception):
    """Raised for login failures with a user-readable message."""


class SteamAuth:
    API   = "https://api.steampowered.com"
    LOGIN = "https://login.steampowered.com"
    STORE = "https://store.steampowered.com"
    UA    = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # Steam Guard confirmation types
    TYPE_NONE   = 1
    TYPE_MOBILE = 2
    TYPE_EMAIL  = 3

    # ── Internal helpers ──────────────────────────────────────────────────

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({"User-Agent": self.UA, "Accept-Language": "en-US,en;q=0.9"})
        return s

    def _get_rsa_key(self, s: requests.Session, username: str) -> dict:
        r = s.get(
            f"{self.API}/IAuthenticationService/GetPasswordRSAPublicKey/v1/",
            params={"account_name": username},
            timeout=10,
        )
        r.raise_for_status()
        resp = r.json().get("response", {})
        if not resp.get("publickey_mod"):
            raise SteamLoginError(
                "Account not found. Double-check your username (not your display name)."
            )
        return resp

    def _encrypt_password(self, password: str, mod_hex: str, exp_hex: str) -> str:
        pub = rsa_lib.PublicKey(int(mod_hex, 16), int(exp_hex, 16))
        encrypted = rsa_lib.encrypt(password.encode("utf-8"), pub)
        return base64.b64encode(encrypted).decode("utf-8")

    # ── Public API ────────────────────────────────────────────────────────

    def begin_login(self, username: str, password: str) -> dict:
        """
        Start the Steam login flow.

        Returns one of:
          {"need_2fa": False, "sessionid": ..., "steamLoginSecure": ...}
          {"need_2fa": True, "type": "email"|"mobile", "code_type": 2|3,
           "client_id": ..., "steamid": ..., "request_id": ...}
        """
        s = self._session()

        # 1. RSA key
        rsa_data = self._get_rsa_key(s, username)
        enc_pw   = self._encrypt_password(
            password, rsa_data["publickey_mod"], rsa_data["publickey_exp"]
        )

        # 2. Begin auth session
        r = s.post(
            f"{self.API}/IAuthenticationService/BeginAuthSessionViaCredentials/v1/",
            data={
                "account_name":         username,
                "encrypted_password":   enc_pw,
                "encryption_timestamp": rsa_data["timestamp"],
                "device_friendly_name": "Steam Free Claimer Web",
                "platform_type":        2,   # WEBUI
                "persistence":          0,   # ephemeral session
            },
            timeout=15,
        )
        r.raise_for_status()
        resp = r.json().get("response", {})

        if not resp or not resp.get("client_id"):
            raise SteamLoginError(
                "Incorrect username or password. Please try again."
            )

        client_id  = str(resp["client_id"])
        steamid    = str(resp["steamid"])
        request_id = resp.get("request_id", "")
        confs      = resp.get("allowed_confirmations", [])

        # Determine 2FA requirement
        need_types = [
            c["confirmation_type"]
            for c in confs
            if c.get("confirmation_type") in (self.TYPE_MOBILE, self.TYPE_EMAIL)
        ]

        if need_types:
            code_type = need_types[0]
            return {
                "need_2fa":  True,
                "type":      "mobile" if code_type == self.TYPE_MOBILE else "email",
                "code_type": code_type,
                "client_id": client_id,
                "steamid":   steamid,
                "request_id": request_id,
            }

        # No 2FA — poll immediately
        return self._poll_and_finalize(s, client_id, request_id)

    def verify_2fa(
        self,
        client_id:  str,
        steamid:    str,
        request_id: str,
        code:       str,
        code_type:  int,
    ) -> dict:
        """
        Submit a Steam Guard code and finalize login.
        Returns {"sessionid": ..., "steamLoginSecure": ...}
        """
        s = self._session()

        r = s.post(
            f"{self.API}/IAuthenticationService/UpdateAuthSessionWithSteamGuardCode/v1/",
            data={
                "client_id": client_id,
                "steamid":   steamid,
                "code":      code.strip().upper(),
                "code_type": code_type,
            },
            timeout=10,
        )
        r.raise_for_status()

        # A non-OK EResult in the body means wrong code
        body = r.json().get("response", {})
        # Steam returns an empty response on success; an error shows up as EResult != 1

        return self._poll_and_finalize(s, client_id, request_id)

    # ── Internal flow ─────────────────────────────────────────────────────

    def _poll_and_finalize(
        self, s: requests.Session, client_id: str, request_id: str
    ) -> dict:
        """Poll until tokens are ready, then exchange them for store cookies."""
        for _ in range(25):
            time.sleep(1.2)
            r = s.post(
                f"{self.API}/IAuthenticationService/PollAuthSessionStatus/v1/",
                data={"client_id": client_id, "request_id": request_id},
                timeout=10,
            )
            poll = r.json().get("response", {})

            if poll.get("refresh_token") and poll.get("access_token"):
                return self._finalize(s, poll)

        raise SteamLoginError("Authentication timed out. Please try again.")

    def _finalize(self, s: requests.Session, poll: dict) -> dict:
        """Call finalizelogin to exchange refresh_token for store session cookies."""
        refresh   = poll["refresh_token"]
        sessionid = os.urandom(12).hex()

        # Finalize — response contains transfer_info with per-subdomain cookie setters
        r = s.post(
            f"{self.LOGIN}/jwt/finalizelogin",
            data={
                "nonce":     refresh,
                "sessionid": sessionid,
                "redir":     f"{self.STORE}/",
            },
            timeout=12,
        )
        finalize = r.json()

        # POST to each transfer URL to set cookies on the respective Steam domains
        for item in finalize.get("transfer_info", []):
            url    = item.get("url", "")
            params = dict(item.get("params", {}))
            params["sessionid"] = sessionid
            try:
                s.post(url, data=params, timeout=10)
            except Exception:
                pass

        # Extract cookies from the session
        login_secure  = None
        final_session = sessionid

        for ck in s.cookies:
            if ck.name == "steamLoginSecure":
                login_secure = ck.value
            elif ck.name == "sessionid" and "steampowered.com" in (ck.domain or ""):
                final_session = ck.value

        # Fallback: build steamLoginSecure from JWT access token
        if not login_secure:
            steam_id    = finalize.get("steamID", "")
            access_tok  = poll.get("access_token", "")
            if steam_id and access_tok:
                login_secure = urllib.parse.quote(
                    f"{steam_id}||{access_tok}", safe=""
                )

        if not login_secure:
            raise SteamLoginError(
                "Login succeeded but session cookie extraction failed. "
                "Please use the manual cookie method instead."
            )

        return {
            "sessionid":       final_session,
            "steamLoginSecure": login_secure,
        }
