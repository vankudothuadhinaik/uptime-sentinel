from __future__ import annotations

import asyncio
import base64
import shutil
import socket
import ssl
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest

import proxy.proxy as proxy_module

PROXY_USERNAME = "local-proxy-user"
PROXY_PASSWORD = "local-proxy-password-" + "x" * 16
Resolver = Callable[[str, int], Awaitable[list[tuple[int, tuple[str, int]]]]]


async def _start_server(
    callback: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]],
) -> tuple[asyncio.AbstractServer, int]:
    server = await asyncio.start_server(callback, "127.0.0.1", 0)
    address = server.sockets[0].getsockname()
    return server, address[1]


async def _fixture_response(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await reader.readuntil(b"\r\n\r\n")
        writer.write(
            b"HTTP/1.1 302 Found\r\n"
            b"Location: http://127.0.0.1/private\r\n"
            b"Content-Length: 0\r\n"
            b"Connection: close\r\n\r\n"
        )
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def _tls_response(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def _connection_fixture(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.close()
    await writer.wait_closed()


async def _proxy_server(monkeypatch: pytest.MonkeyPatch) -> tuple[asyncio.AbstractServer, int]:
    monkeypatch.setattr(proxy_module, "USERNAME", PROXY_USERNAME)
    monkeypatch.setattr(proxy_module, "PASSWORD", PROXY_PASSWORD)
    server = await asyncio.start_server(proxy_module.handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def _raw_proxy_request(port: int, request: bytes) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        writer.write(request)
        await writer.drain()
        return await reader.read()
    finally:
        writer.close()
        await writer.wait_closed()


async def _local_resolver(port: int, calls: list[tuple[str, int]], host: str, target_port: int):
    calls.append((host, target_port))
    return [(socket.AF_INET, ("127.0.0.1", port))]


@pytest.mark.asyncio
async def test_proxy_pins_one_resolver_result_for_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_server, fixture_port = await _start_server(_connection_fixture)
    calls: list[tuple[str, int]] = []

    async def resolver(host: str, port: int):
        return await _local_resolver(fixture_port, calls, host, port)

    monkeypatch.setattr(proxy_module, "_resolve_public", resolver)
    try:
        _, writer = await proxy_module._open_pinned("rebind-fixture.test", 443)
        writer.close()
        await writer.wait_closed()
        assert calls == [("rebind-fixture.test", 443)]
    finally:
        fixture_server.close()
        await fixture_server.wait_closed()


@pytest.mark.asyncio
async def test_actual_proxy_does_not_follow_local_unsafe_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_server, fixture_port = await _start_server(_fixture_response)
    proxy_server, proxy_port = await _proxy_server(monkeypatch)
    calls: list[tuple[str, int]] = []

    async def resolver(host: str, port: int):
        return await _local_resolver(fixture_port, calls, host, port)

    monkeypatch.setattr(proxy_module, "_resolve_public", resolver)
    try:
        proxy = httpx.Proxy(
            f"http://127.0.0.1:{proxy_port}",
            auth=(PROXY_USERNAME, PROXY_PASSWORD),
        )
        async with httpx.AsyncClient(
            proxy=proxy, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.get("http://redirect-fixture.test/")
        assert response.status_code == 302
        assert response.headers["location"] == "http://127.0.0.1/private"
        assert calls == [("redirect-fixture.test", 80)]
    finally:
        proxy_server.close()
        await proxy_server.wait_closed()
        fixture_server.close()
        await fixture_server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_rejects_unauthorized_and_unsupported_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proxy_server, proxy_port = await _proxy_server(monkeypatch)
    try:
        unauthorized = await _raw_proxy_request(
            proxy_port,
            b"GET http://example.test/ HTTP/1.1\r\nHost: example.test\r\nConnection: close\r\n\r\n",
        )
        assert unauthorized.startswith(b"HTTP/1.1 407 Proxy Authentication Required")

        encoded = base64.b64encode(f"{PROXY_USERNAME}:{PROXY_PASSWORD}".encode()).decode()
        unsupported = await _raw_proxy_request(
            proxy_port,
            (
                b"TRACE http://example.test/ HTTP/1.1\r\n"
                b"Host: example.test\r\n"
                + f"Proxy-Authorization: Basic {encoded}\r\n".encode()
                + b"Connection: close\r\n\r\n"
            ),
        )
        assert unsupported.startswith(b"HTTP/1.1 405 Method Not Allowed")
    finally:
        proxy_server.close()
        await proxy_server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_rejects_target_credentials_and_unsupported_connect_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proxy_server, proxy_port = await _proxy_server(monkeypatch)
    encoded = base64.b64encode(f"{PROXY_USERNAME}:{PROXY_PASSWORD}".encode()).decode()
    auth = f"Proxy-Authorization: Basic {encoded}\r\n".encode()
    try:
        credentials = await _raw_proxy_request(
            proxy_port,
            b"GET http://user:password@example.test/ HTTP/1.1\r\n"
            b"Host: example.test\r\n" + auth + b"Connection: close\r\n\r\n",
        )
        assert credentials.startswith(b"HTTP/1.1 400 Bad Request")

        unsupported_port = await _raw_proxy_request(
            proxy_port,
            b"CONNECT example.test:80 HTTP/1.1\r\n"
            b"Host: example.test\r\n" + auth + b"Connection: close\r\n\r\n",
        )
        assert unsupported_port.startswith(b"HTTP/1.1 403 Forbidden")
    finally:
        proxy_server.close()
        await proxy_server.wait_closed()


def _create_self_signed_certificate(directory: Path) -> tuple[Path, Path]:
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("openssl is required for the local invalid-TLS fixture")
    certificate = directory / "fixture.crt"
    key = directory / "fixture.key"
    subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
            "-subj",
            "/CN=invalid-tls.test",
            "-days",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return certificate, key


@pytest.mark.asyncio
async def test_actual_proxy_preserves_tls_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TemporaryDirectory() as temporary_directory:
        certificate, key = _create_self_signed_certificate(Path(temporary_directory))
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.load_cert_chain(certificate, key)
        fixture_server = await asyncio.start_server(_tls_response, "127.0.0.1", 0, ssl=tls_context)
        proxy_server, proxy_port = await _proxy_server(monkeypatch)

        async def resolver(_: str, __: int):
            return [(socket.AF_INET, ("127.0.0.1", fixture_server.sockets[0].getsockname()[1]))]

        monkeypatch.setattr(proxy_module, "_resolve_public", resolver)
        try:
            proxy = httpx.Proxy(
                f"http://127.0.0.1:{proxy_port}",
                auth=(PROXY_USERNAME, PROXY_PASSWORD),
            )
            async with httpx.AsyncClient(
                proxy=proxy, follow_redirects=False, trust_env=False, verify=True
            ) as client:
                with pytest.raises(httpx.HTTPError):
                    await client.get("https://invalid-tls.test/")
        finally:
            proxy_server.close()
            await proxy_server.wait_closed()
            fixture_server.close()
            await fixture_server.wait_closed()
