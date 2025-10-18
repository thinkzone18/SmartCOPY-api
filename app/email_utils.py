import os
import requests

def send_license_email(to_email: str, license_key: str):
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("FROM_EMAIL")
    from_name = os.getenv("FROM_NAME", "SmartCOPY")

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "api-key": api_key
    }

    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": "Your SmartCOPY License Key",
        "htmlContent": f"""
            <p>Hello,</p>
            <p>Thank you for purchasing <b>SmartCOPY Pro</b>.</p>
            <p>Your license key is:</p>
            <h2>{license_key}</h2>
            <p>— Team ThinkZone</p>
        """
    }

    r = requests.post(url, headers=headers, json=payload, timeout=15)
    if r.status_code in (200, 201, 202):
        print(f"✅ Brevo email sent to {to_email}")
    else:
        print(f"⚠️ Brevo email failed: {r.status_code} → {r.text}")
