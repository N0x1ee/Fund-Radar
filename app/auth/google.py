"""Google Sign-In — verify the ID token that the browser gets from Google.

How the flow works (no client secret, no redirect dance):

  1. The browser loads Google Identity Services and shows the official
     "Sign in with Google" button, configured with our public Client ID.
  2. The user picks their Google account. Google hands the browser a signed
     JWT called an *ID token* (the "credential").
  3. The browser POSTs that credential to /auth/google.
  4. This module asks Google to validate the signature and decode it, then we
     re-check the claims that actually matter for security.
  5. The route creates (or finds) the matching FundRadar user and issues the
     SAME httpOnly session cookie that password login issues — so every other
     part of the app (bookmarks, /profile, /auth/me) works unchanged.

Why we call Google's tokeninfo endpoint instead of verifying the RSA
signature locally: local verification needs the `cryptography` package and
JWKS key caching. Asking Google is one short HTTPS call, needs no extra
dependency (stdlib urllib only — same approach the Groq provider uses), and
Google is the authority on its own keys. The trade-off is ~100 ms per sign-in,
which is irrelevant here.

SECURITY: verifying the signature is NOT enough on its own. A token signed by
Google but issued for a *different* application would otherwise be accepted —
that is the classic "audience confusion" attack. We therefore check `aud`
against our own Client ID, check the issuer, and require a verified email.
"""
from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

import bcrypt

from app.config import settings

# Google's public endpoint that validates an ID token and returns its claims.
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# The only issuers Google uses for ID tokens.
VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

# Don't let a caller push a giant body at us before we've validated anything.
MAX_CREDENTIAL_CHARS = 8192

_TIMEOUT_SECONDS = 10


class GoogleAuthError(Exception):
    """Raised when a Google credential is missing, malformed, or untrustworthy.

    The route turns this into a 401 with a user-friendly message. The message
    is intentionally vague to the client but specific in the server logs.
    """


def google_enabled() -> bool:
    """True when a Client ID is configured, i.e. the button should be shown.

    Everything Google-related is gated on this, so an unconfigured deployment
    behaves exactly like before this feature existed.
    """
    return bool(settings.google_client_id.strip())


def _fetch_tokeninfo(credential: str) -> dict:
    """Ask Google to validate the ID token and return its decoded claims."""
    url = f"{TOKENINFO_URL}?{urllib.parse.urlencode({'id_token': credential})}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Google returns 400 for expired / tampered / unknown tokens.
        raise GoogleAuthError(f"Google rejected the sign-in token (HTTP {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise GoogleAuthError("Could not reach Google to verify the sign-in.") from exc
    except json.JSONDecodeError as exc:
        raise GoogleAuthError("Google returned an unreadable response.") from exc


def verify_google_credential(credential: str) -> dict:
    """Validate a Google ID token and return the claims we care about.

    Returns a dict with `email`, `full_name` and `google_id`. Raises
    GoogleAuthError for anything we are not completely sure about — when in
    doubt we refuse the sign-in rather than guess.
    """
    if not google_enabled():
        raise GoogleAuthError("Google Sign-In is not configured on this server.")

    credential = (credential or "").strip()
    if not credential:
        raise GoogleAuthError("No Google sign-in token was supplied.")
    if len(credential) > MAX_CREDENTIAL_CHARS:
        raise GoogleAuthError("Google sign-in token is implausibly large.")

    claims = _fetch_tokeninfo(credential)

    if claims.get("error") or claims.get("error_description"):
        raise GoogleAuthError("Google rejected the sign-in token.")

    # --- The audience check: this token must have been minted for US. --------
    expected_audience = settings.google_client_id.strip()
    if claims.get("aud") != expected_audience:
        raise GoogleAuthError("This Google token was issued for a different app.")

    if claims.get("iss") not in VALID_ISSUERS:
        raise GoogleAuthError("Unexpected token issuer.")

    # `sub` is Google's permanent, unique user id. Its absence means this is
    # not a user ID token at all.
    google_id = claims.get("sub")
    if not google_id:
        raise GoogleAuthError("Google token is missing the account identifier.")

    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise GoogleAuthError("This Google account has no email address attached.")

    # tokeninfo returns booleans as the *strings* "true"/"false".
    email_verified = str(claims.get("email_verified", "")).lower() == "true"
    if not email_verified:
        raise GoogleAuthError("This Google account's email address is not verified.")

    full_name = (claims.get("name") or "").strip() or None

    return {"email": email, "full_name": full_name, "google_id": google_id}


def unusable_password_hash() -> str:
    """A valid bcrypt hash of a random secret that nobody knows.

    Google accounts have no FundRadar password, but `users.password_hash` is a
    NOT NULL column. Storing the hash of a throwaway random value keeps the
    schema unchanged (no risky migration before a demo) while making password
    login for this account impossible: `verify_password` can never succeed
    because the plaintext was discarded the moment this function returned.
    """
    random_secret = secrets.token_urlsafe(48).encode("utf-8")[:72]
    return bcrypt.hashpw(random_secret, bcrypt.gensalt()).decode("utf-8")
