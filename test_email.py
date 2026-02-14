import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()
print("EMAIL_FROM:", os.getenv("EMAIL_FROM"))
print("OFFICE_EMAIL:", os.getenv("OFFICE_EMAIL"))
print("API KEY starts with:", (os.getenv("SENDGRID_API_KEY") or "")[:3])
print("API KEY length:", len(os.getenv("SENDGRID_API_KEY") or ""))

message = Mail(
    from_email=os.getenv("EMAIL_FROM"),
    to_emails=os.getenv("OFFICE_EMAIL"),
    subject="SendGrid Test",
    html_content="<strong>If you see this, SendGrid works.</strong>",
)

sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
response = sg.send(message)

print("Status:", response.status_code)
print("Body:", response.body)
print("Headers:", response.headers)
