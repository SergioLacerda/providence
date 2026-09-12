"""Unit tests for AlertDispatcher HTTPS enforcement."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from providence_runtime.alerts import AlertDispatcher

pytestmark = pytest.mark.unit


class TestAlertDispatcherHttpsEnforcement:
    """Tests for HTTPS requirement in AlertDispatcher."""

    def test_https_url_accepted(self) -> None:
        """HTTPS URLs should be accepted by default."""
        dispatcher = AlertDispatcher(url="https://example.com/webhook")
        assert dispatcher._url == "https://example.com/webhook"

    def test_http_url_rejected_by_default(self) -> None:
        """HTTP URLs should be rejected by default."""
        with pytest.raises(ValueError, match="not secure"):
            AlertDispatcher(url="http://example.com/webhook")

    def test_http_url_accepted_with_flag(self) -> None:
        """HTTP URLs should be accepted when allow_http=True."""
        dispatcher = AlertDispatcher(url="http://example.com/webhook", allow_http=True)
        assert dispatcher._url == "http://example.com/webhook"

    def test_error_message_mentions_https(self) -> None:
        """Error message should recommend HTTPS."""
        with pytest.raises(ValueError, match="HTTPS"):
            AlertDispatcher(url="http://localhost:8000/webhook")

    def test_error_message_mentions_allow_http_flag(self) -> None:
        """Error message should mention the allow_http escape hatch."""
        with pytest.raises(ValueError, match="allow_http=True"):
            AlertDispatcher(url="http://internal.example.com/webhook")

    def test_various_https_urls(self) -> None:
        """Various HTTPS URLs should be accepted."""
        urls = [
            "https://example.com/webhook",
            "https://api.example.com/v1/webhook",
            "https://localhost:443/webhook",
            "https://192.168.1.1:8443/webhook",
        ]
        for url in urls:
            dispatcher = AlertDispatcher(url=url)
            assert dispatcher._url == url

    def test_various_http_urls_rejected(self) -> None:
        """Various HTTP URLs should be rejected."""
        urls = [
            "http://example.com/webhook",
            "http://api.example.com/v1/webhook",
            "http://localhost:8000/webhook",
            "http://192.168.1.1:8000/webhook",
        ]
        for url in urls:
            with pytest.raises(ValueError, match="not secure"):
                AlertDispatcher(url=url)

    def test_invalid_scheme_silently_skipped(self) -> None:
        """Invalid schemes should be silently skipped during posting."""
        # file://, ftp://, etc. should be rejected at post time
        dispatcher = AlertDispatcher(
            url="file:///tmp/webhook", allow_http=True
        )  # allow_http doesn't apply to file://
        # The validation happens at __init__ time for http/https, not file://
        # file:// should fail at post time, not init time
        assert dispatcher._url == "file:///tmp/webhook"

    def test_environment_variable_respects_https(self) -> None:
        """from_env() should respect HTTPS enforcement."""
        with patch.dict(
            os.environ,
            {
                "SDD_WEBHOOK_URL": "https://example.com/webhook",
                "SDD_WEBHOOK_TYPE": "generic",
            },
        ):
            dispatcher = AlertDispatcher.from_env()
            assert dispatcher is not None
            assert dispatcher._url == "https://example.com/webhook"

    def test_environment_variable_http_rejected(self) -> None:
        """from_env() should reject HTTP by default."""
        with (
            patch.dict(
                os.environ,
                {
                    "SDD_WEBHOOK_URL": "http://example.com/webhook",
                    "SDD_WEBHOOK_TYPE": "generic",
                },
            ),
            pytest.raises(ValueError, match="not secure"),
        ):
            AlertDispatcher.from_env()

    def test_environment_variable_http_allowed_with_flag(self) -> None:
        """from_env() should allow HTTP with SDD_WEBHOOK_ALLOW_HTTP=true."""
        with patch.dict(
            os.environ,
            {
                "SDD_WEBHOOK_URL": "http://localhost:8000/webhook",
                "SDD_WEBHOOK_TYPE": "generic",
                "SDD_WEBHOOK_ALLOW_HTTP": "true",
            },
        ):
            dispatcher = AlertDispatcher.from_env()
            assert dispatcher is not None
            assert dispatcher._url == "http://localhost:8000/webhook"

    def test_allow_http_flag_case_insensitive(self) -> None:
        """SDD_WEBHOOK_ALLOW_HTTP flag parsing should be case-insensitive."""
        with patch.dict(
            os.environ,
            {
                "SDD_WEBHOOK_URL": "http://example.com/webhook",
                "SDD_WEBHOOK_ALLOW_HTTP": "True",  # Capital T should also work
            },
        ):
            # Should accept because .lower() makes it "true"
            dispatcher = AlertDispatcher.from_env()
            assert dispatcher is not None
            assert dispatcher._url == "http://example.com/webhook"

    def test_allow_http_empty_string_treated_as_false(self) -> None:
        """Empty SDD_WEBHOOK_ALLOW_HTTP should be treated as false."""
        with (
            patch.dict(
                os.environ,
                {
                    "SDD_WEBHOOK_URL": "http://example.com/webhook",
                    "SDD_WEBHOOK_ALLOW_HTTP": "",
                },
            ),
            pytest.raises(ValueError, match="not secure"),
        ):
            AlertDispatcher.from_env()


class TestAlertDispatcherPostWithHttps:
    """Tests for webhook posting with HTTPS enforcement."""

    @patch("urllib.request.urlopen")
    def test_posts_to_https_endpoint(self, mock_urlopen: MagicMock) -> None:
        """Should successfully post to HTTPS endpoints."""
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        dispatcher = AlertDispatcher(url="https://example.com/webhook")
        dispatcher._post({"event": "test", "data": "value"})

        # Verify the post was attempted
        assert mock_urlopen.called

    @patch("urllib.request.urlopen")
    def test_posts_to_http_when_allowed(self, mock_urlopen: MagicMock) -> None:
        """Should post to HTTP when explicitly allowed."""
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        dispatcher = AlertDispatcher(
            url="http://localhost:8000/webhook", allow_http=True
        )
        dispatcher._post({"event": "test"})

        assert mock_urlopen.called

    def test_rejects_non_http_schemes_at_post_time(self) -> None:
        """Non-HTTP(S) schemes should be silently skipped at post time."""
        # This dispatcher might be created with file:// URL (if allow_http=True permits it)
        # but _post should silently skip it
        dispatcher = AlertDispatcher(
            url="file:///tmp/webhook", allow_http=True
        )  # allow_http doesn't affect file://
        # _post should silently skip non-http(s) schemes
        dispatcher._post({"event": "test"})
        # No assertion needed — the test passes if no exception is raised

    @patch("urllib.request.urlopen")
    def test_silently_handles_network_errors(self, mock_urlopen: MagicMock) -> None:
        """Should silently handle network errors during webhook posting."""
        mock_urlopen.side_effect = Exception("Network error")

        dispatcher = AlertDispatcher(url="https://example.com/webhook")
        # Should not raise — exceptions are silently suppressed
        dispatcher._post({"event": "test"})

        # Verify urlopen was called even though it failed
        assert mock_urlopen.called

    @patch("urllib.request.urlopen")
    def test_silently_handles_timeout_errors(self, mock_urlopen: MagicMock) -> None:
        """Should silently handle timeout errors during webhook posting."""

        mock_urlopen.side_effect = TimeoutError("Connection timeout")

        dispatcher = AlertDispatcher(url="https://example.com/webhook")
        # Should not raise — exceptions are silently suppressed
        dispatcher._post({"event": "test"})

        assert mock_urlopen.called


class TestAlertDispatcherEnv:
    """Tests for AlertDispatcher environment variable configuration."""

    def test_from_env_returns_none_when_url_missing(self) -> None:
        """from_env() should return None when SDD_WEBHOOK_URL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            dispatcher = AlertDispatcher.from_env()
            assert dispatcher is None

    def test_from_env_returns_none_when_url_empty(self) -> None:
        """from_env() should return None when SDD_WEBHOOK_URL is empty."""
        with patch.dict(os.environ, {"SDD_WEBHOOK_URL": ""}, clear=True):
            dispatcher = AlertDispatcher.from_env()
            assert dispatcher is None

    def test_from_env_configures_all_options(self) -> None:
        """from_env() should configure all environment options."""
        with patch.dict(
            os.environ,
            {
                "SDD_WEBHOOK_URL": "https://example.com/webhook",
                "SDD_WEBHOOK_TYPE": "slack",
                "SDD_WEBHOOK_TIMEOUT": "10",
                "SDD_WEBHOOK_EVENTS": "event1,event2,event3",
            },
        ):
            dispatcher = AlertDispatcher.from_env()
            assert dispatcher is not None
            assert dispatcher._url == "https://example.com/webhook"
            assert dispatcher._webhook_type == "slack"
            assert dispatcher._timeout == 10
            assert "event1" in dispatcher._events
            assert "event2" in dispatcher._events
            assert "event3" in dispatcher._events


