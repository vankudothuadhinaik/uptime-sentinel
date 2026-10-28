from __future__ import annotations

import base64

import pytest

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
        "::ffff:127.0.0.1",
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
