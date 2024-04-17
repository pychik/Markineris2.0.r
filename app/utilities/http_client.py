from json import dumps as j_dumps

from requests import Session
from requests.exceptions import ConnectionError, Timeout

from config import settings
from logger import logger


class Requester:
    @staticmethod
    def crm_post(organization_idn: str) -> tuple:

        data = dict(organization_idn=organization_idn)
        with Session() as session:
            headers = dict(so_session_secret=settings.MARKINERIS_SECRET)
            headers.update({'Content-type': 'application/json', 'Accept': 'text/plain'})

            try:
                r = session.post(url=settings.MARKINERIS_CHECK_OI_LINK, headers=headers, data=j_dumps(data),

                                 timeout=settings.Process.TIMEOUT)
            except ConnectionError:
                logger.error(settings.Messages.CONNECTION_MARKINERIS_ERROR)
                return False, settings.Messages.CONNECTION_MARKINERIS_ERROR
            except Timeout:
                logger.error(settings.Messages.CONNECTION_MARKINERIS_ERROR)
                return False, settings.Messages.CONNECTION_MARKINERIS_ERROR
        if r.status_code == 200:
            sended = r.json().get("success")
            mes = r.json().get("message")

        else:
            sended = False
            mes = None
        return sended, mes
