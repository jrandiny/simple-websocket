from constant import *
from http_util import *
from dataclasses import dataclass
from typing import Dict
from base64 import b64encode
from hashlib import sha1, md5
import socketserver
import re


@dataclass()
class WSFrame():
    fin: bool
    opcode: WSOpcodeType
    mask: bool
    length: int
    maskingKey: int
    data: bytearray
    raw_data: bytearray
    data_length: int


class WSUtils():
    @staticmethod
    def getAcceptKey(webSocketKey: bytes) -> str:
        raw = str.encode(webSocketKey + GUID)
        webSocketAccept = b64encode(sha1(raw).digest())
        return webSocketAccept.decode()

    @staticmethod
    def generateHandshakeReply(request: HTTPRequest) -> bytes:
        key = WSUtils.getAcceptKey(request.header['sec-websocket-key'])
        response = []
        response.append("HTTP/1.1 101 Switching Protocols")
        response.append("Upgrade: websocket")
        response.append("Connection: Upgrade")
        response.append("Sec-WebSocket-Accept: {}".format(key))

        if 'sec-websocket-version' in request.header:
            version = request.header['sec-websocket-version'].split(', ')[0]
            response.append("Sec-WebSocket-Version: {}".format(version))

        if 'sec-websocket-protocol' in request.header:
            protocol = request.header['sec-websocket-protocol'].split(', ')[0]
            response.append('Sec-WebSocket-Protocol: {}'.format(protocol))
        response.append('')
        response.append('')

        return ('\r\n'.join(response)).encode()

    @staticmethod
    def parseMaskPayloadLen(mask: bool, length: int):
        payload_length = 0
        temp_byte = b''
        if (length <= MAX_PAYLOAD_FRAME_CONTROL):
            payload_length = length
        elif (length <= MAX_PAYLOAD_FIRST_ORDER):
            payload_length = 126
            temp_byte = length.to_bytes(2, byteorder='big')
        elif (length <= MAX_PAYLOAD_SECOND_ORDER):
            payload_length = 127
            temp_byte = length.to_bytes(8, byteorder='big')
        else:
            raise Exception("Data too long!")
        masking = (1 if mask else 0) << 7 | payload_length

        ret = bytearray()
        ret.append(masking)
        ret += temp_byte
        return ret

    @staticmethod
    def generatePayload(opcode: WSOpcodeType, data: bytearray, fin: bool = True):
        ws_frame = WSFrame
        ws_frame.fin = fin
        ws_frame.opcode = opcode
        ws_frame.mask = False
        ws_frame.length = len(data)
        ws_frame.maskingKey = 0
        ws_frame.data = data
        return ws_frame

    @staticmethod
    def generateFrame(ws_frame: WSFrame) -> bytearray:
        sentFrame = bytearray()
        fin = 1 if ws_frame.fin else 0
        sentFrame.append(fin << 7 | ws_frame.opcode.value)
        sentFrame += WSUtils.parseMaskPayloadLen(ws_frame.mask, ws_frame.length)

        if (ws_frame.mask):
            mask = ws_frame.maskingKey.to_bytes(4, 'big')
            sentFrame += mask

        sentFrame += ws_frame.data
        return sentFrame

    @staticmethod
    def parseFrame(frame: bytes) -> WSFrame:
        fin = bool(frame[0] & 0x80)
        opcode = WSOpcodeType(frame[0] & 0xF)
        mask = bool(frame[1] & 0x80)
        payload_len = frame[1] & 0x7F

        length = payload_len
        current_bytes = 1

        if payload_len == 126:
            length = int.from_bytes(frame[2:4], byteorder='big')
            current_bytes = 3
        elif payload_len == 127:
            length = int.from_bytes(frame[2:10], byteorder='big')
            current_bytes = 9

        masking_key = bytearray()

        if (mask):
            masking_key = frame[current_bytes + 1:current_bytes + 5]
            current_bytes += 4

            data_length = len(frame) - current_bytes - 1

            if (data_length >= length):
                data = frame[current_bytes + 1:]

                decoded_data = bytearray()

                for i in range(0, len(data)):
                    decoded_data.append(data[i] ^ masking_key[i % 4])
            else:
                data = bytearray()
                decoded_data = bytearray()
        else:
            data = frame[current_bytes + 1:]
            decoded_data = data

        return WSFrame(fin, opcode, mask, length, masking_key, decoded_data, data, data_length)


