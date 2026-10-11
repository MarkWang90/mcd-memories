#!/usr/bin/env python3
"""铅笔 — 手写 SVG 插画。

画法只有一条规矩：物体大半沉进黑暗，只有朝光的那一条边缘是亮的。
所有形状都用几何pathy拼，不用任何外部素材，保证仓库克隆下来就能跑。

每个函数返回一个完整 SVG 字符串。为了避免同页内 defs id 撞车，
所有 id 都带 uid 后缀。
"""

from __future__ import annotations

import base64
import itertools
import textwrap
from xml.etree import ElementTree  # noqa: F401  (留给后续 SVG 校验)

_ids = itertools.count()


def uid() -> str:
    return f"a{next(_ids)}"


GOLD = "#E3AE4C"
BRASS = "#B8873A"
CREAM = "#DED5BE"
DIM = "#6E7A72"
RED = "#C42C3A"
JADE = "#1B4A3E"
INK = "#061612"


# --------------------------------------------------------------------------
# 胶片噪点：整套视觉的底座
# --------------------------------------------------------------------------
def noise_datauri() -> str:
    svg = textwrap.dedent(
        """\
        <svg xmlns="http://www.w3.org/2000/svg" width="320" height="320">
          <filter id="n">
            <feTurbulence type="fractalNoise" baseFrequency="0.85"
                          numOctaves="3" stitchTiles="stitch"/>
            <feColorMatrix type="saturate" values="0"/>
          </filter>
          <rect width="320" height="320" filter="url(#n)"/>
        </svg>"""
    )
    encoded = base64.b64encode(svg.encode()).decode()
    return f"url('data:image/svg+xml;base64,{encoded}')"


# --------------------------------------------------------------------------
# 汉堡 — 报告的主角
# --------------------------------------------------------------------------
def burger_shape() -> str:
    """不带 <svg> 外壳的汉堡本体，坐标系 200x200。

    抽出来是为了让它在别处（罐头标签、SVG 内部）也能被直接引用，
    同时因为它是纯色分层、不依赖任何 gradient id，引用时不会撞 defs。
    """
    return f"""<g>
  <ellipse cx="100" cy="176" rx="72" ry="12" fill="{GOLD}" opacity=".10"/>
  <path d="M24 128 h152 a10 10 0 0 1 10 10 v14 a34 34 0 0 1 -34 34 h-104 a34 34 0 0 1 -34 -34 v-14 a10 10 0 0 1 10 -10 z"
        fill="#6B4620"/>
  <rect x="20" y="106" width="160" height="26" rx="11" fill="#3A2416"/>
  <path d="M20 100 l160 0 v10 l-160 0 z" fill="{GOLD}" opacity=".92"/>
  <path d="M20 100 l80 14 l80 -14 z" fill="{BRASS}" opacity=".55"/>
  <path d="M22 98 q16 -14 32 0 q16 -14 32 0 q16 -14 32 0 q16 -14 32 0 q16 -14 30 0 v8 h-158 z"
        fill="#37704A"/>
  <path d="M14 96 a86 62 0 0 1 172 0 z" fill="#8A5F2C"/>
  <path d="M14 96 a86 62 0 0 1 172 0 z" fill="#000" opacity=".28"/>
  <path d="M14 96 a86 62 0 0 1 172 0" stroke="{GOLD}" stroke-width="1.6" opacity=".45"/>
  <g fill="{CREAM}" opacity=".62">
    <ellipse cx="66" cy="60" rx="7" ry="3.4" transform="rotate(-24 66 60)"/>
    <ellipse cx="100" cy="48" rx="7" ry="3.4" transform="rotate(-6 100 48)"/>
    <ellipse cx="134" cy="60" rx="7" ry="3.4" transform="rotate(22 134 60)"/>
    <ellipse cx="86" cy="76" rx="6.5" ry="3.2" transform="rotate(-14 86 76)"/>
    <ellipse cx="118" cy="78" rx="6.5" ry="3.2" transform="rotate(16 118 78)"/>
  </g>
</g>"""


