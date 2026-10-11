#!/bin/bash
# ============================================================
# 麦麦记忆 · 定时采集安装脚本
#
# 为什么需要你手动跑一次：
#   这个脚本要往 ~/Library/LaunchAgents/ 写文件、并调用 launchctl，
#   这些操作在沙箱里会被系统拦下来。在你自己终端里跑就有权限了。
#
# 它做的只有一件事：每天自动拉一次订单，把时间线续上。
#   （order-list 接口只给最近 10 单，所以「跑得越勤，历史越长」）
#
# 用法：
#   bash install_headless.sh            # 安装 launchd（推荐，macOS）
#   bash install_headless.sh cron       # 或者装 crontab
#   bash install_headless.sh status     # 看状态
#   bash install_headless.sh run        # 立刻手动采一次
#   bash install_headless.sh uninstall  # 卸载
# ============================================================
set -e

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="cn.mcd.memories.collector"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="${PYTHON:-$(command -v python3)}"
LOG="$PROJ/data/collector.log"

if [ -z "$PY" ]; then
  echo "✗ 找不到 python3。装一个，或用 PYTHON=/path/to/python3 bash $0 指定路径。"
  exit 1
fi

if [ ! -f "$PROJ/.env" ]; then
  echo "✗ 还没有 $PROJ/.env —— 没有 Token 采不到数据。"
  echo "  先执行：echo 'MCD_MCP_TOKEN=你的token' > $PROJ/.env && chmod 600 $PROJ/.env"
  exit 1
fi

collect() {
  cd "$PROJ"
  mkdir -p data
  {
    echo "───── $(date '+%Y-%m-%d %H:%M:%S') ─────"
    "$PY" scripts/fetch_orders.py
    "$PY" scripts/stories.py --json
  } >> "$LOG" 2>&1
}

case "${1:-launchd}" in

  launchd)
    echo "→ 安装 launchd 任务（每天 08:30 与 21:30 各采一次）"
    mkdir -p "$(dirname "$PLIST_DST")"
    cat > "$PLIST_DST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd "$PROJ" &amp;&amp; "$PY" scripts/fetch_orders.py &amp;&amp; "$PY" scripts/stories.py --json &gt;&gt; "$LOG" 2&gt;&amp;1</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>RunAtLoad</key><false/>
  <key>StandardErrorPath</key><string>$PROJ/data/collector.err.log</string>
</dict>
</plist>
PLIST

    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load "$PLIST_DST"
    echo "✓ 已装载。验证：launchctl list | grep mcd.memories"
    ;;

  cron)
    echo "→ 安装 crontab（每天 08:30 与 21:30）"
    ( crontab -l 2>/dev/null | grep -v "$LABEL"; \
      echo "30 8,21 * * * cd \"$PROJ\" && \"$PY\" scripts/fetch_orders.py >> \"$LOG\" 2>&1  # $LABEL" \
    ) | crontab -
    echo "✓ 已安装，当前 crontab："
    crontab -l | grep "$LABEL" || true
    ;;

  status)
    echo "=== launchd ==="
    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
      launchctl list | grep "$LABEL"
    else
      echo "  未装载"
    fi
    echo "=== crontab ==="
    crontab -l 2>/dev/null | grep "$LABEL" || echo "  未安装"
    echo "=== 已入库订单 ==="
    "$PY" - <<PYEOF
import json, os
p = os.path.join("$PROJ", "data", "orders.json")
if not os.path.exists(p):
    print("  还没有数据，先跑一次：bash install_headless.sh run")
else:
    orders = json.load(open(p, encoding="utf-8"))
    days = sorted({o["date"] for o in orders if o.get("date")})
    print(f"  {len(orders)} 单 · 跨度 {days[0]} → {days[-1]}（{len(days)} 个用餐日）")
PYEOF
    echo "=== 最近采集日志 ==="
    tail -6 "$LOG" 2>/dev/null || echo "  无日志"
    ;;

  run)
    echo "→ 手动采一次"
    collect
    echo "✓ 完成，日志见 data/collector.log"
    ;;

  uninstall)
    echo "→ 卸载"
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    rm -f "$PLIST_DST"
    crontab -l 2>/dev/null | grep -v "$LABEL" | crontab - || true
    echo "✓ 已卸载（已采集的数据保留在 data/ 里）"
    ;;

  *)
    echo "用法：bash $0 [launchd|cron|status|run|uninstall]"
    ;;
esac
