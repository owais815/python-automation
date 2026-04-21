"""
Automation cycle: VS Code → Cursor → Browser → back to VS Code (loop).
For each open editor tab: switch to it, scroll it to bottom then top, then next tab. Same for browser tabs.
"""

import argparse
import json
import subprocess
import time
import random
import signal
from pathlib import Path

import pyautogui

# --- Config (adjust for your screen / layout) ---
SCROLL_DURATION_SEC = 120   # 2 minutes per editor (half down, half up)
WAIT_BETWEEN_APPS_SEC = 180  # 3 minutes between app phases
BROWSER_TAB_CYCLE_SEC = 30  # ~time per browser tab (scroll / move)
SCROLL_STEP_INTERVAL_SEC = 0.5  # time between each scroll step (down/up)

# Pacing: longer = every process clearly visible on screen
STEP_PAUSE_SEC = 2.0        # pause after each click/move so you see it
MOVE_DURATION_SEC = 1.2     # how long each mouse move takes

# Editor tab bar: TOP BAR = horizontal row of file-name tabs above the code (not sidebar).
# We always use TAB_BAR_Y for vertical position (saved file only gives X). Smaller Y = higher on screen.
# If click lands IN the file: set TAB_BAR_Y smaller (e.g. 50 or 55). If above window: set larger (e.g. 75).
SCRIPT_DIR = Path(__file__).resolve().parent
TAB_COORDS_FILE = SCRIPT_DIR / "tab_coords.json"
NUM_TABS_TO_CALIBRATE = 5  # number of editor tabs to record in --calibrate
TAB_BAR_Y = 45  # vertical pixel of tab bar (from --find-y: mouse on top bar = Y 45–51)
DEFAULT_TABS = [(220 + i * 100, TAB_BAR_Y) for i in range(5)]  # fallback if no file

# Apps (macOS)
APP_VSCODE = "Visual Studio Code"
APP_CURSOR = "Cursor"
APP_BROWSER = "Google Chrome"  # or "Safari"

# Control
running = True


def stop_handler(*_):
    global running
    running = False


def load_tab_coords() -> list[tuple[int, int]]:
    """Load tab positions: X from file, Y always TAB_BAR_Y so we hit the top bar."""
    if not TAB_COORDS_FILE.exists():
        return list(DEFAULT_TABS)
    try:
        data = json.loads(TAB_COORDS_FILE.read_text())
        if "tabs" in data:
            raw = [tuple(p) for p in data["tabs"]]
        elif "tab4" in data and "tab5" in data:
            raw = [tuple(data["tab4"]), tuple(data["tab5"])]
        else:
            return list(DEFAULT_TABS)
        # Always use TAB_BAR_Y for Y (saved Y often lands in file); keep X from file
        return [(x, TAB_BAR_Y) for x, _ in raw]
    except (json.JSONDecodeError, KeyError, TypeError):
        return list(DEFAULT_TABS)


def save_tab_coords(tabs: list[tuple[int, int]]) -> None:
    TAB_COORDS_FILE.write_text(
        json.dumps({"tabs": [list(t) for t in tabs]}, indent=2)
    )


def run_calibrate() -> None:
    """Record editor tab positions: user moves mouse to each tab in the TOP BAR, script records after countdown."""
    print("Calibration: TOP BAR tabs (VS Code / Cursor).")
    print("TOP BAR = the horizontal row of FILE NAME TABS above the code (e.g. 'automation_cycle.py').")
    print("NOT the sidebar. Aim at the center of each tab in that top row.\n")
    print(f"Have at least {NUM_TABS_TO_CALIBRATE} editor tabs open, then follow prompts.\n")
    recorded = []
    for i in range(1, NUM_TABS_TO_CALIBRATE + 1):
        label = f"{i}st" if i == 1 else f"{i}nd" if i == 2 else f"{i}rd" if i == 3 else f"{i}th"
        print(f"Move mouse to the {label} TAB IN THE TOP BAR (file name tab) and keep it there.")
        for c in range(5, 0, -1):
            print(f"  Recording in {c}...")
            time.sleep(1)
        x, y = pyautogui.position()
        print(f"  Recorded: ({x}, {y})\n")
        recorded.append((x, y))
    save_tab_coords(recorded)
    print(f"Saved to {TAB_COORDS_FILE}. Run without --calibrate to start automation.")


def bring_app(name: str) -> None:
    subprocess.run(["open", "-a", name], check=False)
    time.sleep(STEP_PAUSE_SEC + 1)  # let app come to front and settle


