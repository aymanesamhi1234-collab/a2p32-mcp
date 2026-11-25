# Use the guard from your agent

One call, before the money moves: the batch is applied completely or not at all.
The first 5 actions of a call are free, so these snippets work with no wallet.

| framework | file | what it does |
|---|---|---|
| LangChain (Python) | `langchain_guard.py` | `@tool guard_batch(orders)` calls the guard and returns its decision |
| Vercel AI SDK (TS) | `vercel_ai_sdk.ts` | `guardBatch` tool with a zod schema for `orders` |
| Open WebUI | `openwebui_spend_guard.py` | paste into Workspace → Tools; adds `guard_batch` (standard Tools interface, not yet exercised inside Open WebUI) |
| MCP clients | any | add `https://zealous-unburned-tameness.ngrok-free.dev/mcp` as a streamable-http server |

Order shape:

```json
{"root": "BUDGET.USD", "action": "INCREASE", "value_dec": 5}
```

`root` is one of `BUDGET.USD`, `API.RATE`, `DB.WRITE`, `TRANSFER.LIMIT`,
`TOKEN.BURN`, `QUEUE.BATCH`, `RETRY.LOOP`, `SESSION.LOCK`. `value_dec` is in
human units; `value` is in the limit's own scale (BUDGET.USD scale 100: 73.50 is
`7350`). `lock: true` trips the tenant's circuit breaker when the order violates
a limit, and every later call from that tenant answers `L` until it is reset.

Answer:

```json
{"ok": true,  "codes": "0",   "values": {"BUDGET.USD": 6200}, "latched": false}
{"ok": false, "codes": "M",   "values": {"BUDGET.USD": 5000}, "latched": false}
{"ok": false, "codes": "T",   "values": {}, "latched": true}
```

`M` = blocked by a limit, nothing applied. `T` = safety lock. `L` = tenant locked.
