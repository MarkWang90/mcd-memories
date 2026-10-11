#!/usr/bin/env bash
# 麦麦记忆 · 一条命令跑完全流程
#
#   bash run.sh
#
# 产出：output/png/ 下的八张竖图 + output/png/00-github封面.png
# 全程只读，不会向你的麦当劳账户写入任何东西。

set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if [ ! -f .env ]; then
  echo ""
  echo "还没有 .env —— 缺少 Token 拿不到数据。"
  echo ""
  echo "  1. 打开 https://open.mcd.cn/mcp ，登录后激活 MCP，复制那串 Token"
  echo "  2. 执行：echo 'MCD_MCP_TOKEN=你的token' > .env && chmod 600 .env"
  echo "  3. 再跑一次：bash run.sh"
  echo ""
  exit 1
fi

echo "── 1/4 读取订单 ──────────────────────────────"
"$PY" scripts/fetch_orders.py

echo "── 2/4 算规律 ────────────────────────────────"
"$PY" scripts/stories.py --json

echo "── 3/4 排版 ──────────────────────────────────"
"$PY" scripts/cards.py

echo "── 4/4 冲印成图 ─────────────────────────────"
"$PY" scripts/render.py

echo ""
echo "好了：$PWD/output/png/"
ls -1 output/png/*.png 2>/dev/null | sed 's|.*/|  |'
