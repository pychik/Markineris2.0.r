# otp_service.py
import random
import requests

# from logger import logger

SMSRU_API_KEY = 'B59B4F72-C5F5-28F3-9A9B-648C38676936'


class SmsOTP:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate_otp(self):
        """Генерация шестизначного OTP кода."""
        return random.randint(100000, 999999)

    def send_sms(self, phone, code):
        """Отправка SMS с OTP кодом через API SMS.ru."""
        phone = phone.replace('+', '')
        url = 'https://sms.ru/sms/send'
        params = {
            'api_id': self.api_key,
            'to': phone,
            'msg': f'Ваш код подтверждения: {code}',
            'json': 1
        }
        response = requests.get(url, params=params)
        result = response.json()
        print(result)
        # print(result['sms'].get(phone), result['sms'][phone].get('status'))
        if result['sms'].get(phone) and result['sms'][phone].get('status') == 'OK':
            return True
        else:
            # logger.info("Ошибка отправки SMS:", result.get('status_text'))
            print("Ошибка отправки SMS:", result.get('sms'))
            return False

    def verify_otp(self, session_code, user_code):
        """Проверка введенного пользователем OTP кода."""
        return str(session_code) == str(user_code)




# SMSC_LOGIN = 'gendalf2014'         # Ваш логин для smsc.ru
# SMSC_PASSWORD = 'Parol4ik1988343489388'
# class SmsOTP:
#     def __init__(self, login, password):
#         self.login = login
#         self.password = password
#
#     def generate_otp(self):
#         """Генерация шестизначного OTP кода."""
#         return random.randint(100000, 999999)
#
#     def send_sms(self, phone, code):
#         """Отправка SMS с OTP кодом через API smsc.ru."""
#         url = 'https://smsc.ru/sys/send.php'
#         params = {
#             'login': self.login,
#             'psw': self.password,
#             # 'sender': 'markineris',
#             'phones': phone,
#             'mes': f'Ваш код подтверждения: {code}',
#             'fmt': 3  # JSON формат ответа
#         }
#         response = requests.get(url, params=params)
#         result = response.json()
#         print(result)
#         # Проверяем статус отправки
#         if 'id' in result:
#             return True
#         else:
#             print("Ошибка отправки SMS:", result.get('error'))
#             return False
#
#     def verify_otp(self, session_code, user_code):
#         """Проверка введенного пользователем OTP кода."""
#         return str(session_code) == str(user_code)
if __name__ == '__main__':
    sms_service = SmsOTP(SMSRU_API_KEY)
    # sms_service = SmsOTP(SMSC_LOGIN, SMSC_PASSWORD)
    otp_code = sms_service.generate_otp()
    phone = '79213779917'
    res = sms_service.send_sms(phone, otp_code)
    print(f'{otp_code=}')
    print(res)
