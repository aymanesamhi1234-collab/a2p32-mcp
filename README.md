# A2P-32 Guard — MCP client

[![A2P-32 Guard MCP connector](https://glama.ai/mcp/connectors/org.duckdns.a2p32guard/a2p32-guard/badges/score.svg)](https://glama.ai/mcp/connectors/org.duckdns.a2p32guard/a2p32-guard)
[![endpoint health](https://github.com/aymanesamhi1234-collab/a2p32-mcp/actions/workflows/health.yml/badge.svg)](https://github.com/aymanesamhi1234-collab/a2p32-mcp/actions/workflows/health.yml)

A spend and limit firewall for autonomous agents: it approves or blocks an
action **before** it happens, and a batch either applies completely or not at
all. Hosted service; this repository contains only the MCP client.

## Listed on

- [Cursor Directory](https://cursor.directory/plugins/a2p-32-guard) (verification pending)
- [Glama connector](https://glama.ai/mcp/connectors/org.duckdns.a2p32guard/a2p32-guard)
- Official MCP registry: `org.duckdns.a2p32guard/a2p32-guard`
- [agent-tools.cloud](https://agent-tools.cloud/a2a/agents/a2p-32-deterministic-guard) (MCP + A2A)
- x402scan · Agent Bazaar · scriptmaster x402 directory
- mcp.directory · mcpservers.org (in review) · Docker MCP Registry (PR #7701)

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
x402. MCP clients get the same free `a2p3_guard` calls per IP and day without any
header, so the first tool call just works. The free quota grows with daily use:
10 calls on day one, +5 per consecutive day, up to 50.

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

## Use it from your agent

Copy-paste tools for LangChain (Python) and the Vercel AI SDK (TypeScript), plus
the MCP config: [`integrations/`](integrations/). The first 5 actions of a call
are free, so they work with no wallet.

## Numbers (measured, not claimed)

Measured 2026-11-25, keep-alive connections:

| what | p50 | p95 | rate |
|---|---|---|---|
| server, 1 connection (local) | 0.25 ms | 0.49 ms | 4,000 req/s |
| server, 8 connections (local) | 0.53 ms | — | 11,600 req/s |
| public endpoint, keep-alive (tunnel) | 80 ms | 126 ms | 78 req/s (8 conns) |
| public endpoint, new connection | 175 ms | — | 9.8 req/s |
| paid call end to end (guardpay, warm) | 345 ms | — | — |
| CDP verify (warm) | 165 ms | — | — |
| engine, 1 producer | 88 ns/order (11.2 M/s) | | |
| engine, 4 producers, batches of 32 | 23.9 ns/order (41.9 M/s) | | |

Public latency is the tunnel round trip (2 × ~40 ms to the edge); the server
itself answers in 0.25 ms. Reuse connections: a new TLS handshake costs ~95 ms
on top of the trip.

Raw data: `/bench.json` on the endpoint.


Measured comparison of the guard endpoints in this market (price and 402
latency, same machine, same day): <https://aymanesamhi1234-collab.github.io/a2p32-mcp/guards.html>

## Verified end to end (Base Sepolia, 2026-11-25)

A real settlement through the CDP facilitator, no mock: fresh payer wallet funded
from the CDP faucet, six-order paid batch, HTTP 200, and the receipt header
`X-PAYMENT-RESPONSE` carrying the transaction hash.

- tx: <https://sepolia.basescan.org/tx/0xf0b54916d14feec3508c88631dbfa461105ca5b670587c46df114d94ca8cf596>
- status 1, 86,262 gas, logs `AuthorizationUsed` + `Transfer` on USDC
- payer −0.001 USDC, seller +0.001; four paid calls moved 0.004 USDC in total
- paid call end to end (verify + on-chain settle + task): 1.0–1.4 s
- the engine itself adds ~80 µs to that call

Mainnet is the same code and a funded wallet; the only difference is the chain id
and the USDC address.

## What it saves

| case | without | with | saving |
|---|---|---|---|
| 30 governance actions | 30 calls · ~4,170 tokens | 1 batch · ~390 tokens | 10.7x fewer tokens |
| price of one batch of 30 | median guard listing: 0.0075 USDC per decision | 0.0050 USDC per batch | one batch < one decision elsewhere |
| buyer gas | — | 0 (CDP facilitator) | no gas |

Free preflight without a wallet:

```bash
curl -s "https://zealous-unburned-tameness.ngrok-free.dev/v1/check?budget=50&spent=12.4&amount=0.05"
curl -s "https://zealous-unburned-tameness.ngrok-free.dev/v1/savings?actions=30"
```

## Pricing (x402 v2 on Base)

    Simulate                 free (120/min)
    Up to 5 actions          free, always (120/min)
    First 50 paid calls/day  0.0010 USDC
    Up to 30 actions         0.0050 USDC
    31–256 actions           0.0150 USDC

EIP-3009 signatures settled by the Coinbase CDP facilitator: no account, no API
key, no gas for the buyer. Discovery: `/.well-known/agent.json`,
`/.well-known/x402`, `/openapi.json`, `/llms.txt`.

### Paying from your own code

`guardpay.py` puts the guard in front of the payment: it reads the 402 price,
refuses locally if it exceeds your cap, asks the free preflight whether the
amount fits the remaining budget, and only then signs and retries.

```python
from guardpay import GuardPay
gp = GuardPay(budget_usd=25, key=os.environ["EVM_KEY"])
r = gp.pay("https://zealous-unburned-tameness.ngrok-free.dev/", body={...}, max_usd=0.01)
```

Troubleshooting: if the payer account has code on Base (an EIP-7702 delegation
or a contract), USDC validates the signature through ERC-1271 and rejects a
plain EOA signature, so the facilitator answers `invalid_exact_evm_payload_signature`.
`guardpay` checks `eth_getCode` before signing and refuses with a clear message
instead of burning the attempt. Use a clean EOA to pay.

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
