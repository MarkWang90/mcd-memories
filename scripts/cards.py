#!/usr/bin/env python3
"""排版间 — 把 stories.json 装配成一份「十顿饭的回忆」。

风格基调是《重庆森林》：精确到分的日期、会过期的东西、
以及一句永远来得比画面晚半拍的字幕。

两条原则：
    1. 每一条文案里的数字都来自 stories.json。文案可以抒情，事实不能虚构；
       算不出来的页面会被整个丢掉 —— 所以有人是六页，有人是九页，这是对的。
    2. 画面负责情绪，排版负责信息。有了好看的画面，就不要再往上面堆东西。

用法：
    python3 scripts/cards.py                      # art 模式 + 长卷（默认，推荐）
    python3 scripts/cards.py --format cards       # 拆成 8 张竖图，适合小红书
    python3 scripts/cards.py --mode photo         # 启用仓库里的实拍底图
    python3 scripts/cards.py --demo               # 不联网，用样例数据看效果
    python3 scripts/cards.py --format cards --mode photo

    --mode  art   不用任何图片，全靠 CSS 布光。零素材依赖，谁都能跑。
            photo 用 assets/backgrounds/ 里的 8 张共用底图，电影感更足。
    --format page  一页纸：单张纵向长卷，一个 HTML 文件，可以直接打印成 PDF。
            cards  八张 1080×1440 竖图，按序号发图集。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import art  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "data" / "stories.json"
DEMO = ROOT / "examples" / "demo-stories.json"
CSS_FILE = ROOT / "templates" / "theme.css"
OUT = ROOT / "output"

# 从 output/html/ 指向 assets/backgrounds/ 的相对路径
BG = "../../assets/backgrounds"
PHOTOS = [
    "bg-01-counter.jpg",
    "bg-05-clock.jpg",
    "bg-06-street.jpg",
    "bg-02-cups.jpg",
    "bg-07-burger.jpg",
    "bg-03-crosswalk.jpg",
    "bg-04-closing.jpg",
    "bg-08-counter.jpg",
]
LIGHTS = ["a1", "a2", "a3", "a4", "a5", "a6"]

DIGITS = "零一二三四五六七八九"


def cn(number: int) -> str:
    """把数字读成中文 —— 王家卫的独白里不会出现阿拉伯数字。"""
    number = int(number)
    if number < 10:
        return DIGITS[number]
    if number < 20:
        return "十" + (DIGITS[number % 10] if number % 10 else "")
    if number < 100:
        out = DIGITS[number // 10] + "十"
        return out + (DIGITS[number % 10] if number % 10 else "")
    if number < 1000:
        out = DIGITS[number // 100] + "百"
        rest = number % 100
        if rest == 0:
            return out
        if rest < 10:
            return out + "零" + DIGITS[rest]
        return out + cn(rest)
    return str(number)


def cn_date(iso: str) -> str:
    """2026-06-07 -> 二〇二六年六月七日"""
    y, m, d = iso.split("-")
    return f'{"".join(DIGITS[int(c)] for c in y)}年{cn(int(m))}月{cn(int(d))}日'


def cn_time(hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    period = (
        "凌晨" if h < 6 else "早上" if h < 11 else "中午" if h < 13 else "下午" if h < 18 else "晚上"
    )
    return f"{period}{cn(h)}点{cn(m) if m else ''}{'整' if m == 0 else ''}"


def short_store(name: str) -> str:
    """街面招牌不会写括注。西二旗西路(上地元中心) → 西二旗西路"""
    for sep in ("(", "（"):
        name = name.split(sep)[0]
    return name.strip()


def caption(lines: list[str], footnote: str | None = None, ghost: bool = True) -> str:
    cls = "line ghost" if ghost else "line"
    body = "".join(f'<div class="{cls}">{ln}</div>' for ln in lines)
    fn = f'<div class="footnote">{fn_}</div>' if (fn_ := footnote) else ""
    return f'<div class="caption">{body}{fn}</div>'


# ======================================================================
# 一、场景 —— 内容在这里决定，呈现方式是后面的事
# ======================================================================
def scenes(st: dict) -> list[dict]:
    """把 stories.json 拆成一组场景。

    每个场景只有内容，不关心自己被渲染成一张图还是长卷里的一段。
    数据不够的场景直接不生成 —— 宁可少一页，也不放半空的页面上去。
    """
    meta = st.get("meta") or {}
    n = int(meta.get("total_orders") or 0)
    span = int(meta.get("span_days") or 0)
    first = st.get("first_order") or {}
    out: list[dict] = []

    def add(name, *, folio="", timecode="", inner, smear=False):
        out.append(
            {"name": name, "folio": folio, "timecode": timecode, "inner": inner, "smear": smear}
        )

    # ---------- 序 · 如果记忆也是一个罐头 ----------
    add(
        "01-序",
        folio="PROLOGUE",
        timecode=_span_code(meta),
        inner=f"""
        <div style="flex:1"></div>
        {caption(
            ['如果记忆也是一个<em style="font-style:normal;color:var(--gold)">罐头</em>，',
             '我希望它不会过期。'],
            '可惜每样东西，都有它自己的日期。'
        )}
        """,
    )

    # ---------- 第一顿 ----------
    if first.get("date"):
        add(
            "02-第一顿",
            folio="DAY 001",
            timecode=f'{first["date"].replace("-", ".")} {first.get("weekday", "")} {first.get("time", "")}'.strip(),
            inner=f"""
        <div class="center" style="flex-direction:column;gap:0">
          <div style="font-family:var(--font-num);font-size:190px;letter-spacing:.02em;
                      color:var(--gold);line-height:1;
                      text-shadow:0 0 110px rgba(227,174,76,.55), 0 8px 50px rgba(0,0,0,.9)">
            {first.get("time", "")}
          </div>
          <div class="kicker" style="margin-top:30px">{first.get("weekday", "")} · {short_store(first.get("store", ""))}</div>
        </div>
        {caption(
            [f'{cn_date(first["date"])}，{first.get("weekday", "")}。',
             f'{cn_time(first["time"])}，你在{short_store(first.get("store", ""))}。'],
            f'点了一份{first.get("combo", "")}。' if first.get("combo") else None
        )}
        """,
        )

    # ---------- 跨度 ----------
    if span > 0 and n > 0:
        months = st.get("months") or []
        peak = max((m["count"] for m in months), default=1)
        bars = "".join(
            f"""<div class="bar-item">
              <div class="bar-value">{m["count"]}</div>
              <div class="bar {'mute' if m["count"] == 1 else ''}"
                   style="height:{max(26, int(m["count"] / max(peak, 1) * 230))}px"></div>
              <div class="bar-label">{int(m["month"][5:])}月</div>
            </div>"""
            for m in months
        )
        avg = round(span / n)
        foot = f'平均每{cn(avg)}天一次。但人不是这样记事情的。' if avg > 1 else None
        add(
            "03-跨度",
            folio="THE SPAN",
            timecode=f"{span} DAYS",
            inner=f"""
        <div class="center" style="flex-direction:column;gap:56px">
          <div style="text-align:center">
            <div class="bignum" style="font-size:150px">{cn(span)}<span class="unit">天</span></div>
            <div class="kicker" style="margin-top:24px">你来了 {n} 次</div>
          </div>
          <div class="bars">{bars}</div>
        </div>
        {caption([f'{cn(span)}天，{cn(n)}顿饭。'], foot)}
        """,
        )

    # ---------- 坐标 · 你只在几个地方吃饭 ----------
    stores = st.get("stores") or []
    if len(stores) >= 2:
        rows = "".join(
            f"""<div style="display:flex;align-items:baseline;gap:28px;margin-bottom:36px">
              <div style="font-family:var(--font-sub);font-size:104px;color:var(--gold);
                          line-height:1;min-width:130px;text-align:right;
                          text-shadow:0 0 60px rgba(227,174,76,.42)">{s["count"]}</div>
              <div>
                <div style="font-family:var(--font-sub);font-size:46px;color:var(--cream)">{short_store(s["name"])}</div>
                <div class="kicker" style="font-size:22px;margin-top:12px">{s.get("first_date", "")}</div>
              </div>
            </div>"""
            for s in stores[:4]
        )
        top_store = short_store(stores[0]["name"])
        add(
            "04-坐标",
            folio="MAP",
            timecode=f'{meta.get("store_count", len(stores))} STORES',
            inner=f"""
        <div class="center" style="flex-direction:column;gap:40px">
          <div style="text-align:center">
            <div class="bignum" style="font-size:170px">{cn(len(stores))}<span class="unit">家</span></div>
            <div class="kicker" style="margin-top:24px">你在这些地方吃过麦当劳</div>
          </div>
          <div style="width:100%;padding:0 40px">{rows}</div>
        </div>
        {caption(
            [f'{cn(n)}顿饭，分散在{cn(len(stores))}家店。'],
            f'大部分时间，你都在{top_store}那家。' if stores[0]["count"] > n / 2 else None
        )}
        """,
        )

    # ---------- 执念 · 无糖可乐 ----------
    drinks = st.get("drinks") or {}
    sf = int(drinks.get("sugarfree_orders") or 0)
    # 只有两次以上才叫执念。一次的那算意外，不该占一整页。
    if n >= 3 and sf >= 2:
        cups = []
        for i in range(n):
            if i < sf:
                style = "opacity:.95"
            elif i == sf:
                style = "opacity:.9;filter:hue-rotate(-40deg) saturate(1.7)"
            else:
                style = "opacity:.20;filter:grayscale(1)"
            cups.append(f'<div style="{style}">{art.cup(62)}</div>')
        cup_row = (
            '<div style="display:flex;align-items:flex-end;gap:8px;justify-content:center">'
            + "".join(cups)
            + "</div>"
        )
        sugared = n - sf
        second = '含糖的，只有一次。' if sugared == 1 else f'含糖的，{cn(sugared)}次。'
        add(
            "05-执念",
            folio="RUNNING GAG",
            timecode=f"{sf} / {n} ORDERS",
            inner=f"""
        <div class="center" style="flex-direction:column;gap:40px">
          <div style="font-family:var(--font-sub);font-size:130px;color:var(--gold);line-height:1;
                      text-shadow:0 0 90px rgba(227,174,76,.5),0 6px 44px rgba(0,0,0,.9)">
            {sf}<span style="font-size:60px;color:var(--brass)"> / {n}</span>
          </div>
          {cup_row}
        </div>
        {caption(
            [f'{cn(n)}顿饭里，你有{cn(sf)}顿点了无糖可乐。',
             f'含糖的只有{cn(sugared)}次。' if sugared == 1 else f'含糖的，{cn(sugared)}次。'],
            '你说你在控制什么。我信了。'
        )}
        """,
        )

    # ---------- 招牌菜 ----------
    top = (st.get("top_combos") or [None])[0]
    if top and top.get("count", 0) >= 2:
        tp_pre = st.get("turning_point")
        fav = (tp_pre or {}).get("new_favorite")
        if fav and fav.get("name") == top["name"] and tp_pre.get("date"):
            _m, _d = tp_pre["date"].split("-")[1:]
            foot5 = f'{top["name"]}。{cn(top["count"])}次，都在{cn(int(_m))}月{cn(int(_d))}日之后。'
        else:
            foot5 = f'{top["name"]}。认定了一样东西，就很少再换。'
        heroes = art.row(art.burger(104), min(top["count"], 3), gap=20)
        add(
            "06-招牌菜",
            folio="THE USUAL",
            timecode=f'×{top["count"]}',
            inner=f"""
        <div class="center">{heroes}</div>
        {caption([f'你点了{cn(top["count"])}次同一份套餐。'], foot5)}
        """,
        )

    # ---------- 分水岭 ----------
    tp = st.get("turning_point")
    rhythm = st.get("rhythm") or {}
    if tp and rhythm.get("early") and rhythm.get("late"):
        early, late = rhythm["early"], rhythm["late"]
        ratio = rhythm.get("ratio")
        add(
            "07-分水岭",
            folio="THE TURN",
            timecode=f'{tp["date"].replace("-", ".")} {tp.get("weekday", "")}'.strip(),
            inner=f"""
        <div style="text-align:center;margin-bottom:40px">
          <div class="kicker">那一天之后，一切都变了</div>
        </div>
        <div class="center" style="flex-direction:column;gap:34px">
          <div class="duo" style="width:100%">
            <div class="duo-col">
              <div class="duo-num">{cn(early["orders"])}</div>
              <div class="duo-label">前{cn(early["days"])}天</div>
            </div>
            <div class="duo-col hit">
              <div class="duo-num">{cn(late["orders"])}</div>
              <div class="duo-label">后{cn(late["days"])}天</div>
            </div>
          </div>
          {f'<div style="text-align:center;font-family:var(--font-sub);font-size:54px;color:var(--gold);text-shadow:0 0 70px rgba(227,174,76,.5),0 4px 40px rgba(0,0,0,.9)">每周的次数，涨了{cn(int(ratio))}倍</div>' if ratio else ""}
        </div>
        {caption(
            [f'那天你第一次去了{short_store(tp["new_store"])}。',
             f'往后{cn(late["days"])}天，你来{cn(late["orders"])}次。'],
            f'而之前{cn(early["days"])}天，你也只来{cn(early["orders"])}次。'
        )}
        """,
            smear=True,
        )

    # ---------- 空窗 ----------
    gap = st.get("biggest_gap")
    if gap and gap.get("days", 0) >= 10 and gap.get("from") and gap.get("to"):
        gm, gd = gap["from"].split("-")[1:]
        tm, td = gap["to"].split("-")[1:]
        cells = "".join('<div class="cell off"></div>' for _ in range(min(gap["days"], 28)))
        add(
            "08-空窗",
            folio="THE GAP",
            timecode=f'{gap["from"].replace("-", ".")} → {gap["to"].replace("-", ".")}',
            inner=f"""
        <div class="center" style="flex-direction:column;gap:52px">
          <div style="text-align:center">
            <div class="bignum" style="font-size:200px">{cn(gap["days"])}<span class="unit">天</span></div>
            <div class="kicker" style="margin-top:24px">你一次都没有出现</div>
          </div>
          <div class="grid" style="grid-template-columns:repeat(14,1fr);gap:9px;width:100%">{cells}</div>
        </div>
        {caption(
            [f'从{cn(int(gm))}月{cn(int(gd))}日，到{cn(int(tm))}月{cn(int(td))}日。'],
            f'这{cn(gap["days"])}天你去了哪里，麦当劳没有告诉我。'
        )}
        """,
        )

    # ---------- 尾声 ----------
    add(
        "09-尾声",
        folio="FIN",
        timecode="END OF TAPE",
        inner=f"""
        <div style="flex:1"></div>
        {caption(
            ['罐头会过期。记忆也会。',
             f'但这{cn(n)}顿，我替你记住了。'],
            '下一顿是什么时候，我也不知道。'
        )}
        """,
    )

    return out


def _span_code(meta: dict) -> str:
    a, b = meta.get("first_date"), meta.get("last_date")
    if a and b:
        return f'{a.replace("-", ".")} — {b.replace("-", ".")}'
    return "NO SIGNAL"


# ======================================================================
# 二、呈现 —— 同一批场景，两种形态
# ======================================================================
def _layers(sc: dict, idx: int, mode: str) -> str:
    """场景的画面层。mode 决定用实拍底图还是纯 CSS 布光。"""
    if mode == "photo":
        photo = f"{BG}/{PHOTOS[idx % len(PHOTOS)]}"
        return (
            f'<div class="photo" style="background-image:url(\'{photo}\')"></div>'
            '<div class="scrim"></div><div class="tint"></div>'
        )
    light = LIGHTS[idx % len(LIGHTS)]
    shaft = '<div class="shaft"></div>'
    smear = '<div class="smear"></div>' if sc.get("smear") else ""
    return f'<div class="bg {light}"></div>{shaft}{smear}'


def _chrome(sc: dict) -> str:
    tc = f'<div class="timecode"><span class="dot"></span>{sc["timecode"]}</div>' if sc.get("timecode") else ""
    fl = f'<div class="folio">{sc["folio"]}</div>' if sc.get("folio") else ""
    return tc, fl


def standalone(sc: dict, idx: int, mode: str, *, width: int = 1080, height: int = 1440) -> str:
    """一张独立的竖图。"""
    tc, fl = _chrome(sc)
    css = CSS_FILE.read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
:root {{ --noise: {art.noise_datauri()}; }}
{css}
.stage {{ height: {height}px; width: {width}px; }}
</style>
</head>
<body>
<div class="stage">
  {_layers(sc, idx, mode)}
  <div class="scan"></div>
  <div class="grain"></div>
  <div class="vignette"></div>
  {tc}
  {fl}
  <div class="frame">
    {sc["inner"]}
  </div>
</div>
</body>
</html>"""