def burger(size: int = 300, label: str | None = None) -> str:
    u = uid()
    svg = f"""<svg width="{size}" height="{size}" viewBox="0 0 200 200" fill="none">
  <defs>
    <radialGradient id="rim{u}" cx=".32" cy=".28" r=".8">
      <stop offset="0" stop-color="{GOLD}" stop-opacity=".85"/>
      <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  {burger_shape()}
  <ellipse cx="70" cy="70" rx="96" ry="80" fill="url(#rim{u})"/>
</svg>"""
    if label:
        svg = svg.replace(
            "</svg>",
            f'<text x="100" y="188" text-anchor="middle" font-family="Songti SC,serif" '
            f'font-size="17" fill="{DIM}">{label}</text></svg>',
        )
    return svg


# --------------------------------------------------------------------------
# 可乐杯 — 报告里出现最多的配角
# --------------------------------------------------------------------------
def cup(size: int = 200) -> str:
    u = uid()
    svg = f"""<svg width="{size}" height="{int(size*1.25)}" viewBox="0 0 160 200" fill="none">
  <defs>
    <linearGradient id="cu{u}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0B1A15"/>
      <stop offset=".26" stop-color="#2E3A42"/>
      <stop offset=".52" stop-color="#141E22"/>
      <stop offset="1" stop-color="#060E0B"/>
    </linearGradient>
  </defs>
  <ellipse cx="80" cy="188" rx="52" ry="9" fill="{GOLD}" opacity=".08"/>
  <!-- 吸管 -->
  <path d="M104 18 l-14 74" stroke="{CREAM}" stroke-width="9" stroke-linecap="round" opacity=".55"/>
  <!-- 杯身 -->
  <path d="M40 40 h80 l-12 132 a10 10 0 0 1 -10 9 h-36 a10 10 0 0 1 -10 -9 z" fill="url(#cu{u})"/>
  <!-- 被灯照亮的那一条竖边 -->
  <path d="M52 46 l-8 128" stroke="{GOLD}" stroke-width="3.4" opacity=".55"/>
  <path d="M40 40 h80 l-4 6 h-72 z" fill="{GOLD}" opacity=".22"/>
  <!-- 杯盖 -->
  <ellipse cx="80" cy="40" rx="40" ry="11" fill="#1E2A2E"/>
  <ellipse cx="80" cy="40" rx="40" ry="11" stroke="{BRASS}" stroke-width="1.4" opacity=".6"/>
  <!-- 凝结在杯壁上的水珠 -->
  <g fill="{CREAM}" opacity=".38">
    <circle cx="60" cy="96" r="3.2"/><circle cx="98" cy="120" r="2.6"/>
    <circle cx="74" cy="146" r="3"/><circle cx="106" cy="86" r="2.2"/>
  </g>
</svg>"""
    return svg


# --------------------------------------------------------------------------
# 罐头 — 封面。一切都从这里开始，也从这里过期
# --------------------------------------------------------------------------
def can(width: int = 380) -> str:
    u = uid()
    h = int(width * 1.3)
    svg = f"""<svg width="{width}" height="{h}" viewBox="0 0 300 390" fill="none">
  <defs>
    <linearGradient id="cn{u}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#08140F"/>
      <stop offset=".22" stop-color="#2C3941"/>
      <stop offset=".44" stop-color="#4A5860"/>
      <stop offset=".72" stop-color="#1B272D"/>
      <stop offset="1" stop-color="#060F0B"/>
    </linearGradient>
    <linearGradient id="lb{u}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0C1B16"/>
      <stop offset=".4" stop-color="#16302A"/>
      <stop offset="1" stop-color="#08130F"/>
    </linearGradient>
  </defs>
  <ellipse cx="150" cy="366" rx="116" ry="17" fill="#000" opacity=".6"/>
  <!-- 罐身 -->
  <path d="M34 78 h232 v270 a50 18 0 0 1 -232 0 z" fill="url(#cn{u})"/>
  <!-- 标签 -->
  <rect x="34" y="128" width="232" height="150" fill="url(#lb{u})"/>
  <rect x="34" y="128" width="232" height="150" stroke="{GOLD}" stroke-width="1.2" opacity=".38"/>
  <rect x="34" y="128" width="232" height="5" fill="{GOLD}" opacity=".5"/>
  <rect x="34" y="273" width="232" height="5" fill="{GOLD}" opacity=".5"/>
  <!-- 标签上的汉堡剪影 -->
  <g transform="translate(150 200) scale(.52)" opacity=".9">{burger(300)}</g>
  <!-- 顶盖 -->
  <ellipse cx="150" cy="78" rx="116" ry="34" fill="#1C282D"/>
  <ellipse cx="150" cy="78" rx="116" ry="34" stroke="{GOLD}" stroke-width="2.4" opacity=".62"/>
  <ellipse cx="150" cy="78" rx="98" ry="26" fill="none" stroke="{INK}" stroke-width="2" opacity=".8"/>
  <ellipse cx="150" cy="78" rx="86" ry="21" fill="none" stroke="{BRASS}" stroke-width="1" opacity=".4"/>
  <!-- 左侧扫光 -->
  <path d="M46 82 v268" stroke="{GOLD}" stroke-width="4" opacity=".45"/>
  <!-- 底沿 -->
  <ellipse cx="150" cy="348" rx="116" ry="18" fill="none" stroke="{BRASS}" stroke-width="1.4" opacity=".34"/>
</svg>"""
    return svg


