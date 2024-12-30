#!/usr/bin/env python3

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class Decryptor:
    def __init__(self, key):
        self.key = key
        self.cipher = AESGCM(self.key)

    def decrypt(self, message):
        self.__verify_feasibility(message)
        ciphertext = bytes(message.payload())
        system_title = message.system_title()
        frame_counter = message.frame_counter()
        initialization_vector = bytes(system_title + frame_counter)
        # https://github.com/ric-geek/DLMS-APDU-Encrypter-Decrypter/blob/752fcbe016f72b61cd3f3631ef40f4f32ca30d60/main_logic.py#L88
        associated_data = b'0' # 0x30; trust me bro
        # Yes, they use encrypt to decrypt.
        # https://github.com/ric-geek/DLMS-APDU-Encrypter-Decrypter/blob/752fcbe016f72b61cd3f3631ef40f4f32ca30d60/main_logic.py#L102
        return self.cipher.encrypt(
                    nonce=initialization_vector,
                    data=ciphertext,
                    associated_data=associated_data
                )

    def __verify_feasibility(self, message):
        if message.security_control_byte() != 0b00100000: # 0x20 => only the 'encrypted' flag is set
            raise RuntimeError("Currently the code only supports encryption, but no other Security Control Byte configuration.")
