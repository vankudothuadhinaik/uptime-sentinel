"""Opt-in tests for a real, controlled forward proxy.

These tests intentionally require explicit fixture URLs. They are skipped by
default and must not be pointed at a general-purpose or public proxy.
"""

import os

import httpx
import pytest

RUN_INTEGRATION = os.getenv("RUN_EGRESS_PROXY_INTEGRATION") == "1"
PROXY_URL = os.getenv("EGRESS_PROXY_TEST_URL")


def _fixture_url(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.fail(f"{name} must be set for egress-proxy integration")
    return value


@pytest.fixture(scope="module")
def proxy_client():
    if not PROXY_URL:
        pytest.fail("EGRESS_PROXY_TEST_URL must be set for egress-proxy integration")
    with httpx.Client(
        proxy=PROXY_URL,
        follow_redirects=False,
        trust_env=False,
        verify=True,
        timeout=10,
    ) as client:
        yield client


pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="controlled egress-proxy integration is opt-in",
)


def test_public_https_endpoint_is_reachable(proxy_client: httpx.Client):
    response = proxy_client.get(_fixture_url("EGRESS_PUBLIC_URL"))
    assert 200 <= response.status_code < 300


@pytest.mark.parametrize("variable", ["EGRESS_PRIVATE_URL", "EGRESS_REBIND_URL"])
def test_proxy_rejects_private_and_rebinding_destinations(
    proxy_client: httpx.Client, variable: str
):
    response = proxy_client.get(_fixture_url(variable))
    # The controlled fixture contract requires an explicit policy-denial status.
    # A DNS failure, refused connection, timeout, or arbitrary 5xx is not proof
    # that the proxy enforced its destination-IP policy.
    assert response.status_code == 403, (
        f"controlled proxy must explicitly deny unsafe fixture {variable} "
        f"with HTTP 403; got {response.status_code}"
    )


def test_redirect_is_not_followed(proxy_client: httpx.Client):
    response = proxy_client.get(_fixture_url("EGRESS_REDIRECT_URL"))
    assert 300 <= response.status_code < 400
    assert response.headers.get("location")


def test_invalid_upstream_certificate_is_rejected(proxy_client: httpx.Client):
    with pytest.raises(httpx.HTTPError):
        proxy_client.get(_fixture_url("EGRESS_BAD_TLS_URL"))
