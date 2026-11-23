# A2P-32 Guard — MCP client

A thin MCP (stdio) bridge for **A2P-32 Guard**, a hosted service that gives
autonomous agents deterministic governance: spend budgets, rate limits, write
quotas and transfer caps enforced as **per-aspect limits**, with batches that
either apply completely or not at all.

This package contains **only the client**. The engine runs behind the hosted
endpoint; there is no engine code here.

## Tools

| tool | what it does | price |
|---|---|---|
| `a2p3_describe` | roots, scales and limits available to you | free |
| `a2p3_status` | current values and state of a tenant | free |
| `a2p3_text` | turn a sentence into orders | free |
| `a2p3_ledger` | usage and simulated billing | free |
| `a2p3_guard` | apply a batch of orders (returns the paid endpoint) | x402 |

Roots: `BUDGET.USD`, `API.RATE`, `DB.WRITE`, `TRANSFER.LIMIT`, `TOKEN.BURN`,
`QUEUE.BATCH`, `RETRY.LOOP`, `SESSION.LOCK`.

## Install

No dependencies beyond the Python standard library (3.10+).

```json
{
  "mcpServers": {
    "a2p32-guard": {
      "command": "python3",
      "args": ["/absolute/path/to/bridge.py"],
      "env": { "A2P_MCP_URL": "https://zealous-unburned-tameness.ngrok-free.dev/mcp" }
    }
  }
}
```

Override the endpoint with `A2P_MCP_URL` to point at your own deployment.

## Pricing (HTTP, x402 v2 on Base)

    Simulate                 free (120/min)
    Guard, first 50/day      0.0010 USDC
    Guard, up to 30 orders   0.0050 USDC
    Guard, 31–256 orders     0.0150 USDC

Payments are EIP-3009 signatures settled by the Coinbase CDP facilitator: no
account, no API key, no gas for the buyer. Discovery:
`/.well-known/agent.json`, `/.well-known/x402`, `/openapi.json`.

## License

MIT — applies to this client only.
