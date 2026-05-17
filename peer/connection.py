import asyncio


class AsyncBitTorrentPeer:
    """Handle asynchronous communication with a single BitTorrent peer."""

    def __init__(self, ip, port, info_hash, peer_id, timeout=10):
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.timeout = timeout
        self.connected = False

    async def connect(self):
        """Establish TCP connection with peer."""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=self.timeout
            )
            self.connected = True
            print(f"Connected to {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to {self.ip}:{self.port} - {e}")
            return False
