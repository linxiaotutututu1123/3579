from __future__ import annotations

from unittest.mock import patch

from src.main import main


def test_main_runs_without_env_file() -> None:
    with patch("src.main.Path.exists", return_value=False):
        with patch("builtins.print") as mock_print:
            main()

            assert mock_print.call_count == 3
            calls = [str(c) for c in mock_print.call_args_list]
            assert any("boot OK" in c for c in calls)


def test_main_loads_env_file_when_exists() -> None:
    with patch("src.main.Path.exists", return_value=True):
        with patch("src.main.load_dotenv") as mock_load:
            with patch("builtins.print"):
                main()

                mock_load.assert_called_once()
