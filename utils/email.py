import logging
import os
from typing import List, Dict, Optional, Union
import sib_api_v3_sdk
from sib_api_v3_sdk import SendSmtpEmail, SendSmtpEmailSender, SendSmtpEmailTo
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


class EmailService:
    """
    Brevo (Sendinblue) email sender.
    Set BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME in env.
    Falls back to logging only if API key missing.
    """

    def __init__(self, sender_email: str, sender_name: str, api_key: Optional[str] = None):
        self.sender_email = sender_email
        self.sender_name = sender_name
        api_key = api_key or os.getenv("BREVO_API_KEY")
        if api_key:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = api_key
            self.api_client = sib_api_v3_sdk.ApiClient(configuration)
            self.transactional_api = sib_api_v3_sdk.TransactionalEmailsApi(self.api_client)
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("BREVO_API_KEY not set; emails will be logged only.")

    def _send(self, to_emails: Union[str, List[str]], subject: str, html_content: str, text_content: Optional[str] = None) -> Dict:
        if isinstance(to_emails, str):
            to_emails = [to_emails]

        if not self.enabled:
            logger.info(f"[EMAIL-LOG-ONLY] To: {to_emails}, Subject: {subject}")
            return {"success": True, "logged": True}

        try:
            recipients = [SendSmtpEmailTo(email=email) for email in to_emails]
            sender = SendSmtpEmailSender(email=self.sender_email, name=self.sender_name)
            email = SendSmtpEmail(
                sender=sender,
                to=recipients,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
            response = self.transactional_api.send_transac_email(email)
            return {"success": True, "message_id": response.message_id}
        except ApiException as e:
            logger.error(f"Brevo API error sending email to {to_emails}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_emails}: {e}")
            return {"success": False, "error": str(e)}

    def send_welcome_email(self, user_email: str, user_name: str, firm_name: str = "", user_password: str = "") -> Dict:
        subject = "Welcome to LegalLink"
        text_body = f"Welcome {user_name}! You can now sign in with {user_email}."
        html_body = f"<p>Welcome <strong>{user_name}</strong>!</p><p>You can now sign in with <strong>{user_email}</strong>.</p>"
        return self._send(user_email, subject, html_body, text_body)

    def send_admin_notification_email(
        self,
        admin_emails: List[str],
        event_type: str,
        user_info: Dict,
        additional_details: Optional[str] = None,
    ) -> Dict:
        subject = f"Admin notification: {event_type}"
        body = f"User info: {user_info}. Details: {additional_details or ''}"
        return self._send(admin_emails, subject, body, body)

    def send_rejection_email(self, user_email: str, reason: Optional[str] = None) -> Dict:
        subject = "LegalLink Registration Update"
        text_body = f"Your registration was rejected. Reason: {reason or 'No reason provided.'}"
        html_body = f"<p>Your registration was rejected.</p><p>Reason: {reason or 'No reason provided.'}</p>"
        return self._send(user_email, subject, html_body, text_body)


def get_email_service(sender_email: str, sender_name: str, api_key: Optional[str] = None) -> EmailService:
    return EmailService(sender_email=sender_email, sender_name=sender_name, api_key=api_key)
