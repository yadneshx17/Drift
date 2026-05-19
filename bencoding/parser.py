# python representaion of the data present in `.torrent` file

# Tokens to Indicate Start of each Data-Strucutre : Dict, List, Integer, String.

from typing_extensions import OrderedDict

TOKEN_INTEGER = b"i"

TOKEN_LIST = b"l"

TOKEN_DICT = b"d"

TOKEN_END = b"e"

TOKEN_STRING_SEPARATOR = b":"


class Decoder:
    def __init__(self, data: bytes):
        if not isinstance(data, bytes):
            raise TypeError('Argument "data" must be of type bytes')
        self._data = data
        self._index = 0

    def decode(self):
        """
        Decodes the bencode data and return the Matching python object.

        :return A python object representing the bencoded data
        """

        c = self._peek()
        if c is None:
            raise EOFError("Unexpected end-of-file")
        elif c == TOKEN_INTEGER:
            self._consume()
            return self._decode_int()
        elif c == TOKEN_LIST:
            self._consume()
            return self._decode_list()
        elif c == TOKEN_DICT:
            self._consume()
            return self._decode_dict()
        elif c in b"0123456789":
            return self._decode_string()
        else:
            raise RuntimeError("Invalid token read at {0}".format(str(self._index)))

    def _peek(self):
        """
        Return the next character from the bencoded data or None
        """
        if self._index + 1 > len(self._data):
            return None
        return self._data[self._index : self._index + 1]

    def _consume(self):
        """
        Increases serach index number. hence, Read next character from the data
        """
        self._index += 1

    def _read_until(self, token: bytes):
        try:
            occurence = self._data.index(
                token, self._index
            )  # `.index(byte, startIndex)`
            result = self._data[self._index : occurence]
            self._index = occurence + 1
            return result
        except ValueError:
            raise RuntimeError(f"Unable to find the token {0}".format(str(token)))

    def _read(self, length: int):
        if self._index + length > len(self._data):
            raise IndexError(
                f"Cannot read {0} bytes from current position {1}".format(
                    str(length), str(self._index)
                )
            )

        result = self._data[self._index : self._index + length]
        self._index += length
        return result

    def _decode_string(self):
        # Parse length digits first (stop at colon, don't search for it)
        start = self._index
        while self._data[self._index : self._index + 1] != TOKEN_STRING_SEPARATOR:
            self._index += 1
        length = int(self._data[start : self._index])
        self._index += 1  # skip the colon
        data = self._read(length)
        return data

    def _decode_int(self):
        return int(self._read_until(TOKEN_END))

    def _decode_list(self):
        res = []
        # recursively decode the content of the file
        while self._data[self._index : self._index + 1] != TOKEN_END:
            res.append(self.decode())
        self._consume()  # The End Token
        return res

    def _decode_dict(self):
        res = OrderedDict()
        while self._data[self._index : self._index + 1] != TOKEN_END:
            key = self.decode()
            obj = self.decode()
            res[key] = obj
        self._consume()  # skip "e"
        return res


class Encoder:
    """
    Encodes python objects into Bencode sequence of bytes.

    Supported python types is:
        str
        int
        list
        dict
        bytes
    """

    def __init__(self, data):
        self._data = data

    def encode(self):
        """
        Encodes the python objects into Bencode binary string

        :returns the bencoded binary data
        """

        return self._encode_next(self._data)

    def _encode_next(self, data):
        if isinstance(data, str):
            return self._encode_string(data)
        elif isinstance(data, int):
            return self._encode_int(data)
        elif isinstance(data, list):
            return self._encode_list(data)
        elif isinstance(data, dict) or isinstance(data, OrderedDict):
            return self._encode_dict(data)
        elif isinstance(data, bytes):
            return self._encode_bytes(data)
        else:
            raise TypeError(f"Unsupported type: {type(data)}")

    def _encode_string(self, data):
        res = str(len(data)) + ":" + data
        return str.encode(res)  # converts strings into bytes

    def _encode_int(self, data):
        return str.encode("i" + str(data) + "e")

    def _encode_bytes(self, data):
        result = bytearray()
        result += str.encode(str(len(data)))
        result += b":"
        result += data
        return result

    def _encode_list(self, data):
        result = bytearray(b"l")
        result += b"".join(self._encode_next(item) for item in data)
        result += b"e"
        return result

    def _encode_dict(self, data):
        result = bytearray("d", "utf-8")
        for k, v in data.items():
            key = self._encode_next(k)
            value = self._encode_next(v)
            if key and value:
                result += key
                result += value
            else:
                raise RuntimeError("Bad dict")
        result += b"e"
        return result
