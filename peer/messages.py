import struct


class ProtocolMessages:
    @staticmethod
    def build_handshake(info_hash: bytes, peer_id: bytes) -> bytes:
        pstr = b"BitTorrent protocol"
        return struct.pack("B", len(pstr)) + pstr + b"\x00" * 8 + info_hash + peer_id

    # Fixed-Length
    @staticmethod
    def build_interested() -> bytes:
        return struct.pack(">IB", 1, 2)  # len, id

    @staticmethod
    def build_not_interested() -> bytes:
        return struct.pack(">IB", 1, 3)

    @staticmethod
    def build_choke() -> bytes:
        return struct.pack(">IB", 1, 0)

    @staticmethod
    def build_unchoke() -> bytes:
        return struct.pack(">IB", 1, 1)

    @staticmethod
    def build_have(piece_index: int) -> bytes:
        return struct.pack(">IBI", 5, 4, piece_index)

    @staticmethod
    def build_request(piece_index: int, begin: int, length: int) -> bytes:
        return struct.pack(">IBIII", 13, 6, piece_index, begin, length)

    # Variable-length
    @staticmethod
    def build_piece(piece_index: int, begin: int, block: bytes) -> bytes:
        return struct.pack(">IBII", 9 + len(block), 7, piece_index, begin) + block

    @staticmethod
    def build_cancel(piece_index: int, begin: int, length: int) -> bytes:
        return struct.pack(">IBIII", 13, 8, piece_index, begin, length)

    @staticmethod
    def build_bitfield(bitfield: bytes) -> bytes:
        return struct.pack(">IB", 1 + len(bitfield), 5) + bitfield

    # --- Parsers ---
    @staticmethod
    def parse_handshake(data: bytes) -> dict:
        return {
            "pstrlen": data[0],
            "pstr": data[1:20],
            "reserved": data[20:28],
            "info_hash": data[28:48],
            "peer_id": data[48:68],
        }

    @staticmethod
    def parse_have(payload: bytes) -> int:
        return struct.unpack(">I", payload)[0]

    @staticmethod
    def parse_request(payload: bytes) -> tuple:
        return struct.unpack(">III", payload)

    @staticmethod
    def parse_piece(payload: bytes) -> tuple:
        index, begin = struct.unpack(">II", payload[:8])
        block = payload[8:]
        return index, begin, block

    @staticmethod
    def parse_cancel(payload: bytes) -> tuple:
        return struct.unpack(">III", payload)

    @staticmethod
    def parse_bitfield(payload: bytes) -> bytes:
        return payload

    # --- Message Dispatch ---
    MESSAGE_NAMES = {
        0: "choke",
        1: "unchoke",
        2: "interested",
        3: "not_interested",
        4: "have",
        5: "bitfield",
        6: "request",
        7: "piece",
        8: "cancel",
    }

    @staticmethod
    async def read_message(reader) -> tuple:
        """Read 4-byte length prefix then payload from a stream."""
        length_data = await reader.readexactly(4)
        length = struct.unpack(">I", length_data)[0]
        if length == 0:
            return None, None  # keep-alive
        data = await reader.readexactly(length)
        return data[0], data[1:]  # msg_id, payload

    @staticmethod
    def message_name(msg_id: int) -> str:
        return ProtocolMessages.MESSAGE_NAMES.get(msg_id, "unknown")
