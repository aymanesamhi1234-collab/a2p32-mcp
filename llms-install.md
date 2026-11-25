# llms-install.md — install A2P-32 Guard (for agent-driven installers)

This server is **remote**. There is no local process, no npm package and no API key.
Installing it means adding one URL to the MCP client.

## Endpoint

```
https://zealous-unburned-tameness.ngrok-free.dev/mcp
```

- Transport: streamable HTTP (JSON or SSE responses; both accepted).
- Auth: none for `initialize`, `tools/list` and the free tools.
- Fallback URL if the primary is unreachable: `https://a2p32guard.loca.lt/mcp`

## Steps

1. Add a remote MCP server with the URL above (Cline: MCP Servers → Remote Servers → URL;
   Claude Code: `claude mcp add --transport http a2p32 <URL>`).
2. Do not set environment variables or command/args: it is HTTP, not stdio.
3. Verify the connection: `initialize` must answer
   `{"serverInfo":{"name":"a2p3","version":"3.2"}}` and `tools/list` must return 5 tools
   (`a2p3_describe`, `a2p3_guard`, `a2p3_text`, `a2p3_status`, `a2p3_ledger`).
4. Optional: call the `budget-check` prompt so the agent knows to check the budget before
   paying for anything.

## What the agent gets

- `a2p3_describe` — the limits it can enforce (budget, rate, writes, transfers, sessions).
- `a2p3_guard` — approve or block a batch before it happens; all-or-nothing.
- `a2p3_text` — turn a sentence into orders.
- `a2p3_status`, `a2p3_ledger` — state and usage.

## Payment

Free to try: `GET /v1/trial` returns a token for 10 paid calls per IP and day
(`Authorization: Bearer trial:<token>`). Paid calls cost from 0.0010 USDC on Base via
x402 (EIP-3009); the buyer needs no account and pays no gas.

## Do not

- Do not clone this repository to install the server; the bridge is optional and only for
  stdio-only clients.
- Do not ask the user for an API key; there is none.
