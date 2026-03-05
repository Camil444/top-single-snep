"""
Sends a recap email after the weekly SNEP update.
Uses Gmail SMTP with SMTP_EMAIL and SMTP_PASSWORD env vars.
"""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_recap_email(report: dict):
    """
    Sends a recap email with update results.

    report dict keys:
        - year: int
        - weeks_processed: list[int]
        - total_entries: int
        - errors: list[str]
        - start_time: datetime
        - end_time: datetime
        - already_up_to_date: bool
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("SMTP_EMAIL or SMTP_PASSWORD not set, skipping email.")
        return

    now = report["end_time"]
    duration = report["end_time"] - report["start_time"]
    has_errors = len(report["errors"]) > 0
    status = "ERREURS" if has_errors else "OK"

    subject = f"SNEP Update {now.strftime('%d/%m/%Y')} — {status}"

    # Build body
    lines = []
    lines.append(f"Mise a jour SNEP — {now.strftime('%A %d %B %Y a %H:%M')}")
    lines.append(f"Duree : {duration.total_seconds():.0f}s")
    lines.append("")

    if report["already_up_to_date"]:
        lines.append("La base de donnees etait deja a jour, aucune insertion.")
    else:
        lines.append(f"Annee : {report['year']}")
        lines.append(f"Semaines traitees : {report['weeks_processed']}")
        lines.append(f"Nombre d'entrees inserees : {report['total_entries']}")

    lines.append("")

    if has_errors:
        lines.append(f"ERREURS ({len(report['errors'])}) :")
        for err in report["errors"][:20]:
            lines.append(f"  - {err}")
        if len(report["errors"]) > 20:
            lines.append(f"  ... et {len(report['errors']) - 20} autres erreurs")
    else:
        lines.append("Aucune erreur.")

    body = "\n".join(lines)

    msg = MIMEMultipart()
    msg["From"] = SMTP_EMAIL
    msg["To"] = SMTP_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Recap email sent to {SMTP_EMAIL}")
    except Exception as e:
        logger.error(f"Failed to send recap email: {e}")
