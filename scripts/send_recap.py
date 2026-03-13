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
        - errors: list[str]          (critical: insertion failures)
        - warnings: list[str]        (non-critical: Genius API, week not available)
        - genius_errors: int          (count of Genius API failures)
        - start_time: datetime
        - end_time: datetime
        - already_up_to_date: bool
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("SMTP_EMAIL or SMTP_PASSWORD not set, skipping email.")
        return

    now = report["end_time"]
    duration = report["end_time"] - report["start_time"]
    has_errors = len(report.get("errors", [])) > 0
    genius_errors = report.get("genius_errors", 0)
    warnings = report.get("warnings", [])

    # Status: only ERREUR if critical errors occurred
    if has_errors:
        status = "ERREUR"
    elif report.get("already_up_to_date"):
        status = "Deja a jour"
    else:
        status = "OK"

    subject = f"SNEP Update {now.strftime('%d/%m/%Y')} — {status}"

    lines = []
    lines.append(f"Mise a jour SNEP — {now.strftime('%A %d %B %Y a %H:%M')}")
    lines.append(f"Duree : {duration.total_seconds():.0f}s")
    lines.append("")

    if report.get("already_up_to_date"):
        lines.append("La base de donnees etait deja a jour, aucune insertion.")
    else:
        lines.append(f"Annee : {report['year']}")
        weeks = report.get("weeks_processed", [])
        if weeks:
            lines.append(f"Semaines inserees : {weeks}")
            lines.append(f"Nombre d'entrees inserees : {report.get('total_entries', 0)}")
        else:
            lines.append("Aucune semaine inseree.")

    # Genius enrichment summary
    if genius_errors > 0:
        lines.append("")
        lines.append(f"Enrichissement Genius : {genius_errors} chansons non enrichies (API indisponible)")
        lines.append("  -> Les classements sont bien inseres, seuls les metadata (producteurs, writers) manquent.")

    # Warnings (non-critical)
    if warnings:
        lines.append("")
        lines.append(f"Infos ({len(warnings)}) :")
        for w in warnings[:10]:
            lines.append(f"  - {w}")

    # Critical errors
    lines.append("")
    if has_errors:
        lines.append(f"ERREURS CRITIQUES ({len(report['errors'])}) :")
        for err in report["errors"][:20]:
            lines.append(f"  - {err}")
    else:
        lines.append("Aucune erreur critique.")

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
