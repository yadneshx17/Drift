import asyncio
from pathlib import Path

from peer import AsyncBitTorrentPeer
from tracker import get_peers

base = Path(__file__).parent
# torrent_path = base / "one-piece.torrent"
torrent_path = base / "kali-linux-2026.1-installer-netinst-amd64.iso.torrent"


async def main():
    peers, info_hash, peer_id = get_peers(torrent_file=torrent_path)
    if len(peers) == 0:
        print("No peers found in tracker. Exiting...")
        return

    for ip, port in peers:
        conn = AsyncBitTorrentPeer(ip, port, info_hash, peer_id)
        await conn.connect()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nDownload interrupted by user")
