"""Tests for VsSource.generate(): running a matched generator script and
handling its success/failure/no-output outcomes."""

from pathlib import Path

import pytest

from VeriSnip.vs_build import VsBuilder


def _write_script(path: Path, body: str, executable: bool = True) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)


def test_generate_returns_empty_list_when_no_script_matches(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    source = VsBuilder.VsSource("widget")

    result = source.generate([])

    assert result == []
    assert "no script found" in capsys.readouterr().out


def test_generate_runs_matching_script_and_relocates_output(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "generated").mkdir()
    script = tmp_path / "widget.py"
    _write_script(
        script,
        "#!/usr/bin/env python3\n"
        "with open('widget.v', 'w') as f:\n"
        "    f.write('module widget;\\nendmodule\\n')\n",
    )

    source = VsBuilder.VsSource("widget")
    result = source.generate([str(script)])

    generated_path = tmp_path / "generated" / "widget.v"
    assert result == [str(generated_path)]
    assert source.directory == str(generated_path)
    assert generated_path.read_text(encoding="utf-8") == "module widget;\nendmodule\n"


def test_generate_warns_when_script_produces_no_output_files(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "generated").mkdir()
    script = tmp_path / "widget.py"
    _write_script(script, "#!/usr/bin/env python3\n")  # produces nothing

    source = VsBuilder.VsSource("widget")
    result = source.generate([str(script)])

    assert result == []
    assert "generated no Verilog or VeriSnip files" in capsys.readouterr().out


def test_generate_exits_when_script_fails(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "generated").mkdir()
    script = tmp_path / "widget.py"
    _write_script(script, "#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n")

    source = VsBuilder.VsSource("widget")
    with pytest.raises(SystemExit) as excinfo:
        source.generate([str(script)])
    assert excinfo.value.code == 1


def test_generate_exits_when_script_not_executable(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "generated").mkdir()
    script = tmp_path / "widget.py"
    _write_script(script, "#!/usr/bin/env python3\n", executable=False)

    source = VsBuilder.VsSource("widget")
    with pytest.raises(SystemExit) as excinfo:
        source.generate([str(script)])
    assert excinfo.value.code == 1
