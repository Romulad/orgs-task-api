from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

def send_html_email(
    title: str,
    template_name: str, 
    email: str | list[str],
    context: dict | None = None,
    connection=None
):
  mail_to = email
  if isinstance(email, str):
    mail_to = [email]

  body = render_to_string(template_name, context)
  msg = EmailMessage(
    title,
    body,
    None, 
    mail_to,
    connection=connection
  )
  msg.content_subtype = 'html'
  msg.send()


def send_invitation_success_email(
    user_data:list,
    org_name:str
):
  with get_connection() as connection:
    for user in user_data:
      send_html_email(
        _(f"Notification - You have been add to org {org_name}"),
        "mails/add_to_org_invitation.html",
        user.email,
        {"first_name": user.first_name, "org_name": org_name},
        connection
      )