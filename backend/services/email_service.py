
import os
import smtplib
from pathlib import Path
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def send_verification_otp(email: str, otp: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM_EMAIL", username).strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not all([host, username, password, sender]):
        if os.getenv("APP_ENV", "development").lower() != "production":
            print(f"[DEV ONLY] Verification OTP for {email}: {otp}")
            return True
        return False

    message = EmailMessage()
    message["Subject"] = "Verify your MedFlow AI account"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Your MedFlow AI verification code is {otp}.\n\n"
        "This code expires in 5 minutes. If you did not create this account, "
        "you can ignore this email."
    )

 
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()

            server.login(username, password)
            server.send_message(message)

        print(f"Verification email sent successfully to {email}")
        return True

    except (OSError, smtplib.SMTPException) as exc:
        print(
            f"Verification email delivery failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return False
   