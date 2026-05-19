import asyncio
import hashlib

from bencoding import Decoder, Encoder
from peer import AsyncBitTorrentPeer


async def download_piece_from_peer(peer, piece_index, piece_length, block_size=16384):
    """
    Download a single piece from a peer.
    Returns dict of {offset: block_data} or None if failed.
    """
    if not peer.has_piece(piece_index):
        return None

    # Send interested
    if not peer.interested:
        await peer.send_interested()

    # Wait for unchoke with timeout
    wait_time = 0
    while peer.peer_choking and wait_time < 5:
        msg_id, payload = await peer.receive_message()
        if msg_id is not None:
            peer.handle_message(msg_id, payload)
        await asyncio.sleep(0.1)
        wait_time += 0.1

    if peer.peer_choking:
        return None

    # Request all blocks
    blocks_needed = []
    for begin in range(0, piece_length, block_size):
        length = min(block_size, piece_length - begin)
        blocks_needed.append((begin, length))
        await peer.send_request(piece_index, begin, length)

    # Collect blocks
    piece_data = {}
    timeout_counter = 0
    max_timeout = 100

    while len(piece_data) < len(blocks_needed) and timeout_counter < max_timeout:
        msg_id, payload = await peer.receive_message()

        if msg_id is None:
            timeout_counter += 1
            await asyncio.sleep(0.1)
            continue

        result = peer.handle_message(msg_id, payload)
        if result and result[0] == "piece":
            _, idx, begin, block = result
            if idx == piece_index:
                piece_data[begin] = block
                timeout_counter = 0

    if len(piece_data) < len(blocks_needed):
        return None

    return piece_data


class TorrentDownloader:
    """Manages concurrent downloading from multiple peers."""

    def __init__(self, torrent_file_path, peers, max_peers=5):
        self.torrent_file_path = torrent_file_path
        self.peers = peers
        self.max_peers = max_peers

        # Load torrent metadata
        with open(torrent_file_path, "rb") as f:
            torrent_data = Decoder(f.read()).decode()

        self.info = torrent_data[b"info"]
        self.info_hash = hashlib.sha1(Encoder(self.info).encode()).digest()
        self.piece_length = self.info[b"piece length"]
        self.pieces_hash = self.info[b"pieces"]
        self.num_pieces = len(self.pieces_hash) // 20

        # Calculate total length
        if b"length" in self.info:
            self.total_length = self.info[b"length"]
        else:
            self.total_length = sum(f[b"length"] for f in self.info[b"files"])

        # Generate peer_id
        self.peer_id = b"-PY0001-" + b"0" * 12

        # Piece management
        self.downloaded_pieces = {}
        self.piece_locks = {i: asyncio.Lock() for i in range(self.num_pieces)}
        self.pieces_in_progress = set()
        self.connected_peers = []

        print(f"Torrent: {self.num_pieces} pieces, {self.total_length} bytes total")

    def get_piece_length(self, piece_idx):
        """Get the length of a specific piece."""
        if piece_idx == self.num_pieces - 1:
            return self.total_length - (piece_idx * self.piece_length)
        return self.piece_length

    def get_piece_hash(self, piece_idx):
        """Get the hash of a specific piece."""
        return self.pieces_hash[piece_idx * 20 : (piece_idx + 1) * 20]

    def verify_piece(self, piece_idx, piece_data):
        """Verify a piece's hash."""
        calculated_hash = hashlib.sha1(piece_data).digest()
        expected_hash = self.get_piece_hash(piece_idx)
        return calculated_hash == expected_hash

    async def peer_worker(self, ip, port):
        """Worker coroutine for a single peer."""
        peer = AsyncBitTorrentPeer(ip, port, self.info_hash, self.peer_id)

        # Connect and handshake
        if not await peer.connect():
            return

        if not await peer.handshake():
            await peer.close()
            return

        # Wait for bitfield
        for _ in range(10):
            msg_id, payload = await peer.receive_message()
            if msg_id is not None:
                peer.handle_message(msg_id, payload)
            if peer.bitfield is not None:
                break
            await asyncio.sleep(0.1)

        self.connected_peers.append(peer)

        try:
            # Download pieces
            while len(self.downloaded_pieces) < self.num_pieces:
                # Find a piece to download
                piece_idx = None
                for i in range(self.num_pieces):
                    if (
                        i not in self.downloaded_pieces
                        and i not in self.pieces_in_progress
                        and peer.has_piece(i)
                    ):
                        async with self.piece_locks[i]:
                            if i not in self.pieces_in_progress:
                                self.pieces_in_progress.add(i)
                                piece_idx = i
                                break

                if piece_idx is None:
                    # No pieces available, wait a bit
                    await asyncio.sleep(1)
                    continue

                # Download the piece
                piece_length = self.get_piece_length(piece_idx)
                piece_blocks = await download_piece_from_peer(
                    peer, piece_idx, piece_length
                )

                if piece_blocks:
                    # Assemble piece
                    complete_piece = b"".join(
                        piece_blocks[offset] for offset in sorted(piece_blocks.keys())
                    )

                    # Verify
                    if self.verify_piece(piece_idx, complete_piece):
                        async with self.piece_locks[piece_idx]:
                            self.downloaded_pieces[piece_idx] = complete_piece
                            self.pieces_in_progress.discard(piece_idx)

                        progress = len(self.downloaded_pieces)
                        print(
                            f"✓ Piece {piece_idx} downloaded from {ip}:{port} ({progress}/{self.num_pieces})"
                        )
                    else:
                        print(
                            f"✗ Piece {piece_idx} failed verification from {ip}:{port}"
                        )
                        async with self.piece_locks[piece_idx]:
                            self.pieces_in_progress.discard(piece_idx)
                else:
                    # Failed to download
                    async with self.piece_locks[piece_idx]:
                        self.pieces_in_progress.discard(piece_idx)
                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Error in peer worker {ip}:{port}: {e}")
        finally:
            await peer.close()
            if peer in self.connected_peers:
                self.connected_peers.remove(peer)

    async def download(self, output_file):
        """Start concurrent download from multiple peers."""
        # Create worker tasks for peers
        tasks = []
        for ip, port in self.peers[: self.max_peers * 2]:  # Try more peers than max
            task = asyncio.create_task(self.peer_worker(ip, port))
            tasks.append(task)
            await asyncio.sleep(0.1)  # Stagger connections

        # Wait for completion or all tasks to finish
        while len(self.downloaded_pieces) < self.num_pieces and any(
            not t.done() for t in tasks
        ):
            await asyncio.sleep(1)
            print(
                f"Progress: {len(self.downloaded_pieces)}/{self.num_pieces} pieces, "
                f"{len(self.connected_peers)} peers connected"
            )

        # Cancel remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        # Write to file if complete
        if len(self.downloaded_pieces) == self.num_pieces:
            print("\n✓ Download complete! Writing to file...")
            with open(output_file, "wb") as f:
                for i in range(self.num_pieces):
                    f.write(self.downloaded_pieces[i])
            print(f"✓ File saved to {output_file}")
            return True
        else:
            print(
                f"\n✗ Download incomplete: {len(self.downloaded_pieces)}/{self.num_pieces} pieces"
            )
            return False


async def torrent_download(torrent_file, peers, output_file, max_peers=5):
    """
    Download a torrent using multiple peers concurrently.

    Args:
        torrent_file: Path to .torrent file
        peers: List of (ip, port) tuples
        output_file: Path to save downloaded file
        max_peers: Maximum number of concurrent peer connections
    """
    downloader = TorrentDownloader(torrent_file, peers, max_peers)
    success = await downloader.download(output_file)
    return success
