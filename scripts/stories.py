#!/usr/bin/env python3
"""故事引擎：把结构化订单变成一组「值得被说出来」的事实。

这里不做任何抒情。本模块只负责从真实字段里算出数字与事实，
文案由 templates/ 里的模板消费。任何一个卡片如果算不出数据，
就会被整个丢掉 —— 保证报告里不出现一句编造的话。

用法：
    python3 scripts/stories.py          # 打印全部洞察
    python3 scripts/stories.py --json   # 输出 stories.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDERS_JSON = ROOT / "data" / "orders.json"
STORIES_JSON = ROOT / "data" / "stories.json"

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 把商品名归到「品类」桶里，用于算偏好。顺序敏感：先匹配先命中。
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("无糖可乐", ("无糖",)),
    ("可乐", ("可乐",)),
    ("咖啡", ("咖啡", "美式", "拿铁", "鲜萃冰咖")),
    ("雪碧", ("雪碧",)),
    ("薯条", ("薯条",)),
    ("鸡翅", ("鸡翅",)),
    ("冰淇淋", ("冰淇淋", "新地", "麦旋风")),
    ("派", ("派",)),
]


def categorize(name: str) -> str:
    for label, keys in CATEGORY_RULES:
        if any(k in name for k in keys):
            return label
    return "其他"


def meal_slot(hour: int | None) -> str:
    if hour is None:
        return "未知"
    if 5 <= hour < 11:
        return "早餐"
    if 11 <= hour < 14:
        return "午餐"
    if 14 <= hour < 17:
        return "下午茶"
    if 17 <= hour < 22:
        return "晚餐"
    return "深夜"


def load_orders() -> list[dict]:
    if not ORDERS_JSON.exists():
        raise SystemExit("找不到 data/orders.json，请先运行 scripts/fetch_orders.py")
    return json.loads(ORDERS_JSON.read_text(encoding="utf-8"))


def parse_dt(order: dict) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(order["created_at"], fmt)
        except (ValueError, KeyError):
            continue
    return None


def build() -> dict:
    orders = load_orders()
    dated = [(parse_dt(o), o) for o in orders]
    dated = [(d, o) for d, o in dated if d]
    dated.sort(key=lambda pair: pair[0])
    if not dated:
        raise SystemExit("订单里没有可用的时间字段。")

    n = len(dated)
    first_dt, first = dated[0]
    last_dt, last = dated[-1]
    span_days = (last_dt.date() - first_dt.date()).days

    # ---- 门店 ----
    store_counter = Counter(o["store"] for _, o in dated)
    stores = []
    for name, count in store_counter.most_common():
        pick = next(o for _, o in dated if o["store"] == name)
        stores.append(
            {
                "name": name,
                "count": count,
                "first_date": next(d for d, o in dated if o["store"] == name).strftime("%Y-%m-%d"),
                "sample_combo": pick["items"][0]["name"] if pick["items"] else "",
            }
        )

    # ---- 套餐 / 单品 ----
    combo_counter = Counter()
    single_counter = Counter()
    category_counter = Counter()
    for _, o in dated:
        for item in o["items"]:
            combo_counter[item["name"]] += item["qty"]
        for s in o["singles"]:
            single_counter[s["name"]] += s["qty"]
            category_counter[categorize(s["name"])] += s["qty"]

    top_combos = [{"name": k, "count": v} for k, v in combo_counter.most_common(3)]
    top_singles = [{"name": k, "count": v} for k, v in single_counter.most_common(5)]

    # ---- 饮品偏好（这是本项目最锋利的一个发现）----
    drinks = Counter()
    orders_with_sugarfree = 0
    orders_with_coffee = 0
    for _, o in dated:
        names = [s["name"] for s in o["singles"]]
        if any("无糖" in x for x in names):
            orders_with_sugarfree += 1
        if any(categorize(x) == "咖啡" for x in names):
            orders_with_coffee += 1
        for x in names:
            cat = categorize(x)
            if cat in ("无糖可乐", "咖啡", "雪碧", "可乐"):
                drinks[cat] += 1

    # ---- 时段 ----
    slots = Counter(meal_slot(o["hour"]) for _, o in dated)
    hours = [o["hour"] for _, o in dated if o["hour"] is not None]
    earliest = min(dated, key=lambda p: (p[1]["time"] or "99:99"))
    latest = max(dated, key=lambda p: (p[1]["time"] or "00:00"))

    # ---- 星期 ----
    weekday_counter = Counter(WEEKDAY_CN[d.weekday()] for d, _ in dated)

    # ---- 空窗期 ----
    gaps = []
    for i in range(1, len(dated)):
        delta = (dated[i][0].date() - dated[i - 1][0].date()).days
        gaps.append((delta, dated[i - 1][0], dated[i][0]))
    gaps.sort(reverse=True)
    biggest_gap = None
    if gaps:
        delta, before, after = gaps[0]
        biggest_gap = {
            "days": delta,
            "from": before.strftime("%Y-%m-%d"),
            "to": after.strftime("%Y-%m-%d"),
        }

    # ---- 月度分布 ----
    month_counter = Counter(d.strftime("%Y-%m") for d, _ in dated)
    months = [{"month": k, "count": v} for k, v in sorted(month_counter.items())]
    quietest_months: list[dict] = []
    if months:
        floor = min(m["count"] for m in months)
        quietest_months = [m for m in months if m["count"] == floor]

    # ---- 节奏变化：以时间中位点把时间线对半切，比较"每周光顾几次" ----
    # 用中位点而不是自然月，是为了避免月份天数不等带来的偏差。
    pivot = dated[len(dated) // 2][0]
    early = [d for d, _ in dated if d < pivot]
    late = [d for d, _ in dated if d >= pivot]
    span_early = max((pivot - dated[0][0]).days, 1)
    span_late = max((dated[-1][0] - pivot).days, 1)
    rhythm = {
        "pivot_date": pivot.strftime("%Y-%m-%d"),
        "early": {
            "orders": len(early),
            "days": span_early,
            "per_week": round(len(early) / span_early * 7, 2),
        },
        "late": {
            "orders": len(late),
            "days": span_late,
            "per_week": round(len(late) / span_late * 7, 2),
        },
        "ratio": None,
    }
    if rhythm["early"]["per_week"] > 0:
        rhythm["ratio"] = round(
            rhythm["late"]["per_week"] / rhythm["early"]["per_week"], 1
        )

    # ---- 分水岭：第二家门店首次出现的那一天，以及从那天起养成的新习惯 ----
    turning_point = None
    if len(stores) >= 2:
        newest = max(stores, key=lambda s: s["first_date"])
        cut = datetime.strptime(newest["first_date"], "%Y-%m-%d")
        after = [o for d, o in dated if d >= cut]
        before = [o for d, o in dated if d < cut]
        after_counter: Counter = Counter()
        for order in after:
            for item in order["items"]:
                after_counter[item["name"]] += item["qty"]
        seen_before = {it["name"] for order in before for it in order["items"]}
        fresh = [
            {"name": k, "count": v}
            for k, v in after_counter.most_common()
            if k not in seen_before and v >= 2
        ]
        turning_point = {
            "date": newest["first_date"],
            "weekday": WEEKDAY_CN[cut.weekday()],
            "new_store": newest["name"],
            "orders_before": len(before),
            "orders_after": len(after),
            "new_favorite": fresh[0] if fresh else None,
        }

    # ---- 金额（默认不展示，用户可开）----
    amounts = [o["amount"] for _, o in dated if o["amount"] is not None]
    money = {
        "total": round(sum(amounts), 2) if amounts else None,
        "avg": round(sum(amounts) / len(amounts), 2) if amounts else None,
        "max": max(amounts) if amounts else None,
        "min": min(amounts) if amounts else None,
    }

    return {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_orders": n,
            "span_days": span_days,
            "first_date": first_dt.strftime("%Y-%m-%d"),
            "last_date": last_dt.strftime("%Y-%m-%d"),
            "store_count": len(stores),
        },
        "first_order": {
            "date": first_dt.strftime("%Y-%m-%d"),
            "time": first_dt.strftime("%H:%M"),
            "weekday": WEEKDAY_CN[first_dt.weekday()],
            "store": first["store"],
            "combo": first["items"][0]["name"] if first["items"] else "",
            "singles": [s["name"] for s in first["singles"]],
        },
        "last_order": {
            "date": last_dt.strftime("%Y-%m-%d"),
            "time": last_dt.strftime("%H:%M"),
            "weekday": WEEKDAY_CN[last_dt.weekday()],
            "store": last["store"],
            "combo": last["items"][0]["name"] if last["items"] else "",
        },
        "stores": stores,
        "top_combos": top_combos,
        "top_singles": top_singles,
        "drinks": {
            "sugarfree_orders": orders_with_sugarfree,
            "coffee_orders": orders_with_coffee,
            "breakdown": [{"name": k, "count": v} for k, v in drinks.most_common()],
        },
        "slots": [{"slot": k, "count": v} for k, v in slots.most_common()],
        "earliest": {
            "time": earliest[1]["time"],
            "date": earliest[1]["date"],
            "store": earliest[1]["store"],
            "combo": earliest[1]["items"][0]["name"] if earliest[1]["items"] else "",
        },
        "latest": {
            "time": latest[1]["time"],
            "date": latest[1]["date"],
            "store": latest[1]["store"],
            "combo": latest[1]["items"][0]["name"] if latest[1]["items"] else "",
        },
        "weekdays": [{"day": k, "count": v} for k, v in weekday_counter.most_common()],
        "biggest_gap": biggest_gap,
        "months": months,
        "quietest_months": quietest_months,
        "rhythm": rhythm,
        "turning_point": turning_point,
        "money": money,
    }


def main() -> int:
    stories = build()
    if "--json" in sys.argv:
        STORIES_JSON.write_text(
            json.dumps(stories, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"已写入 {STORIES_JSON.relative_to(ROOT)}")
        return 0
    print(json.dumps(stories, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
