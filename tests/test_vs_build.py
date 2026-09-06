"""Tests for build directory population and its supporting directory helpers
in vs_build: build_sources/build_verilog_sources, clean_build, create_directory,
and remove_directory."""

import os
from pathlib import Path

from VeriSnip import vs_build
from VeriSnip.vs_build import (
    VsBuilder,
    build_verilog_sources,
    clean_build,
    create_directory,
    remove_directory,
)


# ---------------------------------------------------------------------------
# build_verilog_sources
# ---------------------------------------------------------------------------

def test_build_verilog_sources_writes_substituted_content(tmp_path: Path):
    src = tmp_path / "top.v"
    src.write_text(
        "module top #(\n"
        "    `include \"params.vs\"\n"
        ") (\n"
        "  input clk\n"
        ");\n"
        "endmodule\n",
        encoding="utf-8",
    )
    params = tmp_path / "params.vs"
    params.write_text("    parameter integer A = 1,\n", encoding="utf-8")
    build_dir = tmp_path / "build_out"

    build_verilog_sources([str(src), str(params)], str(build_dir))

    out = build_dir / "top.v"
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "parameter integer A = 1\n) (" in content
    assert "`include" not in content


def test_build_verilog_sources_ignores_vs_files_directly(tmp_path: Path):
    src = tmp_path / "top.v"
    src.write_text("module top;\nendmodule\n", encoding="utf-8")
    snippet = tmp_path / "unused.vs"
    snippet.write_text("wire unused;\n", encoding="utf-8")
    build_dir = tmp_path / "build_out"

    build_verilog_sources([str(src), str(snippet)], str(build_dir))

    assert (build_dir / "top.v").is_file()
    assert not (build_dir / "unused.vs").exists()


def test_build_verilog_sources_skips_rewrite_when_content_unchanged(tmp_path: Path):
    src = tmp_path / "top.v"
    src.write_text("module top;\nendmodule\n", encoding="utf-8")
    build_dir = tmp_path / "build_out"

    build_verilog_sources([str(src)], str(build_dir))
    out = build_dir / "top.v"
    stale_mtime_ns = out.stat().st_mtime_ns - 10**9
    os.utime(out, ns=(stale_mtime_ns, stale_mtime_ns))

    build_verilog_sources([str(src)], str(build_dir))

    assert out.stat().st_mtime_ns == stale_mtime_ns


def test_build_verilog_sources_rewrites_when_content_changes(tmp_path: Path):
    src = tmp_path / "top.v"
    src.write_text("module top;\nendmodule\n", encoding="utf-8")
    build_dir = tmp_path / "build_out"

    build_verilog_sources([str(src)], str(build_dir))
    out = build_dir / "top.v"
    stale_mtime_ns = out.stat().st_mtime_ns - 10**9
    os.utime(out, ns=(stale_mtime_ns, stale_mtime_ns))

    src.write_text("module top;\n  wire changed;\nendmodule\n", encoding="utf-8")
    build_verilog_sources([str(src)], str(build_dir))

    assert out.stat().st_mtime_ns != stale_mtime_ns
    assert "wire changed;" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# VsBuilder.build_sources (end to end)
# ---------------------------------------------------------------------------

def _write_full_project(tmp: Path) -> None:
    (tmp / "top.v").write_text(
        "module top #(\n"
        "    `include \"params.vs\"\n"
        ") (\n"
        "  input clk\n"
        ");\n"
        "endmodule\n",
        encoding="utf-8",
    )
    (tmp / "params.vs").write_text("    parameter integer A = 1,\n", encoding="utf-8")
    (tmp / "top_tb.v").write_text(
        "module top_tb;\n"
        "  top dut (.clk(clk));\n"
        "endmodule\n",
        encoding="utf-8",
    )
    (tmp / "boardA.v").write_text(
        "module boardA;\n"
        "  top dut (.clk(clk));\n"
        "endmodule\n",
        encoding="utf-8",
    )


def test_build_sources_populates_rtl_testbench_and_board_dirs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_full_project(tmp_path)

    builder = VsBuilder("top", "top_tb", ["boardA"], [])
    builder.resolve_sources()
    builder.build_sources()

    build_dir = tmp_path / "build"

    rtl_content = (build_dir / "RTL" / "top.v").read_text(encoding="utf-8")
    assert "parameter integer A = 1\n) (" in rtl_content
    assert "`include" not in rtl_content

    tb_files = {p.name for p in (build_dir / "TestBench").iterdir()}
    assert tb_files == {"top_tb.v"}  # top.v is excluded: already built under RTL

    board_files = {p.name for p in (build_dir / "boardA").iterdir()}
    assert board_files == {"boardA.v"}  # top.v is excluded: already built under RTL


# ---------------------------------------------------------------------------
# create_directory / remove_directory / clean_build
# ---------------------------------------------------------------------------

def test_create_directory_creates_nested_path(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c"

    create_directory(str(target))

    assert target.is_dir()


def test_create_directory_is_idempotent(tmp_path: Path):
    target = tmp_path / "a"
    create_directory(str(target))

    create_directory(str(target))  # must not raise

    assert target.is_dir()


def test_remove_directory_removes_existing_dir_and_contents(tmp_path: Path):
    target = tmp_path / "build"
    (target / "sub").mkdir(parents=True)
    (target / "sub" / "file.txt").write_text("x", encoding="utf-8")

    remove_directory(str(target))

    assert not target.exists()


def test_remove_directory_is_noop_when_absent(tmp_path: Path):
    target = tmp_path / "does_not_exist"

    remove_directory(str(target))  # must not raise

    assert not target.exists()


def test_remove_directory_handles_oserror_gracefully(tmp_path: Path, monkeypatch):
    target = tmp_path / "locked"
    target.mkdir()

    def boom(path):
        raise OSError("permission denied")

    monkeypatch.setattr(vs_build.shutil, "rmtree", boom)

    remove_directory(str(target))  # must not raise despite rmtree failing


def test_clean_build_removes_build_and_generated_dirs(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "generated").mkdir()
    (tmp_path / "build" / "keepme.txt").write_text("x", encoding="utf-8")

    clean_build(str(tmp_path))

    assert not (tmp_path / "build").exists()
    assert not (tmp_path / "generated").exists()


def test_clean_build_noop_when_nothing_to_clean(tmp_path: Path):
    clean_build(str(tmp_path))  # must not raise
