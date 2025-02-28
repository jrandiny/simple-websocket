import os
from enum import Enum

HOST = '0.0.0.0'
PORT = int(os.getenv('PORT', 9004))
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
SOURCE_FILE = 'data.zip'
MAX_PAYLOAD_FRAME_CONTROL = 125
MAX_PAYLOAD_FIRST_ORDER = (2**16) - 1
MAX_PAYLOAD_SECOND_ORDER = (2**64) - 1

MAX_MESSAGE_SIZE_ALLOWED = 17000000


class WSOpcodeType(Enum):
    CONTINOUS = 0x0
    TEXT = 0x1
    BIN = 0x2
    PING = 0x9
    PONG = 0xA
    CLOSE = 0x8