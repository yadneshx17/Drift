import asyncio
from pathlib import Path

from torrent import torrent_download
from tracker import get_peers

base = Path(__file__).parent
torrent_path = base / "kali-linux-2026.1-installer-netinst-amd64.iso.torrent"


async def main():
    peers = get_peers(torrent_file=torrent_path)
    if len(peers) == 0:
        print("No peers found in tracker. Exiting...")
        return

    try:
        print(f"\nFound {len(peers)} peers from tracker:")
        for ip, port in peers[:10]:
            print(f"  {ip}:{port}")
        if len(peers) > 10:
            print(f"  ... and {len(peers) - 10} more")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    success = await torrent_download(
        "kali-linux-2026.1-installer-netinst-amd64.iso.torrent",
        peers,
        "kali-linux-2026.1-installer-netinst-amd64.iso",
        max_peers=50,
    )

    if success:
        print("Download successful!")
    else:
        print("Download failed or incomplete")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nDownload interrupted by user")
