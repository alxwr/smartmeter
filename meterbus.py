#!/usr/bin/env python3

# Documentation:
# https://en.wikipedia.org/wiki/Meter-Bus#Data_link_protocol
# https://m-bus.com/documentation-wired/05-data-link-layer

import sys
import time

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Deals with the M-Bus Data Link Layer
class FrameReader:
    def __init__(self, serial_connection):
        self.serial_connection = serial_connection

    # Reading 1024 bytes with a 4s timeout works reasonably well.
    #def frames(self):
    #    while True:
    #        data = self.serial_connection.read(1024)
    #        print(data.hex(), flush=True)
    #        print('---', flush=True)


    def frames(self):
        window = bytearray(b"\x00\x00\x00\x00")
        while True:
            # Search for header
            data = self.serial_connection.read(1)
            if len(data) == 0:
                continue
            window.append(data[0])
            del window[0]
            # Is it a long frame?
            if window[0] == 0x68 and window[3] == 0x68 and window[1] == window[2]:
                # Deconstruct the byte stream
                frame_length = window[1]
                control = self.serial_connection.read(1)[0]
                address = self.serial_connection.read(1)[0]
                payload = self.serial_connection.read(frame_length-2)
                checksum = self.serial_connection.read(1)[0]
                mbus_stop = self.serial_connection.read(1)[0]
                # Debugging
                #print(f"{window.hex()}|{control:x}|{address:x}|{payload.hex()}|{checksum:x}|{mbus_stop:x}")
                #print(f"frame length: {frame_length}")
                #print(f"frame payload length: {len(payload)}")
                # Stopbyte check
                if mbus_stop != 0x16:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    eprint(f"Unexpected M-Bus stop: {mbus_stop.hex()}; skipped frame", flush=True)
                    continue
                # Checksum check
                calculated_checksum = sum([
                        control,
                        address,
                        sum(payload)
                     ]) & 0xff
                if calculated_checksum != checksum:
                    eprint(f"Checksum mismatch; skipped frame", flush=True)
                    continue
                # Build the frame and yield it
                yield LongFrame(
                            frame_length=frame_length,
                            control=control,
                            address=address,
                            payload=payload,
                            checksum=checksum
                        )
            else:
                # This covers invalid data as well as ignored frame types
                continue

class LongFrame:
    def __init__(self, frame_length, control, address, payload, checksum):
        self.frame_length = frame_length
        self.control = control
        self.address = address
        self.payload = payload
        self.checksum = checksum

# Deals with the M-Bus Transport Layer
class MessageReader:
    def __init__(self, serial_connection):
        self.serial_connection = serial_connection

    def messages(self):
        message = None
        expected_sequence_number = 0
        for frame in FrameReader(self.serial_connection).frames():
            seq = self.__sequence_number(frame)
            if expected_sequence_number != seq:
                eprint(f"Unexpected sequence number; expected: {expected_sequence_number}; actual: {seq}; skipping message")
                continue
            if message == None:
                if seq == 0:
                    message = Message(
                                stsap=frame.payload[1],
                                dtsap=frame.payload[2],
                                data=frame.payload[3:]
                            )
            else:
                message.append(frame.payload[3:])
            expected_sequence_number += 1
            if self.__is_last_frame(frame):
                yield message
                message = None
                expected_sequence_number = 0

    def __control_info(self, frame):
        return frame.payload[0]

    def __is_last_frame(self, frame):
        return self.__control_info(frame) & 0b00010000 != 0 # check whether the FIN flag is set

    def __sequence_number(self, frame):
        return self.__control_info(frame) & 0b00001111 # extract the sequence number

class Message:
    def __init__(self, stsap, dtsap, data):
        self.stsap = stsap
        self.dtsap = dtsap
        self.data = bytearray(b'')
        self.append(data)

    def append(self, data):
        self.data.extend(bytearray(data))

    def ciphering_service(self):
        return self.data[0]

    def system_title_length(self):
        return self.data[1]

    def system_title(self):
        return self.data[2:self.length_offset()]

    def length_offset(self):
        return 2+self.system_title_length()

    def length_byte_count(self):
        first_byte = self.data[self.length_offset()]
        if first_byte > 0x7f: #127
            # If the most significant bit is 1, the length field will consist
            # of a number of bytes denoted in the remaining seven bits.
            number_of_bytes_to_come = first_byte & 0x7f
            return 1+number_of_bytes_to_come
        else:
            return 1

    def length(self):
        offset = self.length_offset()
        byte_count = self.length_byte_count()
        if byte_count == 1:
            return self.data[offset]
        else:
            return int.from_bytes(self.data[offset+1:offset+byte_count])

    def security_control_byte_offset(self):
        return self.length_offset() + self.length_byte_count()

    def security_control_byte(self):
        return self.data[self.security_control_byte_offset()]

    def frame_counter(self):
        offset = self.security_control_byte_offset() + 1
        counter_bytes = self.data[offset:offset+4]
        return counter_bytes

    def payload(self):
        start = self.security_control_byte_offset() + 5
        end = self.security_control_byte_offset() + self.length()
        return self.data[start:end]
