import base64

import xtea
import warnings

from config import settings

warnings.filterwarnings("ignore")


class Encryptor:

    def __init__(self):
        self.__cipher = xtea.new(settings.ENCRYPT_KEY.encode())
        self.__block_size = 8

    def encrypt_url(self, to_encrypt_data: str) -> str:
        padded_data = self.pad(to_encrypt_data.encode())
        encrypted_data = self.__cipher.encrypt(padded_data)

        return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt_url(self, to_decrypt_data: str) -> str:
        encrypted_data_bytes = base64.urlsafe_b64decode(to_decrypt_data)
        decrypted_data = self.__cipher.decrypt(encrypted_data_bytes)

        unpadded_data = self.unpad(decrypted_data).decode()

        return unpadded_data

    def pad(self, data):
        padding_length = self.__block_size - (len(data) % self.__block_size)
        padded_data = data + bytes([padding_length] * padding_length)

        return padded_data

    def unpad(self, padded_data):
        padding_length = padded_data[-1]

        return padded_data[:-padding_length]


def get_encryptor() -> Encryptor:
    return Encryptor()
