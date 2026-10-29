from __future__ import annotations

import asyncio
import base64
import socket

import pytest

import proxy.proxy as proxy_module
from proxy.proxy import _authorized, _safe_ip


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "fe80::1",
        "224.0.0.1",
        "0.0.0.0",
        "192.0.0.1",
        "198.18.0.1",
        "240.0.0.1",
        "ff02::1",
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
    ],
)
def test_non_public_addresses_are_rejected(address: str) -> None:
    assert not _safe_ip(address)


@pytest.mark.parametrize("address", ["1.1.1.1", "8.8.8.8", "2606:4700:4700::1111"])
def test_public_addresses_are_accepted(address: str) -> None:
    assert _safe_ip(address)


def test_invalid_ip_is_not_accepted() -> None:
    with pytest.raises(ValueError):
        _safe_ip("not-an-ip")


def test_proxy_authentication_requires_exact_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    import proxy.proxy as proxy_module

    monkeypatch.setattr(proxy_module, "USERNAME", "test-user")
    monkeypatch.setattr(proxy_module, "PASSWORD", "x" * 32)
    encoded = base64.b64encode(f"test-user:{'x' * 32}".encode()).decode()
    assert _authorized({"proxy-authorization": f"Basic {encoded}"})
    assert not _authorized({"proxy-authorization": "Basic wrong"})
    assert not _authorized({})


def test_proxy_authentication_fails_closed_when_credentials_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import proxy.proxy as proxy_module

    monkeypatch.setattr(proxy_module, "USERNAME", "")
    monkeypatch.setattr(proxy_module, "PASSWORD", "")
    # Even Basic auth for an empty user/password must not authorize public access.
    empty_credentials = base64.b64encode(b":").decode()
    assert not _authorized({"proxy-authorization": f"Basic {empty_credentials}"})
    assert not _authorized({})


@pytest.mark.asyncio
async def test_dns_resolution_rejects_mixed_public_and_private_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = asyncio.get_running_loop()

    async def mixed_answers(*args: object, **kwargs: object):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
        ]

    monkeypatch.setattr(loop, "getaddrinfo", mixed_answers)
    with pytest.raises(PermissionError, match="non-public"):
        await proxy_module._resolve_public("mixed.test", 443)


@pytest.mark.asyncio
async def test_dns_resolution_failure_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = asyncio.get_running_loop()

    async def resolution_failure(*args: object, **kwargs: object):
        raise socket.gaierror("fixture resolution failure")

    monkeypatch.setattr(loop, "getaddrinfo", resolution_failure)
    with pytest.raises(ValueError, match="DNS resolution failed"):
        await proxy_module._resolve_public("missing.test", 443)
