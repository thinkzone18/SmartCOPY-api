import smtplib
from email.message import EmailMessage
from .config import settings

def send_license_email(recipient: str, license_key: str):
    """Send license key email to customer."""
    msg = EmailMessage()
    msg["Subject"] = "Your SmartCOPY License Key"
    msg["From"] = f"{settings.EMAIL_SENDER_NAME} <{settings.SMTP_USER}>"
    msg["To"] = recipient

    msg.set_content(f"""
Hello,

Thank you for purchasing SmartCOPY!

Your license key:
    {license_key}

License validity: 1 year from activation.

If you need help on activating SmartCOPY, refer to the README or contact us at admin@thinkzone18.com.

Best regards,
ThinkZone Support Team
""")

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
            smtp.send_message(msg)
            print(f"✅ License email sent to {recipient}")
    except Exception as e:
        print(f"❌ Error sending email to {recipient}: {e}")
