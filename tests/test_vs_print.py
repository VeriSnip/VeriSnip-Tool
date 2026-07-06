import sys
from io import StringIO
from unittest.mock import patch

from VeriSnip import vs_colours


def _capture_print(modifier, message, argv):
    with patch.object(sys, "argv", argv):
        buf = StringIO()
        with patch("sys.stdout", buf):
            vs_colours.vs_print(modifier, message)
        return buf.getvalue()


def test_note_only_with_debug():
    assert _capture_print(vs_colours.NOTE, "hint", ["vs_build"]) == ""
    assert "NOTE" in _capture_print(vs_colours.NOTE, "hint", ["vs_build", "--debug"])


def test_warning_hidden_in_quiet():
    assert _capture_print(vs_colours.WARNING, "warn", ["vs_build", "--quiet"]) == ""
    assert "Warning" in _capture_print(vs_colours.WARNING, "warn", ["vs_build"])


def test_error_and_ok_shown_in_quiet():
    assert "Error" in _capture_print(vs_colours.ERROR, "fail", ["vs_build", "--quiet"])
    assert "Done" in _capture_print(vs_colours.OK, "ok", ["vs_build", "--quiet"])


def test_info_hidden_in_quiet():
    assert _capture_print(vs_colours.INFO, "info", ["vs_build", "--quiet"]) == ""
