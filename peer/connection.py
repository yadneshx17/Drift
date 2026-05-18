import asyncio

from .messages import ProtocolMessages


class AsyncBitTorrentPeer:
    """Handle asynchronous communication with a single BitTorrent peer."""

    def __init__(self, ip, port, info_hash, peer_id, timeout=10):
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.timeout = timeout
        self.connected = False
        self.reader = None
        self.writer = None

        # States
        self.choked = True
        self.interested = False
        self.peer_choking = True
        self.peer_interested = False
        self.bitfield = None

    async def connect(self):
        """Establish TCP connection with peer."""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=self.timeout
            )
            self.connected = True
            print(f"\nConnected to {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"\n    Failed to connect to {self.ip}:{self.port} - {e}")
            return False

    async def handshake(self):
        """Send handshake and verify peer's response."""
        try:
            msg = ProtocolMessages.build_handshake(self.info_hash, self.peer_id)
            self.writer.write(msg)
            await self.writer.drain()

            resp = await asyncio.wait_for(self.reader.readexactly(68), self.timeout)
            result = ProtocolMessages.parse_handshake(resp)

            if result["info_hash"] != self.info_hash:
                print(f"[-] Info hash mismatch from {self.ip}:{self.port}")
                return False

            print(f"[*] Handshake successful with {self.ip}:{self.port}")
            return True
        except (asyncio.exceptions.IncompleteReadError, ConnectionError, OSError) as e:
            print(f"Handshake failed with {self.ip}:{self.port} - {e}")
            return False

    async def send_interested(self):
        """Send interested message to peer."""
        msg = ProtocolMessages.build_interested()
        self.writer.write(msg)
        await self.writer.drain()
        self.interested = True

    async def send_not_interested(self):
        """Send not_interested message to peer."""
        msg = ProtocolMessages.build_not_interested()
        self.writer.write(msg)
        await self.writer.drain()
        self.interested = False

    async def send_request(self, piece_index, begin, length):
        """Request a block from peer."""
        msg = ProtocolMessages.build_request(piece_index, begin, length)
        self.writer.write(msg)
        await self.writer.drain()

    async def receive_message(self):
        """Receive and return (msg_id, payload) from peer."""
        try:
            return await ProtocolMessages.read_message(self.reader)
        except asyncio.TimeoutError:
            return None, None

    def handle_message(self, msg_id, payload):
        """Process received message and update peer state."""
        if msg_id is None:
            return None

        name = ProtocolMessages.message_name(msg_id)
        print(f"  -> {self.ip}:{self.port} sent: {name}")

        if msg_id == 0:
            self.peer_choking = True
        elif msg_id == 1:
            self.peer_choking = False
            print(f"  [unchoked]")
        elif msg_id == 2:
            self.peer_interested = True
        elif msg_id == 3:
            self.peer_interested = False
        elif msg_id == 4:
            piece_index = ProtocolMessages.parse_have(payload)
            return piece_index
        elif msg_id == 5:
            self.bitfield = payload
        elif msg_id == 6:
            return ProtocolMessages.parse_request(payload)
        elif msg_id == 7:
            return ProtocolMessages.parse_piece(payload)
        elif msg_id == 8:
            return ProtocolMessages.parse_cancel(payload)

        return None

    def has_piece(self, piece_index):
        """Check if peer has a specific piece."""
        if self.bitfield is None:
            return False
        if piece_index >= len(self.bitfield) * 8:
            return False
        byte_index = piece_index // 8
        bit_index = 7 - (piece_index % 8)
        return bool((self.bitfield[byte_index] >> bit_index) & 1)

    async def close(self):
        """Close connection to peer."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
        self.reader = None
        self.writer = None
