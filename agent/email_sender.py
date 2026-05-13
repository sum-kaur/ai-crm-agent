"""SMTP email sender using Python's built-in smtplib — no third-party service needed.

Works with Gmail App Passwords, Outlook, or any SMTP provider.

Gmail setup (2 minutes):
  1. Enable 2-Step Verification: myaccount.google.com/security
  2. Create an App Password:     myaccount.google.com/apppasswords
  3. Use that 16-char password as SMTP_PASSWORD in your .env

Set in .env:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=you@gmail.com
  SMTP_PASSWORD=xxxx xxxx xxxx xxxx
  SMTP_FROM_NAME=Alex
"""
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import agent.storage as storage


@dataclass
class SMTPConfig:
    host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    from_name: str = field(default_factory=lambda: os.getenv("SMTP_FROM_NAME", "Alex"))

    def is_configured(self) -> bool:
        return bool(self.user and self.password)


class EmailSender:
    def __init__(self, config: SMTPConfig):
        self.config = config

    def test_connection(self) -> tuple[bool, str]:
        """Verify SMTP credentials without sending anything."""
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(self.config.host, self.config.port, timeout=10) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.login(self.config.user, self.config.password)
            return True, "Connection successful."
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed — check email and App Password."
        except Exception as exc:
            return False, str(exc)

    def send_one(self, to_email: str, subject: str, body: str) -> None:
        """Send a single plain-text email."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.from_name} <{self.config.user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP(self.config.host, self.config.port, timeout=30) as srv:
            srv.ehlo()
            srv.starttls(context=ctx)
            srv.login(self.config.user, self.config.password)
            srv.sendmail(self.config.user, to_email, msg.as_string())

    def send_all(self, dry_run: bool = False) -> dict:
        """Send all unsent staged emails. Returns a result summary dict."""
        emails_df = storage.get_unsent_emails()
        results: dict = {
            "total": len(emails_df),
            "sent": 0,
            "failed": 0,
            "errors": [],
            "dry_run": dry_run,
        }

        for _, row in emails_df.iterrows():
            if dry_run:
                results["sent"] += 1
                continue
            try:
                self.send_one(row["contact_email"], row["subject"], row["body"])
                storage.mark_email_sent(int(row["id"]))
                storage.update_contact_status(int(row["contact_id"]), "contacted")
                results["sent"] += 1
            except Exception as exc:
                results["failed"] += 1
                results["errors"].append(f"{row['contact_email']}: {exc}")

        return results
