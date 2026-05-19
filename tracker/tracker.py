import hashlib
import os
import socket
import urllib.parse
import urllib.request

from bencoding import Decoder, Encoder


def get_peerId():
    peer_id_prefix = b"-DRIFT0001-"
    return peer_id_prefix + os.urandom(20 - len(peer_id_prefix))


def get_peers(torrent_file, port=6881, numwant=50):
    with open(torrent_file, "rb") as f:
        data = f.read()
    decoded = Decoder(data).decode()

    if b"announce" not in decoded:
        raise ValueError("Torrent File missing 'announce' key")

    # Extract all HTTP trackers
    tracker_urls = []
    if b"announce" in decoded:
        tracker = decoded[b"announce"].decode()
        if tracker.startswith("http"):
            tracker_urls.append(tracker)

    # if b"announce-list" in decoded:
    #     for tier in decoded[b"announce-list"]:
    #         for url_bytes in tier:
    #             url = url_bytes.decode()
    #             if url.startswith("http") and url not in tracker_urls:
    #                 tracker_urls.append(url)

    info = decoded[b"info"]
    info_bytes = Encoder(info).encode()
    info_hash = hashlib.sha1(info_bytes).digest()

    print(f"\nFound {len(tracker_urls)} HTTP trackers")

    if b"length" in info:
        left = info[b"length"]
    elif b"files" in info:
        left = sum(f[b"length"] for f in info[b"files"])
    else:
        raise ValueError("Invalid info directory: missing 'length' or 'files'")

    print(f"Total size: {left / (1024**3):.2f} GB")
    print("Info hash:", info_hash)
    print("Tracker url:", tracker_urls)

    peer_id = get_peerId()  # replace with the function
    tracker_url = tracker_urls[0]

    # for tracker_url in tracker_urls:
    params = {
        "info_hash": info_hash,
        "peer_id": peer_id,
        "port": port,
        "uploaded": 0,
        "downloaded": 0,
        "left": left,
        "compact": 1,
        "event": "started",
        "numwant": numwant,
    }

    # URL-encode binary values properly
    query_parts = []
    for key, val in params.items():
        if isinstance(val, bytes):
            # Properly encode binary data
            encoded_val = urllib.parse.quote(val, safe="")
            query_parts.append(f"{key}={encoded_val}")
        else:
            # Regular URL encoding for non-binary values
            query_parts.append(f"{key}={urllib.parse.quote(str(val), safe='')}")

    query_string = "&".join(query_parts)

    # Build the full announce URL
    if "?" in tracker_url:
        full_url = tracker_url + "&" + query_string
    else:
        full_url = tracker_url + "?" + query_string

    print(f"\nAnnounce URL: {tracker_url}")
    print(f"Full announce URL: {full_url}")
    # print(f"Requesting: {tracker_urls}")

    # Send HTTP GET request
    req = urllib.request.Request(full_url)
    req.add_header("User-Agent", "Python-Drifttorrent-Client/1.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            tracker_data = response.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Tracker returned error: {e.code} - {error_body}")

    # print(f"Received tracker response: {tracker_data}")
    # Decode the tracker response (bencoded)
    tracker_decoded = Decoder(tracker_data).decode()

    # Check for failure reason
    if b"failure reason" in tracker_decoded:
        failure = tracker_decoded[b"failure reason"].decode("utf-8")
        raise ValueError(f"Tracker failure: {failure}")

    if b"peers" not in tracker_decoded:
        raise ValueError("Tracker response missing 'peers' key")

    peers_data = tracker_decoded[b"peers"]
    # print(f"Received peers from tracker: ", peers_data)

    peers = []
    if isinstance(peers_data, bytes):
        # Compact format: 4 byter IP + 2 bytes port per peer
        if len(peers_data) % 6 != 0:
            raise ValueError("Invalid compact peer format")

        for i in range(0, len(peers_data), 6):
            ip_bytes = peers_data[i : i + 4]
            port_bytes = peers_data[i + 4 : i + 6]
            ip = ".".join(map(str, ip_bytes))
            # ip = socket.inet_ntoa(ip_bytes) # using socket lib
            if ip == "127.0.0.1":
                continue
            port = int.from_bytes(port_bytes, "big")
            peers.append((ip, port))
    elif isinstance(peers_data, list):
        # Non-compact format: sometimes the tracker might send a list of dictionaries
        for peer_dict in peers_data:
            ip = peer_dict[b"ip"].decode("utf-8")
            port = peer_dict[b"port"]
            peers.append((ip, port))
    else:
        raise ValueError("Unknown peers format")

    return peers


if __name__ == "__main__":
    try:
        peers, info_hash, peer_id = get_peers("kali-linux-2026.1-installer-netinst-amd64.iso.torrent")
        print(f"\nFound {len(peers)} peers from tracker:")
        for ip, port in peers[:10]:
            print(f"  {ip}:{port}")
        if len(peers) > 10:
            print(f"  ... and {len(peers) - 10} more")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
