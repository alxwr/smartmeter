#!/usr/bin/env python3

import binascii
import os
import serial
import sys
import time
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator

import evn_crypto
from evn_prometheus_adapter import ElementTreeToPrometheusAdapter
import meterbus

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

SERIAL_PORT = "/dev/ttyAMA0"
BAUDRATE = 2400
INSTRUMENT = "smartmeter"
INSTRUMENT_HUMAN_NAME = "Smartmeter"
INSTRUMENT_TYPE = 'T210-D'
KEYFILE = '/opt/smartmeter/keyfile'

with open(KEYFILE, "rb") as file:
    DECRYPTION_KEY = binascii.unhexlify(file.read().strip())

TARGET_DIR = "/var/lib/prometheus/node-exporter"
if not os.path.isdir(TARGET_DIR):
    sys.stderr.write("{} is not present, using /tmp\n".format(TARGET_DIR))
    TARGET_DIR = "/tmp"
TMP_FILE = "{}/smartmeter.prom.$$".format(TARGET_DIR)
METRICS_FILE = "{}/smartmeter.prom".format(TARGET_DIR)


translator = GXDLMSTranslator()

ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        rtscts=False,
        dsrdtr=False,
        xonxoff=False
)

decryptor = evn_crypto.Decryptor(DECRYPTION_KEY)


def main():
    for message in meterbus.MessageReader(ser).messages():
        #print(message)
        #print(message.data.hex())
        #print(f"ciphering service: {message.ciphering_service():x}")
        #print(f"system title: {message.system_title().hex()}")
        #print(f"length byte count: {message.length_byte_count()}")
        #print(f"length: {message.length()}")
        #print(f"frame counter: {message.frame_counter().hex()}")
        #print(f"security control: {message.security_control_byte():x}")
        #print(f"payload: {message.payload().hex()}")
        #print(f"payload len: {len(message.payload())}")
        try:
            ciphertext = message.payload()
            plaintext = decryptor.decrypt(message)
            #print(f"plaintext: {plaintext.hex()}")
            xml = translator.pduToXml(plaintext)
            adapter = ElementTreeToPrometheusAdapter(
                instrument=INSTRUMENT,
                instrument_human_name=INSTRUMENT_HUMAN_NAME,
                instrument_type=INSTRUMENT_TYPE,
                xml=xml
            )
            with open(TMP_FILE, mode="w", encoding="utf-8") as tmp_file:
                tmp_file.write(adapter.prometheus_format())
            os.rename(TMP_FILE, METRICS_FILE)
        except Exception as error:
            # Make sure we don't show obsolete metrics
            try:
                os.remove(METRICS_FILE)
            except FileNotFoundError:
                pass
            raise error


if __name__ == "__main__":
    main()
