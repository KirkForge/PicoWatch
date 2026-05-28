"""PicoWatch CLI smoke tests."""

from picowatch.cli import main


def test_cli_no_args_shows_help(capsys):
    """Calling picowatch with no args prints help and exits 1."""
    try:
        main([])
    except SystemExit as exc:
        assert exc.code == 1
    captured = capsys.readouterr()
    assert "picowatch" in captured.out or "picowatch" in captured.err
