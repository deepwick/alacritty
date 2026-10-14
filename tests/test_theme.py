import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from deepwick_spec.check_port import check_port
from deepwick_spec.palette import ANSI_SLOTS, load_palette

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors


def theme():
    path = REPO / "deepwick.toml"
    assert path.is_file(), "deepwick.toml missing"
    return tomllib.loads(path.read_text(encoding="utf-8"))["colors"]


def test_ansi_colors():
    t = theme()
    for slot in ANSI_SLOTS:
        assert t["normal"][slot] == PALETTE.ansi[slot], slot
        assert t["bright"][slot] == PALETTE.ansi["bright" + slot.capitalize()], slot


def test_primary_cursor_selection():
    t = theme()
    assert t["primary"] == {"background": C["background"], "foreground": C["foreground"], "bright_foreground": C["white"]}
    assert t["cursor"] == {"text": C["background"], "cursor": C["foreground"]}
    assert t["vi_mode_cursor"] == t["cursor"]
    assert t["selection"] == {"text": C["foreground"], "background": C["selection"]}


def test_search_hints_and_bars():
    t = theme()
    assert t["search"]["matches"] == {"foreground": C["foreground"], "background": C["selection"]}
    assert t["search"]["focused_match"] == {"foreground": C["gold"], "background": C["selection"]}
    assert t["hints"]["start"] == {"foreground": C["background"], "background": C["blue"]}
    assert t["hints"]["end"] == {"foreground": C["background"], "background": C["lightBlue"]}
    for bar in ("footer_bar", "line_indicator"):
        assert t[bar] == {"foreground": C["background"], "background": C["blue"]}, bar


def test_dim_colors_left_to_alacritty():
    assert "dim" not in theme()


@pytest.mark.skipif(
    not (shutil.which("alacritty") and (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))),
    reason="requires alacritty and a display",
)
def test_alacritty_loads_theme_without_config_warnings(tmp_path):
    config = tmp_path / "config" / "alacritty"
    (config / "themes").mkdir(parents=True)
    shutil.copy(REPO / "deepwick.toml", config / "themes" / "deepwick.toml")
    (config / "alacritty.toml").write_text('[general]\nimport = ["themes/deepwick.toml"]\n')
    env = dict(os.environ)
    for kind in ("CONFIG", "DATA", "STATE", "CACHE"):
        env[f"XDG_{kind}_HOME"] = str(tmp_path / kind.lower())
    result = subprocess.run(
        ["timeout", "3", "alacritty", "--daemon", "-vv", "--socket", str(tmp_path / "sock"),
         "--config-file", str(config / "alacritty.toml")],
        env=env, capture_output=True, text=True,
    )
    log = result.stdout + result.stderr
    assert str(config / "themes" / "deepwick.toml") in log, log
    bad = [line for line in log.splitlines() if ("WARN" in line or "ERROR" in line) and ("onfig" in line or "color" in line)]
    assert bad == []


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []
