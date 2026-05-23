# Drift - Bittorrent client written in Python


> A lightweight BitTorrent client built in Python.

Drift is a learning-focused implementation of the BitTorrent protocol that handles torrent parsing, tracker communication, peer connections, and concurrent piece downloading.

---

# Preview

- Parses `.torrent` files
- Connects to trackers
- Fetches peers
- Performs BitTorrent handshakes
- Downloads pieces concurrently
- Verifies SHA-1 hashes
- Reconstructs final files

---

# Features

## Core Features

- Bencoding encoder & decoder
- Torrent metadata parsing
- Tracker communication
- Peer-to-peer socket communication
- Concurrent downloading
- Piece validation using SHA-1
- Modular codebase

## Technical Concepts Used

- TCP sockets
- Binary protocols
- Multithreading / concurrency
- File reconstruction
- Hash verification
- Distributed networking

---

# Project Structure

```bash
Drift/
│
├── main.py                # Entry point
├── bencoding/             # Bencoding parser/encoder
├── peer/                  # Peer communication logic
├── torrent/               # Torrent metadata handling
├── tracker/               # Tracker communication
├── tests/                 # Unit tests
└── README.md
