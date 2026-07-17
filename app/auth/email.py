"""Email sending for account verification, via the Resend API.

Uses only the standard library (urllib) so there is no extra dependency to
install on the web host. Verification is considered ENABLED only when
`settings.resend_api_key` is set; otherwise `verification_enabled()` returns
False and callers skip sending (and skip blocking login), so the app runs fine
with no email provider configured.

Set up (see EMAIL_VERIFICATION_SETUP.md):
  RESEND_API_KEY=re_xxx          # from https://resend.com
  EMAIL_FROM=FundRadar <onboarding@resend.dev>   # or your verified domain
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.config import settings

log = logging.getLogger("fundradar.email")

RESEND_URL = "https://api.resend.com/emails"


def verification_enabled() -> bool:
    """True only when an email provider is configured."""
    return bool(settings.resend_api_key)


def _send(to: str, subject: str, html: str) -> bool:
    """POST one email to Resend. Returns True on success, False on failure."""
    if not verification_enabled():
        return False
    payload = json.dumps({
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode()
    req = urllib.request.Request(
        RESEND_URL, data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {settings.resend_api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        log.warning("Resend HTTP %s: %s", e.code, e.read()[:300])
    except Exception as e:  # noqa: BLE001 — never let email failure crash a request
        log.warning("Resend send failed: %s", e)
    return False


def send_verification_email(to: str, name: str | None, verify_url: str) -> bool:
    """Send the 'confirm your email' message with the verification link."""
    greeting = f"Hi {name}," if name else "Hi,"
    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:auto;color:#0f2540">
      <h2 style="color:#2563eb;margin:0 0 8px">Confirm your email</h2>
      <p>{greeting}</p>
      <p>Thanks for signing up for <b>FundRadar</b>. Please confirm your email
         address to activate your account.</p>
      <p style="margin:24px 0">
        <a href="{verify_url}"
           style="background:#2563eb;color:#fff;text-decoration:none;
                  padding:12px 22px;border-radius:9px;font-weight:700;display:inline-block">
          Verify my email
        </a>
      </p>
      <p style="color:#64798f;font-size:13px">
        Or paste this link into your browser:<br>
        <a href="{verify_url}">{verify_url}</a>
      </p>
      <p style="color:#64798f;font-size:13px">This link expires in 24 hours.
         If you didn't create this account, you can ignore this email.</p>
    </div>
    """
    return _send(to, "Verify your FundRadar email", html)
