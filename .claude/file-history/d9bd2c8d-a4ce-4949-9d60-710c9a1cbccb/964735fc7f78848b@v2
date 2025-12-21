from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.alerts.dingtalk import DingTalkConfig, _sign, send_markdown


def test_sign_generates_valid_signature() -> None:
    secret = "test_secret"
    timestamp_ms = 1234567890000
    sig = _sign(secret, timestamp_ms)
    assert isinstance(sig, str)
    assert len(sig) > 0


def test_send_markdown_without_secret() -> None:
    cfg = DingTalkConfig(webhook_url="https://example.com/webhook")

    with patch("src.alerts.dingtalk.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_markdown(cfg, "Test Title", "Test **content**")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # First positional arg is URL
        url = call_args[0][0]
        assert url == "https://example.com/webhook"
        assert call_args.kwargs["json"]["msgtype"] == "markdown"
        assert call_args.kwargs["json"]["markdown"]["title"] == "Test Title"


def test_send_markdown_with_secret_appends_signature() -> None:
    cfg = DingTalkConfig(webhook_url="https://example.com/webhook", secret="mysecret")

    with (
        patch("src.alerts.dingtalk.requests.post") as mock_post,
        patch("src.alerts.dingtalk.time.time", return_value=1234567890.123),
    ):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_markdown(cfg, "Title", "Content")

        call_args = mock_post.call_args
        url = call_args[0][0]
        assert "timestamp=" in url
        assert "sign=" in url


def test_send_markdown_with_secret_and_query_string() -> None:
    cfg = DingTalkConfig(webhook_url="https://example.com/webhook?token=abc", secret="mysecret")

    with (
        patch("src.alerts.dingtalk.requests.post") as mock_post,
        patch("src.alerts.dingtalk.time.time", return_value=1234567890.123),
    ):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_markdown(cfg, "Title", "Content")

        call_args = mock_post.call_args
        url = call_args[0][0]
        # Should use & instead of ? since URL already has query string
        assert "&timestamp=" in url
