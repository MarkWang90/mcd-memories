#!/usr/bin/env python3
"""麦当劳 MCP 极简只读客户端。

麦当劳 MCP 的响应是「给人看的说明」+「一段可解析的 JSON」拼在一起，
本模块负责把两者剥开，并把所有调用收敛成两个方法：

    client.raw_call(tool)   -> 原始文本
    client.json_call(tool)  -> 解析后的 dict

设计原则：只读。这个模块不提供任何写操作入口。
凭证只从 .env 或环境变量读取，任何时候都不会被打印出来。
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENDPOINT = "https://mcp.mcd.cn"


def load_config() -> dict:
    """读取 .env 与环境变量，环境变量优先。"""
    cfg: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip()
    if os.environ.get("MCD_MCP_TOKEN"):
        cfg["MCD_MCP_TOKEN"] = os.environ["MCD_MCP_TOKEN"]
    return cfg


class MCDError(RuntimeError):
    pass


class MCDClient:
    def __init__(self, token: str | None = None, endpoint: str | None = None) -> None:
        cfg = load_config()
        self.token = token or cfg.get("MCD_MCP_TOKEN")
        self.endpoint = (
            endpoint or cfg.get("MCD_MCP_ENDPOINT") or DEFAULT_ENDPOINT
        ).rstrip("/")
        if not self.token:
            raise MCDError(
                "缺少 MCD_MCP_TOKEN。请在项目根目录的 .env 中配置，"
                "或设置同名环境变量。Token 可在 https://open.mcd.cn/mcp 激活获取。"
            )
        self._id = 0
        self.initialized = False

    # ---------- 传输层 ----------

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            hint = {
                401: "Token 失效或未激活，请重新激活获取新 Token。",
                403: "Token 无权访问该工具。",
                429: "触发限流，稍后再试。",
            }.get(exc.code, "")
            raise MCDError(f"HTTP {exc.code} {hint}") from exc
        except urllib.error.URLError as exc:
            raise MCDError(f"网络不可达：{exc.reason}") from exc

        # Streamable HTTP 会返回 SSE 帧，取最后一个 data: 负载
        if raw.lstrip().startswith("event:") or "\ndata:" in raw:
            frames = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
            if frames:
                raw = frames[-1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MCDError(f"响应不是合法 JSON：{raw[:200]}") from exc

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        return self._post(
            {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        )

    # ---------- 协议层 ----------

    def connect(self) -> "MCDClient":
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcd-memories", "version": "1.0.0"},
            },
        )
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            pass  # 通知帧没有响应，失败无妨
        self.initialized = True
        return self

    def tools(self) -> list[dict]:
        return self._rpc("tools/list").get("result", {}).get("tools", [])

    def raw_call(self, name: str, arguments: dict | None = None) -> str:
        resp = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in resp:
            raise MCDError(f"{name} 调用失败：{resp['error'].get('message', resp['error'])}")
        content = resp.get("result", {}).get("content") or []
        return content[0].get("text", "") if content else ""

    def json_call(self, name: str, arguments: dict | None = None) -> dict:
        """调用工具并把内嵌的 JSON 段解析出来。"""
        text = self.raw_call(name, arguments)
        match = re.search(r"##\s*Original Response\s*\n+(\{.*)", text, re.S)
        blob = (match.group(1) if match else text).strip()
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            start, end = blob.find("{"), blob.rfind("}")
            if start >= 0 and end > start:
                return json.loads(blob[start : end + 1])
            raise MCDError(f"{name} 的响应里找不到 JSON")


if __name__ == "__main__":
    client = MCDClient().connect()
    print(f"已连接 {client.endpoint}")
    print(f"可用工具 {len(client.tools())} 个")
