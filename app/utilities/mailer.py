from __future__ import print_function

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from config import settings
from logger import logger


class MailSender:
    def __init__(self, user_login_name: str, email: str, subject: str, message: str) -> None:
        self.user_login_name = user_login_name
        self.email = email
        self.subject = subject
        self.message = message
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = settings.MAIL_API_TOKEN

    def send_email(self) -> str:
        # create an instance of the API class
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(self.configuration))
        sender = sib_api_v3_sdk.SendSmtpEmailSender(name=settings.Mail.SENDER_NAME, email=settings.Mail.SENDER_EMAIL)
        send_to = sib_api_v3_sdk.SendSmtpEmailTo(email=self.email, name=self.user_login_name)
        arr_to = [send_to]
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(sender=sender,
                                                       to=arr_to,
                                                       html_content=f"<html><body>"
                                                                    f"<h1 class=\"my-0 mr-md-auto font-weight-normal\">"
                                        f"<span style=\"background-color: #f0ad4e; padding: 4px 8px;text-align: center;"
                                        f"border-radius: 5px;\">&nbspMARKINERIS&nbsp</span></h1>"
                                                                    f"<h2>Здравствуйте {self.user_login_name}</h2>"
                                                                    f"{self.message}</body></html>",
                                                       subject=self.subject)

        try:
            # Send a transactional email
            api_response = api_instance.send_transac_email(send_smtp_email)
            return f"success {api_response}"
        except ApiException as e:
            logger.error(e)
            return f"error {e}"