class WSHandler(socketserver.BaseRequestHandler):
    def handle(self):

        recv_data = self.request.recv(1024)
        # print(recv_data)

        http_request = HTTPUtils.parseRequest(recv_data.decode('utf-8'))
        # print(http_request)

        if (
            http_request.header['upgrade'].lower() == 'websocket' and
            http_request.header['connection'].lower() == 'upgrade'
        ):
            # print("Incoming websocket request")
            self.request.sendall(WSUtils.generateHandshakeReply(http_request))

            exit_flag = False
            over_flag = False
            multi_flag = False

            wait_length = 0

            request_queue = []
            request_buffer = bytearray()

            while True:
                # websocket part
                recv_data = self.request.recv(MAX_MESSAGE_SIZE_ALLOWED)

                # print('----------------- new recv')
                # print('------ len recv(data)')
                # print(len(recv_data))
                # print('------- recv_data')
                # print(recv_data)

                if (recv_data == b'' or exit_flag):
                    return

                try:
                    request_buffer += recv_data
                    while len(request_buffer) > 0:
                        temp_ws_request = WSUtils.parseFrame(request_buffer)
                        # print(temp_ws_request)
                        print(temp_ws_request.length)

                        if (temp_ws_request.length <= temp_ws_request.data_length):
                            # print('valid')
                            request_buffer = temp_ws_request.raw_data[temp_ws_request.length:]
                            temp_ws_request.data = temp_ws_request.data[:temp_ws_request.length]
                            # print(len(request_buffer))
                            request_queue.append(temp_ws_request)
                        else:
                            # print('gagal ini')
                            # wait_length = temp_ws_request.length - temp_ws_request.data_length
                            raise Exception

                except Exception as e:
                    # print('--------------------- exception')
                    # print('------------- request_buffer')
                    # print(request_buffer)
                    # print('Invalid format')
                    # print(e)
                    pass

                while (len(request_queue) != 0):
                    send_message = not exit_flag

                    opcode = WSOpcodeType.TEXT
                    response_data = bytearray()
                    fin_flag = True
                    ws_request = request_queue.pop()

                    print('------ handle')
                    print(ws_request.length)

                    if ws_request.length != len(ws_request.data):
                        # message too long
                        # print('Message too long')
                        code = 1009
                        code = code.to_bytes(2, byteorder='big')
                        error = bytearray("Message too long!", encoding='utf-8')
                        response_data = bytearray(code + error)
                        opcode = WSOpcodeType.CLOSE
                        exit_flag = True

                    elif (ws_request.opcode == WSOpcodeType.PING):
                        # PING
                        opcode = WSOpcodeType.PONG
                        response_data = ws_request.data

                    elif (ws_request.opcode == WSOpcodeType.CLOSE):
                        # CLOSE
                        # print('Client request to close the connection')
                        code = ws_request.data[:2]
                        error = bytearray("Good Bye!", encoding='utf-8')
                        response_data = bytearray(code + error)
                        opcode = WSOpcodeType.CLOSE
                        exit_flag = True

                    elif (ws_request.opcode == WSOpcodeType.TEXT):
                        # TEXT handler
                        buffer_data = ws_request.data.decode()

                        if buffer_data[:6] == '!echo ':
                            response_data = bytearray(buffer_data[6:], encoding='utf-8')
                            if not ws_request.fin:
                                multi_flag = True
                                fin_flag = False

                        elif buffer_data == '!submission':
                            # kirim zip file
                            with open(SOURCE_FILE, 'rb') as zipFile:
                                response_data = zipFile.read()

                            opcode = WSOpcodeType.BIN

                        elif multi_flag:
                            response_data = ws_response.data

                            if ws_request.fin:
                                multi_flag = False
                            else:
                                fin_flag = False

                            opcode = ws_request.opcode
                        else:
                            send_message = False

                    elif (ws_request.opcode == WSOpcodeType.BIN):
                        md5sum_input = md5()
                        md5sum_input.update(ws_request.data)
                        md5sum_file = md5()

                        with open(SOURCE_FILE, 'rb') as zipFile:
                            md5sum_file.update(zipFile.read())

                        input_hash = md5sum_input.hexdigest()
                        file_hash = md5sum_file.hexdigest()

                        status = 1 if input_hash == file_hash else 0
                        # print("md5sum: ", input_hash)
                        # print("md5 kita:", file_hash)
                        response_data = bytearray(str(status), encoding='utf-8')

                    else:
                        send_message = False

                    if (send_message):
                        # print('----------------- send response')
                        ws_response = WSUtils.generatePayload(opcode, response_data, fin_flag)
                        # print(ws_response)
                        self.request.sendall(WSUtils.generateFrame(ws_response))
