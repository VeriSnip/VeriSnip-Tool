"""Tests for vs_cli: argument parsing, pre/post-build script discovery,
script execution, and top-level orchestration in main()."""

import os
import sys
from pathlib import Path

import pytest

from VeriSnip import vs_cli


# ---------------------------------------------------------------------------
# find_default_script
# ---------------------------------------------------------------------------

def test_find_default_script_returns_none_when_absent(tmp_path: Path):
    assert vs_cli.find_default_script(str(tmp_path), "pre_build") is None


def test_find_default_script_returns_single_match(tmp_path: Path):
    script = tmp_path / "pre_build.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")

    found = vs_cli.find_default_script(str(tmp_path), "pre_build")

    assert found == str(script)


def test_find_default_script_ignores_other_stems(tmp_path: Path):
    (tmp_path / "post_build.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    assert vs_cli.find_default_script(str(tmp_path), "pre_build") is None


def test_find_default_script_exits_on_multiple_matches(tmp_path: Path):
    (tmp_path / "pre_build.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "pre_build.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        vs_cli.find_default_script(str(tmp_path), "pre_build")

    assert excinfo.value.code == 1


# ---------------------------------------------------------------------------
# parse_arguments
# ---------------------------------------------------------------------------

def _parse(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["vs_build", *argv])
    return vs_cli.parse_arguments()


def test_testbench_defaults_from_module_name(monkeypatch):
    module_name, testbench, *_ = _parse(monkeypatch, ["top"])
    assert module_name == "top"
    assert testbench == "top_tb"


def test_explicit_testbench_is_kept(monkeypatch):
    _, testbench, *_ = _parse(monkeypatch, ["top", "--TestBench", "my_tb"])
    assert testbench == "my_tb"


def test_underscore_prefixed_testbench_expands_with_module_name(monkeypatch):
    _, testbench, *_ = _parse(monkeypatch, ["top", "--TestBench", "_alt_tb"])
    assert testbench == "top_alt_tb"


def test_whitespace_only_testbench_value_exits(monkeypatch):
    # An empty string ("--TestBench=") is falsy and bypasses the emptiness
    # check entirely; only a whitespace-only value actually triggers it.
    monkeypatch.setattr(sys, "argv", ["vs_build", "top", "--TestBench", " "])
    with pytest.raises(SystemExit) as excinfo:
        vs_cli.parse_arguments()
    assert excinfo.value.code == 1


def test_empty_testbench_value_is_kept_as_is(monkeypatch):
    # Documents current behavior: "--TestBench=" yields "" rather than the
    # <module>_tb default, since the emptiness check only matches truthy values.
    _, testbench, *_ = _parse(monkeypatch, ["top", "--TestBench="])
    assert testbench == ""


def test_boards_are_split_and_prefix_expanded(monkeypatch):
    _, _, board_modules, *_ = _parse(monkeypatch, ["top", "--Boards", "BoardA _BoardB"])
    assert board_modules == ["BoardA", "top_BoardB"]


def test_invalid_board_name_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["vs_build", "top", "--Boards", "bad/board"])
    with pytest.raises(SystemExit) as excinfo:
        vs_cli.parse_arguments()
    assert excinfo.value.code == 1


def test_include_dirs_are_split(monkeypatch):
    _, _, _, include_dirs, *_ = _parse(monkeypatch, ["top", "--inc_dir", "./rtl ../shared"])
    assert include_dirs == ["./rtl", "../shared"]


def test_invalid_include_dir_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["vs_build", "top", "--inc_dir", "good !bad"])
    with pytest.raises(SystemExit) as excinfo:
        vs_cli.parse_arguments()
    assert excinfo.value.code == 1


def test_unknown_flag_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["vs_build", "top", "--nonsense"])
    with pytest.raises(SystemExit) as excinfo:
        vs_cli.parse_arguments()
    assert excinfo.value.code == 1


def test_extra_positional_args_are_left_for_forwarding(monkeypatch):
    module_name, *_ = _parse(monkeypatch, ["top", "EXTRA_FLAG=1"])
    assert module_name == "top"
    # Extra positionals are intentionally not returned; they stay in sys.argv.
    assert "EXTRA_FLAG=1" in sys.argv


def test_clean_and_pre_post_build_flags_are_returned(monkeypatch):
    (
        _,
        _,
        _,
        _,
        clean,
        pre_build,
        post_build,
    ) = _parse(
        monkeypatch,
        ["top", "--clean", "--pre-build", "setup.sh", "--post-build", "cleanup.sh"],
    )
    assert clean is True
    assert pre_build == "setup.sh"
    assert post_build == "cleanup.sh"


def test_pre_post_build_default_to_none_when_omitted(monkeypatch):
    *_, pre_build, post_build = _parse(monkeypatch, ["top"])
    assert pre_build is None
    assert post_build is None


# ---------------------------------------------------------------------------
# run_script
# ---------------------------------------------------------------------------