def do_mouse_demo() -> None:
    """Short mouse movement to show automation is active."""
    w, h = pyautogui.size()
    for _ in range(3):
        if not running:
            return
        x = random.randint(w // 4, 3 * w // 4)
        y = random.randint(h // 4, 3 * h // 4)
        pyautogui.moveTo(x, y, duration=MOVE_DURATION_SEC)
        time.sleep(STEP_PAUSE_SEC)


def focus_editor_area() -> None:
    """Click center of screen so scroll applies to editor."""
    w, h = pyautogui.size()
    pyautogui.moveTo(w * 3 // 4, h // 2, duration=MOVE_DURATION_SEC)
    time.sleep(STEP_PAUSE_SEC)
    pyautogui.click()
    time.sleep(STEP_PAUSE_SEC)


def switch_to_tab_and_scroll_all(tabs: list[tuple[int, int]], total_scroll_sec: float) -> None:
    """For each tab: switch to it, focus editor, scroll to bottom then top; then next tab."""
    if not tabs:
        return
    per_tab_sec = total_scroll_sec / len(tabs)
    for x, y in tabs:
        if not running:
            return
        # Switch to this tab
        pyautogui.moveTo(x, y, duration=MOVE_DURATION_SEC)
        time.sleep(STEP_PAUSE_SEC)
        pyautogui.click()
        time.sleep(STEP_PAUSE_SEC)
        # Focus editor so scroll applies
        focus_editor_area()
        if not running:
            return
        # Scroll this file to bottom then top
        scroll_editor_full(per_tab_sec)


def scroll_editor_full(seconds: float) -> None:
    """Scroll editor to bottom over first half, then to top over second half."""
    half = seconds / 2
    # Scroll down to bottom (first half)
    end_down = time.time() + half
    while time.time() < end_down and running:
        pyautogui.scroll(-2)
        time.sleep(SCROLL_STEP_INTERVAL_SEC)
    if not running:
        return
    # Scroll up to top (second half)
    end_up = time.time() + half
    while time.time() < end_up and running:
        pyautogui.scroll(2)
        time.sleep(SCROLL_STEP_INTERVAL_SEC)


def do_editor_phase(app_name: str) -> None:
    """Open app, mouse demo, then for each open tab: switch to it and scroll it fully; wait 3 min."""
    if not running:
        return
    bring_app(app_name)
    if not running:
        return
    do_mouse_demo()
    if not running:
        return
    tabs = load_tab_coords()
    switch_to_tab_and_scroll_all(tabs, SCROLL_DURATION_SEC)
    if not running:
        return
    time.sleep(WAIT_BETWEEN_APPS_SEC)


def scroll_or_move_in_browser() -> None:
    """Scroll down a bit, then up; or small random move if not scrollable."""
    pyautogui.scroll(-3)
    time.sleep(STEP_PAUSE_SEC)
    pyautogui.scroll(3)
    time.sleep(STEP_PAUSE_SEC)
    w, h = pyautogui.size()
    pyautogui.moveTo(
        random.randint(w // 4, 3 * w // 4),
        random.randint(h // 4, 3 * h // 4),
        duration=MOVE_DURATION_SEC,
    )
    time.sleep(STEP_PAUSE_SEC)


def do_browser_phase() -> None:
    """Bring browser to front, cycle tabs and scroll/move in each."""
    if not running:
        return
    bring_app(APP_BROWSER)
    if not running:
        return
    # Cycle tabs: scroll/move in current tab, then next tab, for BROWSER_TAB_CYCLE_SEC per tab
    end = time.time() + 6 * BROWSER_TAB_CYCLE_SEC  # ~6 tabs worth of time
    while time.time() < end and running:
        scroll_or_move_in_browser()
        time.sleep(STEP_PAUSE_SEC)
        # Next tab: Cmd+Shift+] on macOS
        pyautogui.hotkey("command", "shift", "]")
        time.sleep(STEP_PAUSE_SEC)
    if not running:
        return
    time.sleep(WAIT_BETWEEN_APPS_SEC)


def main() -> None:
    global running
    parser = argparse.ArgumentParser(description="VS Code → Cursor → Browser automation cycle.")
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Record editor tab positions (move mouse to each tab when prompted).",
    )
    parser.add_argument(
        "--find-y",
        action="store_true",
        help="Print mouse Y every second for 10 sec; use that value for TAB_BAR_Y.",
    )
    args = parser.parse_args()
    if args.find_y:
        print("Move mouse to a FILE TAB in the TOP BAR (the row with file names ABOVE the code).")
        print("NOT the center of the screen. NOT the sidebar. Y will be printed every second.")
        for i in range(10, 0, -1):
            x, y = pyautogui.position()
            print(f"  {i}s ... Y={y}  (set TAB_BAR_Y = {y} at top of script)")
            time.sleep(1)
        return
    if args.calibrate:
        run_calibrate()
        return

    pyautogui.FAILSAFE = True
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    tabs = load_tab_coords()
    print(f"Tab coords: {len(tabs)} tabs, Y={TAB_BAR_Y} (top bar): {tabs}")
    print(f"If click misses top bar: edit TAB_BAR_Y at top of script (try 50 or 58).")
    print("Automation started. Move mouse to corner to abort (FAILSAFE).")
    print("Press Ctrl+C to stop.\n")
    time.sleep(3)

    while running:
        do_editor_phase(APP_VSCODE)
        do_editor_phase(APP_CURSOR)
        do_browser_phase()
        # Back to VS Code for next loop
        if running:
            bring_app(APP_VSCODE)
            time.sleep(STEP_PAUSE_SEC)

    print("Stopped.")


if __name__ == "__main__":
    main()
