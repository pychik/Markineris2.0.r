from typing import Optional

from requests import post

from config import settings


class IdnGetter:

    @staticmethod
    def get_company(idn: str) -> tuple[int, Optional[list]]:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Token {settings.DADATA_TOKEN}',
        }
        json_data = {
            'query': idn,
        }

        response = post(url=settings.DADATA_INFO_IDN_LINK, headers=headers, json=json_data)

        result_status = 1
        if response.status_code == 200:
            sug_list = response.json().get("suggestions")

            result_status, answer_list = IdnGetter.idn_parse(sug_list=sug_list)
        else:
            answer_list = ['', ]
        return result_status, answer_list

    @staticmethod
    def idn_parse(sug_list: list) -> tuple[int, Optional[list]]:
        result_status = 2
        answer_list = []
        if sug_list:
            res_list = list(
                map(lambda x: x.get("data") if x.get("data").get("state").get("status") == "ACTIVE" else None, sug_list))

            if res_list and len(res_list) != 0 and res_list[0]:
                data_dict = res_list[0]

                # use dict.get(<key>) or settings.default_value because we already get key in our dictionary
                answer_list = [data_dict.get("opf").get("short") or settings.NO_VALUE,
                               data_dict.get("name").get("full") or settings.NO_VALUE,
                               data_dict.get("inn") or settings.NO_VALUE, data_dict.get("okpo") or settings.NO_VALUE,
                               data_dict.get("okato") or settings.NO_VALUE,
                               data_dict.get("oktmo") or settings.NO_VALUE,
                               data_dict.get("okved") or settings.NO_VALUE, ]
                result_status = 5

        return result_status, answer_list
