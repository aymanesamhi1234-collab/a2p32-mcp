"""LangChain tool: ask A2P-32 Guard before an agent spends or writes.

    pip install langchain-core
    from integrations.langchain_guard import guard_batch
    agent = create_react_agent(llm, [guard_batch])

The first 5 actions of a call are free, so the tool works with no wallet.
Beyond that the endpoint answers 402 and the tool returns the challenge; pay it
with guardpay (same repo) and pass X-PAYMENT.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from langchain_core.tools import tool

GUARD = "https://zealous-unburned-tameness.ngrok-free.dev"


@tool
def guard_batch(orders: list[dict]) -> str:
    """Decide a batch of spend/limit changes atomically before acting.

    Each order is {"root": "BUDGET.USD", "action": "INCREASE", "value_dec": 5}
    (or "value" in the limit's own scale). Roots: BUDGET.USD, API.RATE,
    DB.WRITE, TRANSFER.LIMIT, TOKEN.BURN, QUEUE.BATCH, RETRY.LOOP, SESSION.LOCK.
    Answers {"ok": true} when the whole batch fits, or {"ok": false, "codes": "M"}
    when one limit blocks it — and then nothing is applied.
    """
    datos = json.dumps({"orders": orders}).encode()
    req = urllib.request.Request(
        GUARD + "/", data=datos,
        headers={"Content-Type": "application/json", "User-Agent": "langchain-guard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.read().decode()


if __name__ == "__main__":
    print(guard_batch.invoke({"orders": [
        {"root": "BUDGET.USD", "action": "SET", "value_dec": 50},
        {"root": "BUDGET.USD", "action": "INCREASE", "value_dec": 12},
    ]}))
