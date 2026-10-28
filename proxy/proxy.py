"""Authenticated HTTP CONNECT/forward proxy with destination-IP SSRF controls.

This is a minimal controlled egress proxy, not a general-purpose anonymous proxy.
Only HTTP proxy requests are accepted. DNS is resolved once per connection and
the socket is connected to that exact resolved IP to prevent DNS-rebinding TOCTOU.
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import ipaddress
import os
import socket
from urllib.parse import urlsplit

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))
USERNAME = os.getenv("PROXY_USERNAME", "")
PASSWORD = os.getenv("PROXY_PASSWORD", "")
HEADER_LIMIT = 32 * 1024
CONNECT_TIMEOUT = 8
IDLE_TIMEOUT = 60


def _safe_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value.split("%", 1)[0])
    # is_global rejects loopback, RFC1918, link-local, multicast, unspecified,
    # reserved ranges, and IPv4-mapped private IPv6 addresses.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if (
        ip.is_multicast
        or ip.is_unspecified
        or ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
    ):
        return False
    return ip.is_global


def _authorized(headers: dict[str, str]) -> bool:
    # Fail closed: an internet-reachable proxy must never accept empty/default credentials.
    if not USERNAME or not PASSWORD:
        return False
    supplied = headers.get("proxy-authorization", "")
    expected = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    return hmac.compare_digest(supplied, expected)


async def _resolve_public(host: str, port: int) -> list[tuple[int, tuple]]:
    loop = asyncio.get_running_loop()
    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout=CONNECT_TIMEOUT
        )
    except (OSError, TimeoutError):
        raise ValueError("DNS resolution failed") from None
    unique: list[tuple[int, tuple]] = []
    seen: set[tuple] = set()
    for family, _type, proto, _canon, sockaddr in infos:
        ip = sockaddr[0]
        if not _safe_ip(ip):
            raise PermissionError("Destination resolves to a non-public IP")
        item = (family, sockaddr)
        if item not in seen:
            unique.append(item)
            seen.add(item)
    if not unique:
        raise ValueError("No usable destination address")
    return unique


async def _open_pinned(host: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    addresses = await _resolve_public(host, port)
    last_error: Exception | None = None
    for family, sockaddr in addresses:
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.setblocking(False)
        try:
            await asyncio.wait_for(
                asyncio.get_running_loop().sock_connect(sock, sockaddr), timeout=CONNECT_TIMEOUT
            )
            reader, writer = await asyncio.open_connection(sock=sock)
            return reader, writer
        except (OSError, TimeoutError) as exc:
            last_error = exc
            sock.close()
    raise OSError("Could not connect to validated destination") from last_error


async def _relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await asyncio.wait_for(reader.read(65536), timeout=IDLE_TIMEOUT)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (OSError, TimeoutError, asyncio.IncompleteReadError):
        pass
    finally:
        writer.close()


async def _tunnel(client_r, client_w, host: str, port: int) -> None:
    upstream_w = None
    try:
        upstream_r, upstream_w = await _open_pinned(host, port)
        client_w.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await client_w.drain()
        await asyncio.gather(_relay(client_r, upstream_w), _relay(upstream_r, client_w))
    except PermissionError:
        client_w.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
        await client_w.drain()
    except (ValueError, OSError, TimeoutError):
        if not client_w.is_closing():
            client_w.write(
                b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
            )
            await client_w.drain()
    finally:
        if upstream_w:
            upstream_w.close()
        client_w.close()


async def handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter) -> None:
    upstream_w = None
    try:
        raw = await asyncio.wait_for(client_r.readuntil(b"\r\n\r\n"), timeout=10)
        if len(raw) > HEADER_LIMIT:
            client_w.write(
                b"HTTP/1.1 431 Request Header Fields Too Large\r\nConnection: close\r\n\r\n"
            )
            return
        lines = raw.decode("iso-8859-1").split("\r\n")
        method, target, _version = lines[0].split(" ", 2)
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            if ":" not in line:
                raise ValueError("Malformed header")
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        if method.upper() == "GET" and target == "/healthz":
            client_w.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n"
            )
            return
        if not _authorized(headers):
            client_w.write(
                b'HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic realm="controlled-egress"\r\nConnection: close\r\nContent-Length: 0\r\n\r\n'
            )
            return

        if method.upper() == "CONNECT":
            if target.count(":") != 1:
                raise ValueError("Invalid CONNECT authority")
            host, port_text = target.rsplit(":", 1)
            port = int(port_text)
            if not host or not (1 <= port <= 65535) or port not in (443, 8443):
                client_w.write(
                    b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
                )
                return
            await _tunnel(client_r, client_w, host.strip("[]"), port)
            return

        parsed = urlsplit(target)
        if parsed.scheme != "http" or not parsed.hostname:
            client_w.write(
                b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
            )
            return
        host = parsed.hostname
        port = parsed.port or 80
        if port != 80:
            client_w.write(
                b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
            )
            return
        upstream_r, upstream_w = await _open_pinned(host, port)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        out = [f"{method} {path} HTTP/1.1"]
        for key, value in headers.items():
            if key not in {"proxy-authorization", "proxy-connection", "connection"}:
                out.append(f"{key}: {value}")
        out.append("Connection: close")
        upstream_w.write(("\r\n".join(out) + "\r\n\r\n").encode("iso-8859-1"))
        await upstream_w.drain()
        await asyncio.gather(_relay(client_r, upstream_w), _relay(upstream_r, client_w))
    except PermissionError:
        if not client_w.is_closing():
            client_w.write(
                b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
            )
    except (ValueError, OSError, TimeoutError, asyncio.IncompleteReadError, UnicodeError):
        if not client_w.is_closing():
            client_w.write(
                b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
            )
    finally:
        if upstream_w:
            upstream_w.close()
        if not client_w.is_closing():
            client_w.close()
        try:
            await client_w.wait_closed()
        except OSError:
            pass


async def main() -> None:
    if len(USERNAME) < 8 or len(PASSWORD) < 32:
        raise SystemExit("PROXY_USERNAME must be >=8 chars and PROXY_PASSWORD >=32 chars")
    server = await asyncio.start_server(handle, HOST, PORT, limit=HEADER_LIMIT + 1)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
