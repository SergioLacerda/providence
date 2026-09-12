"""Tests for HttpProvider URL validation and async availability."""

from __future__ import annotations

import pytest
from providence_runtime.providers.http_provider import HttpProvider


def test_file_scheme_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """file:// scheme is rejected at construction time."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "file:///etc/passwd")
    with pytest.raises(ValueError, match="unsupported scheme 'file'"):
        HttpProvider()


def test_ftp_scheme_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """ftp:// scheme is rejected at construction time."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "ftp://example.com/data")
    with pytest.raises(ValueError, match="unsupported scheme 'ftp'"):
        HttpProvider()


def test_http_localhost_warns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """http:// URL is accepted but emits a warning."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://localhost:8080")
    import logging

    with caplog.at_level(
        logging.WARNING, logger="providence_runtime.providers.http_provider"
    ):
        provider = HttpProvider()
    assert provider._url == "http://localhost:8080"
    assert any("plaintext HTTP" in r.message for r in caplog.records)


def test_https_accepted_no_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """https:// URL is accepted without any warning."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://service.internal")
    import logging

    with caplog.at_level(
        logging.WARNING, logger="providence_runtime.providers.http_provider"
    ):
        provider = HttpProvider()
    assert provider._url == "https://service.internal"
    assert not any("plaintext" in r.message for r in caplog.records)


def test_unset_url_skips_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SDD_INTELLIGENCE_URL is unset, no validation runs."""
    monkeypatch.delenv("SDD_INTELLIGENCE_URL", raising=False)
    provider = HttpProvider()
    assert provider._url is None


def test_http_remote_host_rejected_without_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """http:// for a non-local host is rejected unless explicitly allowed."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://intel.example.com")
    monkeypatch.delenv("SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP", raising=False)
    with pytest.raises(ValueError, match="plaintext HTTP for non-local host"):
        HttpProvider()


def test_http_remote_host_allowed_with_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """http:// for a non-local host is accepted when explicitly opted in."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://intel.example.com")
    monkeypatch.setenv("SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP", "true")
    provider = HttpProvider()
    assert provider._url == "http://intel.example.com"


def test_https_remote_host_not_in_allow_list_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host allow-list restricts remote endpoints even over HTTPS."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://untrusted.example.com")
    monkeypatch.setenv("SDD_INTELLIGENCE_ALLOWED_HOSTS", "trusted.example.com")
    with pytest.raises(ValueError, match="not in SDD_INTELLIGENCE_ALLOWED_HOSTS"):
        HttpProvider()


def test_https_remote_host_in_allow_list_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host present in the allow-list is accepted."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://trusted.example.com")
    monkeypatch.setenv("SDD_INTELLIGENCE_ALLOWED_HOSTS", "trusted.example.com")
    provider = HttpProvider()
    assert provider._url == "https://trusted.example.com"


def test_remote_without_token_warns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A remote endpoint without an auth token logs a warning but is allowed."""
    import logging

    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://intel.example.com")
    monkeypatch.delenv("SDD_INTELLIGENCE_TOKEN", raising=False)
    monkeypatch.delenv("SDD_ENV", raising=False)
    monkeypatch.delenv("SDD_GOVERNANCE_MODE", raising=False)
    with caplog.at_level(
        logging.WARNING, logger="providence_runtime.providers.http_provider"
    ):
        HttpProvider()
    assert any("without SDD_INTELLIGENCE_TOKEN" in r.message for r in caplog.records)


def test_remote_without_token_rejected_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://intel.example.com")
    monkeypatch.delenv("SDD_INTELLIGENCE_TOKEN", raising=False)
    monkeypatch.setenv("SDD_ENV", "production")
    with pytest.raises(ValueError, match="requires authenticated remote"):
        HttpProvider()


def test_remote_without_token_rejected_in_hard_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://intel.example.com")
    monkeypatch.delenv("SDD_INTELLIGENCE_TOKEN", raising=False)
    monkeypatch.setenv("SDD_GOVERNANCE_MODE", "hard")
    with pytest.raises(ValueError, match="requires authenticated remote"):
        HttpProvider()


def test_local_without_token_accepted_in_hard_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://localhost:8080")
    monkeypatch.delenv("SDD_INTELLIGENCE_TOKEN", raising=False)
    monkeypatch.setenv("SDD_GOVERNANCE_MODE", "hard")
    provider = HttpProvider()
    assert provider._url == "http://localhost:8080"


def test_auth_headers_include_bearer_token_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_auth_headers returns a Bearer header when SDD_INTELLIGENCE_TOKEN is set."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://intel.example.com")
    monkeypatch.setenv("SDD_INTELLIGENCE_TOKEN", "secret-token")
    provider = HttpProvider()
    assert provider._auth_headers() == {"Authorization": "Bearer secret-token"}


def test_auth_headers_empty_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """_auth_headers returns no headers when no token is configured."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://localhost:8080")
    monkeypatch.delenv("SDD_INTELLIGENCE_TOKEN", raising=False)
    provider = HttpProvider()
    assert provider._auth_headers() == {}


@pytest.mark.asyncio
async def test_is_available_false_when_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_available() returns False when no URL configured."""
    monkeypatch.delenv("SDD_INTELLIGENCE_URL", raising=False)
    provider = HttpProvider()
    assert await provider.is_available() is False


@pytest.mark.asyncio
async def test_is_available_false_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_available() returns False when health check fails."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://127.0.0.1:9")
    provider = HttpProvider()
    result = await provider.is_available()
    assert result is False


@pytest.mark.asyncio
async def test_analyze_task_returns_degraded_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """analyze_task returns degraded result when service unreachable."""
    from unittest.mock import AsyncMock, patch

    from providence_runtime.intelligence import TaskContext

    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://nonexistent.internal")
    provider = HttpProvider()

    with patch.object(provider, "is_available", new=AsyncMock(return_value=False)):
        task = TaskContext(
            query="test",
            path_id="A",
            context_bytes_loaded=0,
            context_budget_bytes=100_000,
        )
        result = await provider.analyze_task(task)

    assert result.provider == "http"
    assert result.task_class == "unknown"