class TestAlertDispatcherPayloadBuilding:
    """Tests for webhook payload building."""

    def test_pagerduty_payload_building(self) -> None:
        """Should build PagerDuty payload correctly."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook", webhook_type="pagerduty"
        )
        event_dict = {
            "event": "economy.budget.breach",
            "agent_id": "agent-123",
            "budget_utilization_pct": 95.5,
            "path_id": "A",
            "ts": "2026-05-15T10:00:00Z",
        }
        payload = dispatcher._build_pagerduty_payload(event_dict)

        assert "routing_key" in payload
        assert "event_action" in payload
        assert payload["event_action"] == "trigger"
        assert "payload" in payload
        assert "summary" in payload["payload"]
        assert "severity" in payload["payload"]

    def test_slack_payload_building(self) -> None:
        """Should build Slack payload correctly."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook", webhook_type="slack"
        )
        event_dict = {
            "event": "economy.budget.breach",
            "agent_id": "agent-123",
            "budget_utilization_pct": 95.5,
            "path_id": "A",
        }
        payload = dispatcher._build_slack_payload(event_dict)

        assert "text" in payload
        assert "CRITICAL:" in payload["text"]
        assert ":fire:" in payload["text"]

    def test_generic_payload_building(self) -> None:
        """Should build generic payload (returns event dict as-is)."""
        dispatcher = AlertDispatcher(url="https://example.com/webhook")
        event_dict = {"event": "test.event", "data": "value"}
        payload = dispatcher._build_generic_payload(event_dict)

        assert payload == event_dict

    def test_pagerduty_severity_critical_for_breach(self) -> None:
        """PagerDuty payload should mark breach events as critical."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook", webhook_type="pagerduty"
        )
        event_dict = {"event": "economy.budget.breach"}
        payload = dispatcher._build_pagerduty_payload(event_dict)

        assert payload["payload"]["severity"] == "critical"

    def test_pagerduty_severity_warning_for_non_breach(self) -> None:
        """PagerDuty payload should mark non-breach events as warning."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook", webhook_type="pagerduty"
        )
        event_dict = {"event": "economy.budget.warn"}
        payload = dispatcher._build_pagerduty_payload(event_dict)

        assert payload["payload"]["severity"] == "warning"

    def test_slack_emoji_fire_for_breach(self) -> None:
        """Slack payload should use fire emoji for breach events."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook", webhook_type="slack"
        )
        event_dict = {"event": "economy.budget.breach"}
        payload = dispatcher._build_slack_payload(event_dict)

        assert ":fire:" in payload["text"]
        assert "CRITICAL:" in payload["text"]

    def test_slack_emoji_warning_for_non_breach(self) -> None:
        """Slack payload should use warning emoji for non-breach events."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook", webhook_type="slack"
        )
        event_dict = {"event": "economy.budget.warn"}
        payload = dispatcher._build_slack_payload(event_dict)

        assert ":warning:" in payload["text"]
        assert "WARNING:" in payload["text"]


