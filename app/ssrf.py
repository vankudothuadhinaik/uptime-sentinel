import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeTarget(ValueError):
    pass


def validate_target(url: str) -> None:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeTarget("target URL is malformed") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username
        or parsed.password
        or any(ord(char) < 32 for char in url)
    ):
        raise UnsafeTarget("target must be an http(s) URL without credentials")
    try:
        addresses = socket.getaddrinfo(
            hostname, port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
        )
    except (socket.gaierror, ValueError) as exc:
        raise UnsafeTarget("target hostname could not be resolved") from exc
    if not addresses:
        raise UnsafeTarget("target hostname has no addresses")
    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise UnsafeTarget("target resolves to a non-public address")