# --------------------------------------------------------------------------
# 指针时钟
# --------------------------------------------------------------------------
def clock(size: int = 260, hour: int = 7, minute: int = 54) -> str:
    u = uid()
    # 12 小时制角度：分针每分钟 6 度，时针每小时 30 度 + 分钟带来的偏移
    import math

    def polar(radius: float, deg: float, cx: float = 100, cy: float = 100) -> tuple:
        rad = math.radians(deg - 90)
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    hour_deg = (hour % 12) * 30 + minute * 0.5
    minute_deg = minute * 6
    hx, hy = polar(44, hour_deg)
    mx, my = polar(68, minute_deg)

    ticks = "".join(
        f'<line x1="{polar(80, a*30)[0]:.1f}" y1="{polar(80, a*30)[1]:.1f}" '
        f'x2="{polar(88, a*30)[0]:.1f}" y2="{polar(88, a*30)[1]:.1f}" '
        f'stroke="{CREAM}" stroke-width="3" opacity=".55"/>'
        for a in range(12)
    )
    svg = f"""<svg width="{size}" height="{size}" viewBox="0 0 200 200" fill="none">
  <defs>
    <radialGradient id="ck{u}" cx=".34" cy=".3" r=".85">
      <stop offset="0" stop-color="#152E27"/>
      <stop offset="1" stop-color="#061210"/>
    </radialGradient>
  </defs>
  <circle cx="100" cy="100" r="96" fill="url(#ck{u})"/>
  <circle cx="100" cy="100" r="96" stroke="{GOLD}" stroke-width="3" opacity=".7"/>
  <circle cx="100" cy="100" r="84" stroke="{BRASS}" stroke-width="1" opacity=".3"/>
  {ticks}
  <line x1="100" y1="100" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{CREAM}" stroke-width="9" stroke-linecap="round"/>
  <line x1="100" y1="100" x2="{mx:.1f}" y2="{my:.1f}" stroke="{GOLD}" stroke-width="5.5" stroke-linecap="round"/>
  <circle cx="100" cy="100" r="7" fill="{RED}"/>
  <circle cx="100" cy="100" r="7" stroke="{CREAM}" stroke-width="2" opacity=".7"/>
</svg>"""
    return svg


# --------------------------------------------------------------------------
# 一排同样的东西 — 用于重复制品转型为一道执念
# --------------------------------------------------------------------------
def row(item_svg: str, count: int, gap: int = 18, size: int = 150) -> str:
    cells = "".join(
        f'<div style="opacity:{1 - i * 0.13:.2f}">{item_svg}</div>'
        for i in range(count)
    )
    return (
        f'<div style="display:flex;align-items:flex-end;gap:{gap}px;'
        f'justify-content:center">{cells}</div>'
    )


# --------------------------------------------------------------------------
# 日历格: total 个格子，其中 hits 个被点亮
# --------------------------------------------------------------------------

def calendar_grid(total: int, hits: list[int], cols: int = 10) -> str:
    cells = []
    for i in range(total):
        cls = "cell on" if i in hits else "cell off"
        cells.append(f'<div class="{cls}"></div>')
    return f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">{"".join(cells)}</div>'
