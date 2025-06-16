import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'nmirnaa607@gmail.com'
SMTP_PASS = 'kyce wwgj fvxv ojez'

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        print("Письмо успешно отправлено.")
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")

def generation_confirmation_code(length=6):
    return secrets.token_hex(length//2)