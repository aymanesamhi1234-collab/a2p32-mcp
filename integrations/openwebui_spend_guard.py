"""
Open WebUI tool: spend guard before the model acts.

Paste this file into Open WebUI -> Workspace -> Tools -> "+" (or import it from
the raw URL of this file in the repo). The tool shows up as `guard_batch` and
the model is told when to call it.

No wallet needed for the free tier: batches of up to five actions are free, so a
chat can use it without any payment configuration.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        guard_url: str = Field(
            default="https://zealous-unburned-tameness.ngrok-free.dev",
            description="Base URL of the guard service",
        )
        tenant: int = Field(default=0, description="Tenant slot (0-63)")
        timeout_s: int = Field(default=30, description="HTTP timeout in seconds")

    def __init__(self) -> None:
        self.valves = self.Valves()

    async def guard_batch(
        self,
        orders: list[dict[str, Any]],
        __event_emitter__: Optional[Any] = None,
    ) -> str:
        """
        Decide whether a batch of spend and limit changes is allowed BEFORE acting.

        Send one batch; the answer is atomic (all applied or none):
          {"ok": true,  "codes": "0"}   the whole batch fits
          {"ok": false, "codes": "M"}   a limit blocks it, nothing was applied

        Each order: {"root": "BUDGET.USD", "action": "INCREASE", "value_dec": 5}
        Roots: BUDGET.USD, API.RATE, DB.WRITE, TRANSFER.LIMIT, TOKEN.BURN,
        QUEUE.BATCH, RETRY.LOOP, SESSION.LOCK.
        Actions: READ, SET, INCREASE, DECREASE, OPEN, CLOSE, STOP.

        :param orders: list of limit operations to validate and apply atomically
        :return: the guard decision as JSON text
        """
        if __event_emitter__:
            await __event_emitter__(
                {"type": "status", "data": {"description": "Checking spend limits…", "done": False}}
            )
        try:
            response = requests.post(
                f"{self.valves.guard_url.rstrip('/')}/v1/guard",
                json={"orders": orders, "tenant": self.valves.tenant},
                timeout=self.valves.timeout_s,
            )
            if response.status_code == 402:
                texto = (
                    "Payment required for this batch (over the free tier). "
                    f"Challenge: {response.text[:600]}"
                )
            elif response.status_code >= 400:
                texto = f"Spend guard error {response.status_code}: {response.text[:300]}"
            else:
                texto = json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001 - the model needs the reason, not a traceback
            texto = f"Error calling the spend guard: {type(exc).__name__}: {exc}"
        finally:
            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": "Spend check done", "done": True}}
                )
        return texto
