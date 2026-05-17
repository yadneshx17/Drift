import hashlib

from typing_extensions import OrderedDict

from bencoding import Decoder, Encoder

# with open("kali-linux-2026.1-installer-netinst-amd64.iso.torrent", "rb") as f:
#     meta_info = f.read()
#     # print(f"---- Info-Hash: {hashlib.sha1(meta_info).hexdigest()}")
#     # print(f"---- Meta-Info: {meta_info}")
#     torrent = Decoder(meta_info).decode()
#     # print(f"---- Torrent: {torrent}")


# write to file
# with open("raw_decode.txt", "w", encoding="utf-8") as out:
#     out.write(str(torrent))


# Readable format
def to_readable(obj):
    if isinstance(obj, dict):
        return {to_readable(k): to_readable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_readable(i) for i in obj]
    elif isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return obj.hex()  # fallback for binary data like 'pieces'
    else:
        return obj


with open("kali-linux-2026.1-installer-netinst-amd64.iso.torrent", "rb") as f:
    meta_info = f.read()

    # raw which we want to use
    torrent = Decoder(meta_info).decode()

# print(f"type: {type(torrent)}")
readable = to_readable(torrent)
# tobehash = torrent[b"info"]
# hashed = hashlib.sha1(tobehash).hexdigest()
# print(f"Hashes: {tobehash}")
print(readable)

with open("rder.txt", "w", encoding="utf-8") as out:
    import json

    json.dump(readable, out, indent=4)

    # pal_decoded_out.txt
    out.write(str(readable))
