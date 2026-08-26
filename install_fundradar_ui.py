"""Install / upgrade the FundRadar dashboard UI add-ons.

Blocks installed (each is a normal HTML file sitting next to this script):
    fundradar-chat-widget.html   -> floating chat bubble, bottom-right
    fundradar-filters.html       -> fund-size categories + filter/sort panel

How it works:
  1. Backs up  app/api/static/dashboard.html  ->  dashboard.html.bak
  2. Removes any previously installed version of these blocks
  3. Inserts the current versions just before </body>

Everything else in dashboard.html is left untouched, so your own edits survive.
Safe to run as many times as you like - it always replaces, never duplicates.

To undo: delete dashboard.html and rename dashboard.html.bak back.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT   = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "api" / "static" / "dashboard.html"
BACKUP = TARGET.with_suffix(".html.bak")

BLOCKS = [
    ("chat",    ROOT / "fundradar-chat-widget.html"),
    ("filters", ROOT / "fundradar-filters.html"),
]

# v1 of the chat widget shipped without FR-BLOCK markers - clean it up too.
LEGACY_START = "<!-- ============================================================"
LEGACY_HINT  = "FundRadar — Floating Chat Widget"
LEGACY_END   = "<!-- ================= end FundRadar chat widget ================= -->"


def strip_block(html: str, name: str) -> str:
    pattern = re.compile(
        r"[ \t]*<!--\s*FR-BLOCK:" + re.escape(name) + r"\s+START\s*-->.*?"
        r"<!--\s*FR-BLOCK:" + re.escape(name) + r"\s+END\s*-->[ \t]*\n?",
        re.DOTALL,
    )
    return pattern.sub("", html)


def strip_legacy_chat(html: str) -> str:
    hint = html.find(LEGACY_HINT)
    if hint == -1:
        return html
    start = html.rfind(LEGACY_START, 0, hint)
    end = html.find(LEGACY_END, hint)
    if start == -1 or end == -1:
        return html
    return html[:start] + html[end + len(LEGACY_END):].lstrip("\n")


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: could not find {TARGET}")
        print("Run this from inside the project folder.")
        return 1

    missing = [p.name for _, p in BLOCKS if not p.exists()]
    if missing:
        print("ERROR: these files are missing from the project folder:")
        for m in missing:
            print("  -", m)
        return 1

    html = TARGET.read_text(encoding="utf-8")
    if "</body>" not in html:
        print("ERROR: no </body> tag in dashboard.html - not touching it.")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup saved: {BACKUP.name}")

    before = len(html)
    html = strip_legacy_chat(html)
    for name, _ in BLOCKS:
        html = strip_block(html, name)
    if len(html) < before:
        print(f"Removed the previous version ({before - len(html):,} characters)")

    payload = "\n".join(path.read_text(encoding="utf-8").rstrip() for _, path in BLOCKS)
    head, sep, tail = html.rpartition("</body>")
    TARGET.write_text(head + payload + "\n" + sep + tail, encoding="utf-8")

    # ---- verify what actually landed on disk, don't just claim success ----
    written = TARGET.read_text(encoding="utf-8")
    print()
    ok = True
    for name, path in BLOCKS:
        marker = f"FR-BLOCK:{name} START"
        hits = written.count(marker)
        if hits == 1:
            print(f"  [OK]   {path.name}")
        else:
            ok = False
            print(f"  [FAIL] {path.name}  (found {hits} copies, expected 1)")

    print(f"\n  {TARGET.name}: {len(html):,} -> {len(written):,} characters")
    print(f"  file on disk: {TARGET}")

    if not ok:
        print("\nSomething went wrong - restore dashboard.html.bak and tell Claude.")
        return 1

    print("\n" + "=" * 52)
    print(" DONE. Now do BOTH of these:")
    print("   1. Restart the app  (close START_APP window, run it again)")
    print("   2. In the browser press CTRL+SHIFT+R to hard-refresh")
    print("      (a normal refresh can show the old cached page)")
    print("=" * 52)
    print("\n You should then see a 'Filter & segment opportunities'")
    print(" panel above the table, and the chat should open as a")
    print(" side panel that pushes the page left.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
