import re
from dataclasses import dataclass
from typing import Dict


@dataclass()
class HTTPRequest():
    request_type: str
    request_path: str
    http_version: str
    header: Dict[str, str]
    body: str


class HTTPUtils():
    @staticmethod
    def headerKeypairParser(entry: str) -> (str, str):
        regex_match = re.search("^([\w-]+): (.*)$", entry)
        return (regex_match.group(1).lower(), regex_match.group(2))

    @staticmethod
    def parseRequest(message: str) -> HTTPRequest:
        header_text, body_text = message.split('\r\n\r\n')
        header = header_text.split('\r\n')
        start_line = header[0]

        request_type, request_path, http_version = start_line.split(' ')

        header_entry = header[1:]

        header_dict = dict(map(HTTPUtils.headerKeypairParser, header_entry))

        return HTTPRequest(
            request_type, request_path, http_version, header_dict, body_text
        )
