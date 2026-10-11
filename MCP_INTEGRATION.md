# MCP 集成说明

本项目「麦麦记忆 · mcd-memories」基于**麦当劳中国官方 MCP** 开发，全程只调用一个只读接口：`order-list`。

---

## 一、使用的 MCP Server

| 项目 | 内容 |
|---|---|
| MCP Server | 麦当劳中国官方 MCP（`mcd-mcp`） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 认证方式 | 请求头 `Authorization: Bearer ${MCD_MCP_TOKEN}` |
| Token 申请 | https://open.mcd.cn/mcp → 手机号登录 → 右上角「控制台」→ 激活 → 复制 |
| 配置示例 | `mcp-config.example.json`（仓库内，**仅含环境变量占位符，不含任何真实凭证**） |

---

## 二、实际使用的 MCP Tool

| Tool 名称 | 在本项目中的作用 | 调用方式 | 是否写操作 |
|---|---|---|---|
| `order-list` | 拉取本人（登录会员）的历史订单，作为全部内容的数据源 | 每次运行调用 1 次；挂定时任务后每天 2 次 | **否，只读** |

**明确未调用的能力**：项目不调用 `create-order`、`cancel-order`、`mall-create-order`、`auto-bind-coupons`、`draw-lottery`、`party-order-create` 等任何下单、支付、改单、领券、抽奖类接口。

`mcd-memories` 的客户端（`scripts/mcd_client.py`）在初始化时向 MCP Server 声明的身份为：

```json
{"clientInfo": {"name": "mcd-memories", "version": "1.0.0"}}
```

客户端模块只暴露 `raw_call()` / `json_call()` 两个读方法，**没有提供任何写操作入口**。

---

## 三、调用流程

```
① 建立会话
   scripts/mcd_client.py → POST https://mcp.mcd.cn
   Header: Authorization: Bearer ${MCD_MCP_TOKEN}

② 取数（唯一一次 MCP 调用）
   scripts/fetch_orders.py → client.json_call("order-list")
   解析 data.list[] → orderProductList[] → comboItemList[]
   扁平化为 {order_id, time, store, items[], amount}

③ 沉淀（绕开接口上限的关键设计）
   order-list 官方固定只返回最近 10 单，不支持分页、不支持传时间范围。
   本项目每次运行都把当次结果落一份快照 data/snapshots/YYYY-MM-DD.json，
   再与累积库 data/orders.json 按 order_id 合并去重。
   → 第一天只能讲 10 顿饭；跑得越久，时间线越长。

④ 计算
   scripts/stories.py 从订单里算出九幕需要的每个数字
   （首末单间隔、第一次点了什么、跨度天数、去过几家店、重复最多的组合、
    单品排行、频率突变点、最长空窗期……）
   算不出来的那一幕会被整页丢掉 —— 数据里没有的，文案不编。

⑤ 呈现
   scripts/cards.py 把数字排成 HTML（纯 CSS 布光，零素材依赖）
   scripts/render.py 用本机 Chrome 无头模式把 HTML 冲印成 1080×1440 PNG
   → 九幕图文长卷，可直接发小红书或导出长图 / PDF
```

数据全程留在本机硬盘：无服务器、无埋点、无第三方 API，图片生成在本地，发不发由用户决定。
`.env`（Token）、`data/`（真实订单）、`output/`（真实成品图）三者在 `.gitignore` 中默认不入库。

---

## 四、业务价值

**对用户**：麦当劳的订单数据是「只有本人能读、但从来没被好好看过」的数据。本项目把它从一串流水，变成一条可回看的时间线 —— 第一次点了什么、最常去哪家店、哪天之后频率忽然变了、最长多久没吃。它不帮你省钱、不算卡路里、不推荐吃什么，只把已经发生过的事讲成一个故事。

**对麦当劳 MCP 生态**：目前参赛项目集中在「省钱 / 券 / 营养 / 点单」几条拥挤赛道，本项目示范了官方只读接口在**数据沉淀 + 情感化表达**这一全新方向上的用法 —— 同一个 `order-list`，不做效率工具，做记忆载体。

**对接口能力本身的诚实呈现**：`order-list` 只返回最近 10 单，是接口的天花板，不是 bug。本项目没有回避这个限制，而是用「每日快照 + 累积去重」把它变成产品特性（跑得越久越完整），并把它明确写进 README，避免用户对数据完整性产生误解。

---

## 五、无 Token 时的降级路径

不申请 Token 也能完整体验：

```bash
python3 scripts/cards.py --demo --format cards
python3 scripts/render.py
```

`--demo` 全程离线，使用 `examples/demo-stories.json` 中的**虚构**样例数据渲染，成品样式与真实运行完全一致。README 中展示的每一张预览图，均由这份虚构数据生成，不含任何人的真实消费记录。
