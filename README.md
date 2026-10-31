# trade-hub

双均线两套系统（HL `crypto-ma-alert` + Lighter `lighter-ma-bot`）的**只读聚合页**：
一个网址回答「两套系统正常吗 / 仓位怎样 / 最近发生了什么」。

- 数据源：HL `GET /api/hl/status?k=`（127.0.0.1:8100）、Lighter `GET /status /positions /stops /symbols /events`（127.0.0.1:8110），均为各自面板的现成只读接口。
- 本服务**零写操作**：kill / 清仓 / 重置等仍在两个原面板的管理区，聚合页只放跳转按钮。
- 自身不做告警推送（两边看守 cron 已覆盖），只做展示；某一边拉不到就那半边显示「不可用 + 时间戳」，不整页报错。
- 后台每 `HUB_POLL_S`（默认 60s）拉一轮写内存缓存，页面从缓存渲染（<100ms，渲染路径零交易所请求）。

## 配置（环境变量）

| 键 | 必填 | 说明 |
|---|---|---|
| `HUB_TOKEN` | 是 | 本页自己的访问 token（`?k=` 或 cookie） |
| `HUB_HL_TOKEN` | 是 | HL 面板的 `ADMIN_TOKEN`（同时用于 API 调用与跳转链接） |
| `HUB_LT_ADMIN_TOKEN` | 否 | Lighter 面板 `ADMIN_TOKEN`；设了则跳转链接带 admin，不设则公开只读链接 |
| `HUB_HL_BASE` | 否 | 默认 `http://127.0.0.1:8100` |
| `HUB_LT_BASE` | 否 | 默认 `http://127.0.0.1:8110` |
| `HUB_HL_PANEL_BASE` / `HUB_LT_PANEL_BASE` | 否 | 跳转链接基址，默认 `https://ma.222677.xyz` / `https://lt.222677.xyz` |
| `HUB_POLL_S` | 否 | 轮询间隔秒数，默认 60；`0` = 不启动轮询（测试用） |
| `HUB_REQUEST_TIMEOUT_S` | 否 | 上游请求超时，默认 12 |

## 运行

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8120
# 容器（镜像自带默认 CMD，端口 8120）
docker run -d -e HUB_TOKEN=... -e HUB_HL_TOKEN=... -p 127.0.0.1:8120:8120 ghcr.io/larkspur8506/trade-hub:latest
```

- `GET /health` 免鉴权；`GET /` 与 `GET /api/summary` 需要 `?k=<HUB_TOKEN>`（首次访问服务端下 cookie，之后免 k）。
- 测试：`python -m unittest discover -s tests -t .`（CI 为准）。
