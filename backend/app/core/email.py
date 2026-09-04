import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def send_password_reset_email(to_email: str, reset_token: str):
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px;">
      <div style="max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px;">
        <h2 style="color: #6366f1; margin-bottom: 8px;">🔑 Parolni tiklash</h2>
        <p style="color: #94a3b8;">Parolingizni tiklash uchun quyidagi tugmani bosing:</p>
        <a href="{reset_url}"
           style="display: inline-block; margin: 24px 0; padding: 14px 28px;
                  background: linear-gradient(135deg, #6366f1, #8b5cf6);
                  color: white; text-decoration: none; border-radius: 8px;
                  font-weight: bold; font-size: 16px;">
          Parolni tiklash
        </a>
        <p style="color: #64748b; font-size: 13px;">
          Bu havola 30 daqiqa davomida amal qiladi.<br>
          Agar siz so'rov yubormagan bo'lsangiz, bu xatni e'tiborsiz qoldiring.
        </p>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Parolni tiklash — Python Challenge"
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
    except Exception as e:
        # Development da email yuborilmasa ham davom etadi, token consolega chiqadi
        print(f"[EMAIL ERROR] {e}")
        print(f"[DEV] Reset URL: {reset_url}")
