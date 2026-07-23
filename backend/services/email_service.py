"""
Transactional email service.

Strategy:
  - If RESEND_API_KEY is configured we send via Resend.
  - If not, we log the email to stdout. This makes local / staging usable
    even before the user provisions a Resend key, and developers can grab
    the reset link from the backend log.

The service is intentionally minimal — three high-level methods that the
auth flow calls. HTML templates are inline + table-based per Resend's
deliverability guidance.
"""

import os
import asyncio
import logging
from typing import Optional

import resend

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.api_key = os.environ.get("RESEND_API_KEY", "").strip()
        self.from_address = os.environ.get(
            "EMAIL_FROM", "NeoNoble Ramp <noreply@neonoble-ramp.com>"
        )
        self.app_base_url = os.environ.get(
            "APP_BASE_URL", "https://neonoble-ramp.preview.emergentagent.com"
        ).rstrip("/")
        if self.api_key:
            resend.api_key = self.api_key
            logger.info("EmailService: Resend configured.")
        else:
            logger.warning(
                "EmailService: RESEND_API_KEY not set — falling back to console logging."
            )

    @property
    def is_live(self) -> bool:
        return bool(self.api_key)

    async def _send(
        self, to: str, subject: str, html: str, text: Optional[str] = None
    ) -> Optional[str]:
        """Send an email (or log it). Returns the Resend message id, or None."""
        if not self.is_live:
            logger.info(
                "\n========== EMAIL (console fallback) ==========\n"
                f"To:      {to}\n"
                f"From:    {self.from_address}\n"
                f"Subject: {subject}\n"
                f"---\n{text or html}\n"
                "==============================================\n"
            )
            return None

        params = {
            "from": self.from_address,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            params["text"] = text
        try:
            result = await asyncio.to_thread(resend.Emails.send, params)
            email_id = result.get("id") if isinstance(result, dict) else None
            logger.info(f"Email sent: id={email_id} to={to} subject={subject!r}")
            return email_id
        except Exception as e:
            logger.error(f"Resend send failed for {to}: {e}")
            return None

    async def send_welcome(self, to: str) -> Optional[str]:
        action_url = f"{self.app_base_url}/dashboard"
        subject = "Welcome to NeoNoble Ramp"
        text = (
            "Welcome to NeoNoble Ramp.\n\n"
            "Your account is ready. Sign in to get started:\n"
            f"{action_url}\n\n"
            "If you didn't create this account, you can ignore this email."
        )
        html = _wrap_html(
            heading="Welcome to NeoNoble Ramp",
            body_html=(
                "<p>Your account is ready. Sign in to get started:</p>"
                f"<p>{_button(action_url, 'Open Dashboard')}</p>"
                "<p style='color:#777;font-size:13px;margin-top:24px;'>"
                "If you didn't create this account, you can safely ignore this email.</p>"
            ),
        )
        return await self._send(to, subject, html, text)

    async def send_password_reset(self, to: str, reset_token: str) -> Optional[str]:
        action_url = f"{self.app_base_url}/reset-password?token={reset_token}"
        subject = "Reset your NeoNoble Ramp password"
        ttl_hours = os.environ.get("PASSWORD_RESET_TTL_HOURS", "24")
        text = (
            "We received a request to reset your NeoNoble Ramp password.\n\n"
            f"Use this link within {ttl_hours} hours:\n{action_url}\n\n"
            "If you didn't request this, you can ignore this email — your password "
            "won't change."
        )
        html = _wrap_html(
            heading="Reset your password",
            body_html=(
                "<p>We received a request to reset your NeoNoble Ramp password.</p>"
                f"<p>{_button(action_url, 'Reset Password')}</p>"
                f"<p style='color:#777;font-size:13px;'>The link expires in "
                f"{ttl_hours} hours.</p>"
                "<p style='color:#777;font-size:13px;'>If you didn't request this, "
                "you can ignore this email — your password won't change.</p>"
            ),
        )
        return await self._send(to, subject, html, text)


def _wrap_html(heading: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#0f0f1a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#0f0f1a;padding:32px 0;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0"
             style="background:#1a1a2e;border-radius:12px;padding:32px;color:#e6e6ee;
                    font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;">
        <tr><td>
          <h1 style="margin:0 0 16px 0;font-size:22px;color:#a78bfa;">{heading}</h1>
          {body_html}
          <hr style="border:none;border-top:1px solid #2a2a40;margin:24px 0;">
          <p style="margin:0;font-size:12px;color:#666;">
            NeoNoble Ramp · NeoNoble Technology Incorporation Limited
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _button(href: str, label: str) -> str:
    return (
        f'<a href="{href}" style="display:inline-block;background:#7c3aed;color:#fff;'
        'text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:600;'
        f'font-size:14px;">{label}</a>'
    )