class TestAlertDispatcherEventDispatching:
    """Tests for event dispatching logic."""

    @patch.object(AlertDispatcher, "_post")
    def test_dispatches_matching_events(self, mock_post: MagicMock) -> None:
        """Should dispatch events that match the trigger set."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook",
            events=frozenset({"economy.budget.breach"}),
        )
        event_dict = {"event": "economy.budget.breach"}
        dispatcher.on_event(event_dict)

        mock_post.assert_called_once()

    @patch.object(AlertDispatcher, "_post")
    def test_skips_non_matching_events(self, mock_post: MagicMock) -> None:
        """Should skip events that don't match the trigger set."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook",
            events=frozenset({"economy.budget.breach"}),
        )
        event_dict = {"event": "other.event"}
        dispatcher.on_event(event_dict)

        mock_post.assert_not_called()

    @patch.object(AlertDispatcher, "_post")
    def test_dispatches_pagerduty_payload(self, mock_post: MagicMock) -> None:
        """Should dispatch PagerDuty payload for PagerDuty webhook type."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook",
            webhook_type="pagerduty",
            events=frozenset({"economy.budget.breach"}),
        )
        event_dict = {"event": "economy.budget.breach", "agent_id": "test"}
        dispatcher.on_event(event_dict)

        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        assert "routing_key" in payload

    @patch.object(AlertDispatcher, "_post")
    def test_dispatches_slack_payload(self, mock_post: MagicMock) -> None:
        """Should dispatch Slack payload for Slack webhook type."""
        dispatcher = AlertDispatcher(
            url="https://example.com/webhook",
            webhook_type="slack",
            events=frozenset({"economy.budget.breach"}),
        )
        event_dict = {"event": "economy.budget.breach"}
        dispatcher.on_event(event_dict)

        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        assert "text" in payload


class TestAlertDispatcherPostFailureLogging:
    """Tests for best-effort dispatch failure visibility."""

    @patch("urllib.request.urlopen")
    def test_dispatch_failure_is_logged_as_warning(
        self, mock_urlopen: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When _post raises, a warning is logged instead of silently suppressed."""
        import logging

        mock_urlopen.side_effect = OSError("connection refused")
        dispatcher = AlertDispatcher(url="https://example.com/webhook")

        with caplog.at_level(logging.WARNING, logger="providence_runtime.alerts"):
            dispatcher._post({"event": "test"})

        assert any("alert dispatch failed" in r.message for r in caplog.records)

    @patch("urllib.request.urlopen")
    def test_dispatch_failure_does_not_propagate(self, mock_urlopen: MagicMock) -> None:
        """Dispatch failure must not propagate — best-effort semantics are preserved."""
        mock_urlopen.side_effect = OSError("connection refused")
        dispatcher = AlertDispatcher(url="https://example.com/webhook")
        events = frozenset({"economy.budget.breach"})
        dispatcher._events = events

        # on_event must not raise even when _post fails
        dispatcher.on_event({"event": "economy.budget.breach"})
