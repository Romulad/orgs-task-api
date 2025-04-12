from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send_html_email(
    title: str,
    template_name: str, 
    email: str | list[str],
    context: str | None = None
):
  mail_to = email
  if isinstance(email, str):
    mail_to = [email]

  body = render_to_string(template_name, context)
  msg = EmailMessage(
    title,
    body,
    None, 
    mail_to
  )
  msg.content_subtype = 'html'
  msg.send()