def reel(all_scenes: list[dict], mode: str, *, title: str) -> str:
    """一卷胶片 —— 一个自包含的 HTML，从上往下滚。

    长卷的好处：一次渲染出全部内容，不用等八次 Chrome；
    可以整页截图、可以直接打印成 PDF、也可以单文件发给别人。
    """
    css = CSS_FILE.read_text(encoding="utf-8")
    blocks = []
    for i, sc in enumerate(all_scenes):
        tc, fl = _chrome(sc)
        blocks.append(f"""
<section class="scene">
  {_layers(sc, i, mode)}
  <div class="scan"></div>
  <div class="grain"></div>
  <div class="vignette"></div>
  {tc}
  {fl}
  <div class="frame">
    {sc["inner"]}
  </div>
</section>""")
    body = "".join(blocks)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
:root {{ --noise: {art.noise_datauri()}; }}
{css}
</style>
</head>
<body>
<div class="reel">
  <div class="reel-inner">
    <div class="perf l"></div>
    <div class="perf r"></div>
{body}
  </div>
</div>
</body>
</html>"""


def github_cover(st: dict, mode: str) -> str:
    """GitHub 仓库封面（social preview）：1280 × 640。"""
    meta = st.get("meta") or {}
    a, b = meta.get("first_date"), meta.get("last_date")
    code = f'{a.replace("-", ".")} — {b.replace("-", ".")}' if a and b else "NO SIGNAL"
    sc = {"inner": "", "folio": "", "timecode": code, "smear": False}
    tc, fl = _chrome(sc)
    css = CSS_FILE.read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
:root {{ --noise: {art.noise_datauri()}; }}
{css}
.stage {{ height: 640px; width: 1280px; }}
.stage .frame {{ padding: 170px 80px 76px; }}
</style>
</head>
<body>
<div class="stage">
  {_layers({"smear": True}, 5, mode)}
  <div class="scan"></div>
  <div class="grain"></div>
  <div class="vignette"></div>
  {tc}
  <div class="frame">
    <div style="max-width:900px">
      <div class="kicker" style="margin-bottom:22px">MCD·MEMORIES</div>
      <div class="title" style="font-size:76px;line-height:1.24">
        如果记忆<br>也是一个<em>罐头</em>
      </div>
      <div class="footnote" style="margin-top:30px;font-size:30px;line-height:1.56">
        把你麦当劳账户里的订单，<br>拍成一部电影。
      </div>
      <div style="margin-top:26px;font-family:var(--font-num);font-size:22px;
                  letter-spacing:.08em;color:#B8873A">github.com/MarkWang90/mcd-memory-can</div>
    </div>
  </div>
</div>
</body>
</html>"""


