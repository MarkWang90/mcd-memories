#!/usr/bin/env python3
"""抓取用餐订单并解析成结构化数据。

关于数据边界（重要，写进 README 的前提）：
    麦当劳 order-list 接口只返回「最近 10 单」，官方固定上限，不支持分页、
    不支持传时间范围。这不是 bug，是接口本身的天花板。

    所以本项目做了一个小设计：每次运行都把当次快照落到 data/snapshots/，
    并与累积库 data/orders.json 合并去重。你跑得越久，时间线越长。
    第一天的报告只能讲 10 顿，半年后可能就能讲 60 顿。

用法：
    python3 scripts/fetch_orders.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcd_client import MCDClient, MCDError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
ORDERS_JSON = DATA / "orders.json"

STORE_NOISE = re.compile(r"^(麦当劳)?(北京|上海|广州|深圳|中国)?")
LOCATION_WORDS = ("餐厅", "门店")


def clean_store_name(raw: str) -> str:
    """把「麦当劳北京西二旗西路(上地元中心)餐厅」压成「西二旗西路(上地元中心)」。"""
    name = (raw or "").strip()
    name = re.sub(r"^麦当劳", "", name)
    name = re.sub(r"^(北京|上海|广州|深圳|天津|重庆|成都|杭州|武汉|西安|南京|苏州)市?", "", name)
    for word in LOCATION_WORDS:
        name = name.replace(word, "")
    return name.strip() or (raw or "").strip()


def to_float(value) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def parse_orders(payload: dict) -> list[dict]:
    """把 order-list 的原始返回解析成扁平化的订单列表。"""
    rows = (payload.get("data") or {}).get("list") or []
    orders: list[dict] = []
    for row in rows:
        items, singles = [], []
        for product in row.get("orderProductList") or []:
            combo = []
            for child in product.get("comboItemList") or []:
                name = (child.get("name") or "").strip()
                qty = int(child.get("quantity") or 1)
                if name:
                    combo.append({"name": name, "qty": qty})
                    singles.append({"name": name, "qty": qty})
            items.append(
                {
                    "name": (product.get("productName") or "").strip(),
                    "qty": int(product.get("quantity") or 1),
                    "combo": combo,
                }
            )
            if not combo:
                # 单点商品（汉堡、咖啡这类没有子项的）本身就是"单品"
                pname = (product.get("productName") or "").strip()
                if pname:
                    singles.append({"name": pname, "qty": int(product.get("quantity") or 1)})

        created = (row.get("createTime") or "").strip()
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(created, fmt)
                break
            except ValueError:
                continue

        orders.append(
            {
                "order_id": row.get("orderId"),
                "created_at": created,
                "date": dt.strftime("%Y-%m-%d") if dt else None,
                "time": dt.strftime("%H:%M") if dt else None,
                "hour": dt.hour if dt else None,
                "weekday": dt.weekday() if dt else None,
                "store_raw": (row.get("storeName") or "").strip(),
                "store": clean_store_name(row.get("storeName") or ""),
                "store_code": row.get("storeCode"),
                "status": (row.get("orderStatus") or "").strip(),
                "amount": to_float(row.get("realTotalAmount")),
                "items": items,
                "singles": singles,
            }
        )

    orders.sort(key=lambda o: o.get("created_at") or "")
    return orders


def merge_history(new_orders: list[dict]) -> tuple[list[dict], int]:
    """与累积库合并去重，返回（全集, 本次新增条数）。"""
    existing: dict[str, dict] = {}
    if ORDERS_JSON.exists():
        try:
            for order in json.loads(ORDERS_JSON.read_text(encoding="utf-8")):
                if order.get("order_id"):
                    existing[order["order_id"]] = order
        except (json.JSONDecodeError, TypeError):
            pass

    added = 0
    for order in new_orders:
        oid = order.get("order_id")
        if not oid:
            continue
        if oid in existing:
            existing[oid].update(order)  # 以最新解析结果为准
        else:
            existing[oid] = order
            added += 1

    merged = sorted(existing.values(), key=lambda o: o.get("created_at") or "")
    return merged, added


def main() -> int:
    try:
        client = MCDClient().connect()
    except MCDError as exc:
        print(f"✗ {exc}")
        return 1

    payload = client.json_call("order-list")
    fresh = parse_orders(payload)
    if not fresh:
        print("✗ 没有解析到任何订单，请检查 Token 与账号状态。")
        return 1

    DATA.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    (SNAPSHOTS / f"{stamp}.json").write_text(
        json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    merged, added = merge_history(fresh)
    ORDERS_JSON.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stores = sorted({o["store"] for o in merged})
    span = f"{merged[0]['date']} → {merged[-1]['date']}" if merged else "-"
    print(f"本次接口返回 {len(fresh)} 单｜累积库 {len(merged)} 单（新增 {added}）")
    print(f"时间跨度：{span}")
    print(f"涉及门店 {len(stores)} 家：{'、'.join(stores)}")
    print(f"已写入 {ORDERS_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
