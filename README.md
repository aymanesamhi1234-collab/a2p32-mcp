# A2P-32 Guard — MCP client

[![A2P-32 Guard MCP connector](https://glama.ai/mcp/connectors/org.duckdns.a2p32guard/a2p32-guard/badges/score.svg)](https://glama.ai/mcp/connectors/org.duckdns.a2p32guard/a2p32-guard)

A spend and limit firewall for autonomous agents: it approves or blocks an
action **before** it happens, and a batch either applies completely or not at
all. Hosted service; this repository contains only the MCP client.

## Connect in one line

```bash
claude mcp add --transport http a2p32 https://zealous-unburned-tameness.ngrok-free.dev/mcp
```

Any MCP client that speaks streamable HTTP can use the same URL:

```json
{ "mcpServers": { "a2p32-guard": { "url": "https://zealous-unburned-tameness.ngrok-free.dev/mcp" } } }
```

No install, no runtime, no local process. The endpoint answers `initialize` and
`tools/list` without payment.

## Try without a wallet

```bash
curl -s https://zealous-unburned-tameness.ngrok-free.dev/v1/trial
# {"token":"...","calls":10,"left":10,"expires":"...T23:59:59Z"}
```

Use it as `Authorization: Bearer trial:<token>` against the paid tool. One token
per IP per day, 10 calls. When it runs out you get a normal 402 and pay with
x402.

## Tools

| tool | what it does | price |
|---|---|---|
| `a2p3_describe` | limits you can enforce, with their scale | free |
| `a2p3_status` | current values and state of a tenant | free |
| `a2p3_text` | turn a sentence into orders | free |
| `a2p3_ledger` | usage and simulated billing | free |
| `a2p3_guard` | apply a batch of orders (returns the paid endpoint) | x402 |

Limits you can enforce: daily budget, API rate, write quota, transfer cap,
token burn, queue batch size, retry loop and session lock.

## Numbers (measured, not claimed)

Measured 2026-11-25 with `bench_publico.py --n 200 --c 8`:

| what | p50 | p95 | p99 | rate |
|---|---|---|---|---|
| public endpoint (tunnel edge) | 94.1 ms | 126.0 ms | 178.3 ms | 9.8 req/s |
| local engine | 1.8 ms | 3.4 ms | 5.6 ms | 412.7 req/s |
| engine, 1 producer | 88 ns/order (11.2 M/s) | | | |
| engine, 4 producers, batches of 32 | 23.9 ns/order (41.9 M/s) | | | |
| 402 challenge incl. CDP verify | 2,953 ms (engine adds < 0.2 ms) | | | |

Raw data: `/bench.json` on the endpoint. Public latency is the tunnel edge, not
the engine.

## Pricing (x402 v2 on Base)

    Simulate                 free (120/min)
    First 50 paid calls/day  0.0010 USDC
    Up to 30 actions         0.0050 USDC
    31–256 actions           0.0150 USDC

EIP-3009 signatures settled by the Coinbase CDP facilitator: no account, no API
key, no gas for the buyer. Discovery: `/.well-known/agent.json`,
`/.well-known/x402`, `/openapi.json`, `/llms.txt`.

## Bridge (optional, stdio clients)

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

## License

MIT — applies to this client only.