# ======================================================================
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="art", choices=["art", "photo"])
    parser.add_argument("--format", default="page", choices=["page", "cards"])
    parser.add_argument("--demo", action="store_true", help="用样例数据渲染，不需要 Token")
    parser.add_argument("--stories", default=None, help="指定 stories.json 路径")
    args = parser.parse_args()

    src = Path(args.stories) if args.stories else (DEMO if args.demo else STORIES)
    if not src.exists():
        hint = "（试试 python3 scripts/cards.py --demo）" if not args.demo else ""
        raise SystemExit(f"找不到数据文件 {src}。{hint}")
    st = json.loads(src.read_text(encoding="utf-8"))

    html_dir = OUT / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    for old in html_dir.glob("*.html"):
        old.unlink()

    all_scenes = scenes(st)
    written: list[Path] = []

    if args.format == "cards":
        for i, sc in enumerate(all_scenes):
            p = html_dir / f"{sc['name']}.html"
            p.write_text(standalone(sc, i, args.mode), encoding="utf-8")
            written.append(p)
    else:
        p = html_dir / "00-长卷.html"
        meta = st.get("meta") or {}
        title = f'麦麦记忆 · {meta.get("span_days", "?")} 天 {meta.get("total_orders", "?")} 顿'
        p.write_text(reel(all_scenes, args.mode, title=title), encoding="utf-8")
        written.append(p)

    cover = html_dir / "00-github封面.html"
    cover.write_text(github_cover(st, args.mode), encoding="utf-8")
    written.append(cover)

    index = [
        '<meta charset="utf-8"><title>麦麦记忆</title>',
        '<body style="margin:0;background:#061612;font-family:-apple-system,PingFang SC,sans-serif">',
        '<div style="padding:20px;color:#DED5BE">'
        f'<div style="margin-bottom:16px">模式 <b>{args.mode}</b> ｜ 形态 <b>{args.format}</b>'
        f' ｜ 共 {len(all_scenes)} 幕 ｜ 数据 {"样例" if args.demo else "真实"}</div>',
    ]
    for p in written:
        h = 1440 if p.name != "00-github封面.html" else 640
        index.append(
            f'<div style="margin-bottom:28px"><div style="color:#B8873A;font-size:13px;'
            f'margin-bottom:6px">{p.name}</div>'
            f'<iframe src="{p.name}" style="width:1080px;height:{min(h,720)}px;border:0;'
            f'transform:scale(.62);transform-origin:top left"></iframe></div>'
        )
    index.append("</div></body>")
    (html_dir / "index.html").write_text("".join(index), encoding="utf-8")

    print(f"模式 {args.mode} ｜ 形态 {args.format} ｜ 数据 {'样例' if args.demo else src.name}")
    print(f"共 {len(all_scenes)} 幕：")
    for sc in all_scenes:
        print(f"   {sc['name']}")
    print(f"\n→ {html_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
