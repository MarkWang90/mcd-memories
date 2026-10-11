#!/usr/bin/env python3
"""暗房 — 把 output/html 冲印成 PNG。

为什么用本机 Chrome 的无头模式，而不是引入 Playwright / Puppeteer：
    1. macOS / Windows 上它多半本来就在，克隆仓库的人不必装任何东西；
    2. 它是唯一能把中文字体、CSS 渐变、滤镜、SVG 同时渲染对的现成渲染器；
    3. 全程离线，不经过任何第三方服务。

用法：
    python3 scripts/render.py                     # 冲印 output/html 里的全部文件
    python3 scripts/render.py --only 07-分水岭     # 只冲印名字里含该字符串的那张
    python3 scripts/render.py --no-cover

两种产出都能处理：
    · 长卷（00-长卷.html）—— 一次渲染整卷，高度自动算出来
    · 卡片（01-序.html 等）—— 并行渲染若干张 1080×1440
"""

from __future__ import annotations

import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "output" / "html"
PNG_DIR = ROOT / "output" / "png"
TMP_DIR = ROOT / "output" / ".chrome"

CARD_W, CARD_H = 1080, 1440
COVER_W, COVER_H = 1280, 640
# Chrome 单次截图有高度上限，长卷超过这个值会只截到一部分
MAX_H = 16000

PLATFORMS = {
    "xhs": (1080, 1440, "小红书 3:4"),
    "dy": (1080, 1920, "抖音 9:16"),
    "cover": (1280, 640, "GitHub 封面"),
}

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit(
        "找不到 Chrome / Edge / Chromium。\n"
        "装一个后重跑；或者直接打开 output/html 里的文件，用浏览器「打印 → 存成 PDF」当成品。"
    )


def shoot(chrome: str, html: Path, out: Path, w: int, h: int) -> bool:
    profile = TMP_DIR / f"p-{html.stem}"
    profile.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=5000",
        f"--window-size={w},{h}",
        f"--user-data-dir={profile}",
        f"--screenshot={out}",
        html.as_uri(),
    ]
    for attempt in range(2):
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            pass  # Chrome 有时渲染完了也不肯退出，产物其实已经落盘
        except Exception:
            pass
        if out.exists() and out.stat().st_size > 0:
            return True
    return False


def reel_height(html: Path) -> int:
    """长卷有多高，由里面有几幕决定。"""
    text = html.read_text(encoding="utf-8")
    n = len(re.findall(r'<section class="scene">', text))
    return int(min(n, MAX_H // CARD_H) * CARD_H)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", default="xhs", choices=list(PLATFORMS))
    parser.add_argument("--only", default=None)
    parser.add_argument("--no-cover", action="store_true")
    args = parser.parse_args()

    if not HTML_DIR.exists():
        raise SystemExit("没有 output/html，先跑 scripts/cards.py")

    card_w, card_h = PLATFORMS[args.platform][:2]
    chrome = find_chrome()
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    reels = sorted(HTML_DIR.glob("00-长卷*.html"))
    cards = sorted(
        t for t in HTML_DIR.glob("*.html")
        if t.stem != "index" and not t.stem.startswith("00-")
    )
    if args.only:
        reels = [t for t in reels if args.only in t.stem]
        cards = [t for t in cards if args.only in t.stem]
    if not reels and not cards and args.no_cover:
        raise SystemExit("没有可冲印的文件")

    print(f"冲洗机：{Path(chrome).name}｜{PLATFORMS[args.platform][2]}")
    ok = total = 0

    # ---- 长卷：一次成型，比八张分开快得多 ----
    for html in reels:
        total += 1
        h = reel_height(html)
        print(f"  长卷共 {h // CARD_H} 幕 · {CARD_W}×{h}")
        out = PNG_DIR / f"{html.stem}.png"
        good = shoot(chrome, html, out, CARD_W, h)
        ok += good
        print(f"  {'✓' if good else '✗'} {out.name}")

    # ---- 卡片：并行 ----
    if cards:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(
                    shoot, chrome, html, PNG_DIR / f"{html.stem}.png", card_w, card_h
                ): html
                for html in cards
            }
            for fut in as_completed(futures):
                html = futures[fut]
                total += 1
                good = fut.result()
                ok += good
                print(f"  {'✓' if good else '✗'} {html.stem}.png")

    # ---- GitHub 封面 ----
    if not args.no_cover and not args.only:
        cover_html = HTML_DIR / "00-github封面.html"
        if cover_html.exists():
            total += 1
            out = PNG_DIR / "00-github封面.png"
            good = shoot(chrome, cover_html, out, COVER_W, COVER_H)
            ok += good
            print(f"  {'✓' if good else '✗'} {out.name}（GitHub 封面）")

    print(f"\n完成 {ok}/{total} → {PNG_DIR.relative_to(ROOT)}")
    if ok < total:
        print("（有失败的。多数时候是上一次的 Chrome 还挂着没退干净，重跑一次通常就好。）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
