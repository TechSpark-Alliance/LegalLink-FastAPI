"""Example script showing how to send transactional emails"""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "user@example.com")
SMTP_PASS = os.getenv("SMTP_PASS", "change-me")


def send_test_email(recipient: str, subject: str, body: str) -> None:
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = SMTP_USER
    message["To"] = recipient

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [recipient], message.as_string())


if __name__ == "__main__":
    send_test_email("developer@example.com", "LegalLink Test Email", "Hello from LegalLink FastAPI!")