def _write_script(path: Path, body: str, executable: bool = True) -> None:
    path.write_text(body, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    else:
        path.chmod(0o644)


def test_run_script_executes_absolute_path(tmp_path: Path):
    marker = tmp_path / "marker.txt"
    script = tmp_path / "script.sh"
    _write_script(script, f"#!/bin/sh\ntouch {marker}\n")

    vs_cli.run_script(str(script), "pre-build")

    assert marker.is_file()


def test_run_script_resolves_relative_path_against_cwd(tmp_path: Path, monkeypatch):
    marker = tmp_path / "marker.txt"
    script = tmp_path / "script.sh"
    _write_script(script, f"#!/bin/sh\ntouch {marker}\n")
    monkeypatch.chdir(tmp_path)

    vs_cli.run_script("script.sh", "pre-build")

    assert marker.is_file()


def test_run_script_missing_file_exits(tmp_path: Path):
    with pytest.raises(SystemExit) as excinfo:
        vs_cli.run_script(str(tmp_path / "does_not_exist.sh"), "pre-build")
    assert excinfo.value.code == 1


def test_run_script_nonzero_exit_code_exits(tmp_path: Path):
    script = tmp_path / "fail.sh"
    _write_script(script, "#!/bin/sh\nexit 3\n")

    with pytest.raises(SystemExit) as excinfo:
        vs_cli.run_script(str(script), "pre-build")

    assert excinfo.value.code == 1


def test_run_script_not_executable_exits(tmp_path: Path):
    script = tmp_path / "not_exec.sh"
    _write_script(script, "#!/bin/sh\nexit 0\n", executable=False)

    with pytest.raises(SystemExit) as excinfo:
        vs_cli.run_script(str(script), "pre-build")

    assert excinfo.value.code == 1


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class _FakeBuilder:
    events: list[str] = []

    def __init__(self, main_module, testbench, board_modules, include_directories):
        self.main_module = main_module
        _FakeBuilder.events.append("init")

    def resolve_sources(self):
        _FakeBuilder.events.append("resolve")

    def build_sources(self):
        _FakeBuilder.events.append("build")


@pytest.fixture
def fake_builder(monkeypatch):
    _FakeBuilder.events = []
    monkeypatch.setattr(vs_cli, "VsBuilder", _FakeBuilder)
    return _FakeBuilder


def test_main_prints_help_and_returns_with_no_args(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["vs_build"])

    vs_cli.main()  # must not raise

    assert "usage" in capsys.readouterr().out.lower()


def test_main_errors_when_module_name_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["vs_build", "--quiet"])

    with pytest.raises(SystemExit) as excinfo:
        vs_cli.main()

    assert excinfo.value.code == 1


def test_main_builds_module_via_vsbuilder(monkeypatch, tmp_path, fake_builder):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["vs_build", "top"])

    vs_cli.main()

    assert fake_builder.events == ["init", "resolve", "build"]


def test_main_runs_explicit_pre_and_post_build_scripts_in_order(monkeypatch, tmp_path, fake_builder):
    order_file = tmp_path / "order.txt"
    pre = tmp_path / "pre.sh"
    post = tmp_path / "post.sh"
    _write_script(pre, f"#!/bin/sh\necho pre >> {order_file}\n")
    _write_script(post, f"#!/bin/sh\necho post >> {order_file}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["vs_build", "top", "--pre-build", "pre.sh", "--post-build", "post.sh"],
    )

    vs_cli.main()

    assert order_file.read_text(encoding="utf-8").splitlines() == ["pre", "post"]
    assert fake_builder.events == ["init", "resolve", "build"]


def test_main_discovers_default_pre_and_post_build_scripts(monkeypatch, tmp_path, fake_builder):
    order_file = tmp_path / "order.txt"
    _write_script(tmp_path / "pre_build.sh", f"#!/bin/sh\necho pre >> {order_file}\n")
    _write_script(tmp_path / "post_build.sh", f"#!/bin/sh\necho post >> {order_file}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["vs_build", "top"])

    vs_cli.main()

    assert order_file.read_text(encoding="utf-8").splitlines() == ["pre", "post"]


def test_main_explicit_flag_overrides_default_discovery(monkeypatch, tmp_path, fake_builder):
    order_file = tmp_path / "order.txt"
    _write_script(tmp_path / "pre_build.sh", f"#!/bin/sh\necho default >> {order_file}\n")
    _write_script(tmp_path / "explicit.sh", f"#!/bin/sh\necho explicit >> {order_file}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["vs_build", "top", "--pre-build", "explicit.sh"])

    vs_cli.main()

    assert order_file.read_text(encoding="utf-8").splitlines() == ["explicit"]


def test_main_errors_on_nonexistent_explicit_pre_build_script(monkeypatch, tmp_path, fake_builder):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["vs_build", "top", "--pre-build", "missing.sh"])

    with pytest.raises(SystemExit) as excinfo:
        vs_cli.main()

    assert excinfo.value.code == 1
    assert fake_builder.events == []


def test_main_clean_invokes_clean_build(monkeypatch, tmp_path):
    called_with = []
    monkeypatch.setattr(vs_cli, "clean_build", lambda directory: called_with.append(directory))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["vs_build", "--clean"])

    with pytest.raises(SystemExit) as excinfo:
        vs_cli.main()

    assert called_with == [str(tmp_path)]
    # --clean without a module name still exits 1 (no build was requested).
    assert excinfo.value.code == 1
