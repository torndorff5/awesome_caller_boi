import os
import smtplib
from email.message import EmailMessage

def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_address: str,
    subject: str,
    body: str,
    from_address: str = None
):
    """
    Send a plain‐text email via SMTP.
    """
    from_address = from_address or smtp_user

    msg = EmailMessage()
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)



def middleware(transcript):
    body = transcript.call_text

    # 2) Load SMTP settings (adjust names as needed):
    SMTP_HOST = "smtp.gmail.com"  # e.g. "smtp.gmail.com"
    SMTP_PORT = 587  # usually 587 for TLS
    SMTP_USER = "torndorff5@gmail.com"  # your SMTP username/email
    SMTP_PASS = os.getenv("SMTP_PASS")  # your SMTP password/app‐password

    # 3) Define recipient(s) and subject:
    TO_ADDRESS = "tannercrosbyorndorff@gmail.com"
    SUBJECT = f"New Call Transcript from {transcript.phone_number}"

    # 4) Send the email:
    send_email(
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        smtp_user=SMTP_USER,
        smtp_pass=SMTP_PASS,
        to_address=TO_ADDRESS,
        subject=SUBJECT,
        body=body
    )

    # (Optional) Print or log a confirmation:
    print(f"Sent transcript email for {transcript.phone_number}")