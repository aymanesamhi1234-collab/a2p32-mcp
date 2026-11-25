#!/usr/bin/env python3
"""guardpay — x402 payment client with a spend guard in front.

    gp = GuardPay(budget_usd=25, key=os.environ["EVM_KEY"])
    r = gp.pay("https://service.example/api", body={"q": "..."}, max_usd=0.05)

Order of operations, always:

    1. call the target URL
    2. if 402, read the price from accepts[0]
    3. refuse locally if the price exceeds max_usd
    4. ask the guard (free) whether the amount fits the remaining budget
    5. only then sign EIP-3009 and retry with X-PAYMENT

Requires: pip install eth-account
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

GUARD = os.environ.get("A2P_GUARD", "https://zealous-unburned-tameness.ngrok-free.dev")

# USDC por cadena. No se acepta otro asset.
USDC = {8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        84532: "0x036CbD53842c5426634e7929541eC2318f3dCF7e"}
RPC = {8453: "https://mainnet.base.org", 84532: "https://sepolia.base.org"}


class Denied(Exception):
    """El guard o el tope local han rechazado el pago."""


def _code(payer: str, chain: int) -> str:
    """Codigo en la cuenta del pagador. '' si no se puede consultar.

    Un EOA normal devuelve '0x'. Si devuelve algo, la cuenta tiene una
    delegacion EIP-7702 (o es un contrato) y USDC validara la firma por
    ERC-1271: una firma EIP-3009 de clave EOA sera rechazada.
    """
    url = RPC.get(chain)
    if not url:
        return ""
    req = urllib.request.Request(
        url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getCode",
                              "params": [payer, "latest"]}).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "guardpay/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read()).get("result", "")
    except Exception:
        return ""


def _http(url: str, body: Any = None, headers: Optional[Dict[str, str]] = None,
          timeout: int = 90):
    datos = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=datos, method="POST" if datos is not None else "GET",
        headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


class GuardPay:
    def __init__(self, budget_usd: float = 10.0, spent_usd: float = 0.0,
                 key: Optional[str] = None, guard: str = GUARD):
        self.budget = float(budget_usd)
        self.spent = float(spent_usd)
        self.key = key
        self.guard = guard.rstrip("/")

    def preflight(self, amount_usd: float) -> Dict[str, Any]:
        """Pregunta gratis al guard si el importe cabe. Lanza Denied si no."""
        url = (f"{self.guard}/v1/check?budget={self.budget}"
               f"&spent={self.spent}&amount={amount_usd}")
        code, _, raw = _http(url)
        try:
            d = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            raise Denied(f"guard no responde ({code})")
        if code != 200:
            raise Denied(f"guard HTTP {code}")
        if not d.get("allow"):
            raise Denied(f"guard: {d.get('reason')} · quedan {d.get('remaining_before')}")
        return d

    def pay(self, url: str, body: Any = None, max_usd: Optional[float] = None,
            headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        code, hdrs, raw = _http(url, body, headers)
        if code != 402:
            return {"status": code, "body": raw, "paid": False}

        reto = json.loads(raw or b"{}")
        acc = (reto.get("accepts") or [{}])[0]
        amount = int(acc.get("maxAmountRequired") or acc.get("amount") or 0)
        usd = amount / 1e6
        if amount <= 0:
            raise Denied("el 402 no trae importe")
        if max_usd is not None and usd > float(max_usd):
            raise Denied(f"precio {usd} > max_usd {max_usd}")

        self.preflight(usd)

        red = str(acc.get("network", "")).split(":")[-1]
        chain = int(red) if red.isdigit() else 8453
        asset = str(acc.get("asset", "0x0"))
        if asset.lower() != USDC.get(chain, "0x0").lower():
            raise Denied("el asset no es USDC de esa cadena")
        if not self.key:
            raise Denied("falta la clave para firmar")

        auth = self._firma(acc, chain, amount)
        recibo = base64.b64encode(json.dumps(auth).encode()).decode()
        code2, h2, raw2 = _http(url, body, {**(headers or {}), "X-PAYMENT": recibo})
        if code2 == 200:
            self.spent += usd
        return {"status": code2, "body": raw2, "paid": code2 == 200,
                "amount_usd": usd, "payment_response": h2.get("X-PAYMENT-RESPONSE")}

    def _firma(self, acc: Dict[str, Any], chain: int, amount: int) -> Dict[str, Any]:
        from eth_account import Account
        payer = Account.from_key(self.key).address
        codigo = _code(payer, chain)
        if codigo not in ("", "0x"):
            raise Denied(
                f"{payer} tiene codigo en la cuenta (delegacion EIP-7702 o "
                "contrato): USDC validara la firma por ERC-1271 y rechazara "
                "una firma EOA. Usa una cuenta EOA limpia para pagar.")
        ahora = int(time.time())
        extra = acc.get("extra") or {}
        nonce = "0x" + os.urandom(32).hex()
        typed = {
            "types": {
                "EIP712Domain": [{"name": "name", "type": "string"},
                                 {"name": "version", "type": "string"},
                                 {"name": "chainId", "type": "uint256"},
                                 {"name": "verifyingContract", "type": "address"}],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"}],
            },
            "primaryType": "TransferWithAuthorization",
            "domain": {"name": extra.get("name", "USD Coin"),
                       "version": extra.get("version", "2"),
                       "chainId": chain,
                       "verifyingContract": acc["asset"]},
            "message": {"from": payer, "to": acc["payTo"], "value": amount,
                        "validAfter": 0, "validBefore": ahora + 300, "nonce": nonce},
        }
        sig = Account.sign_typed_data(self.key, full_message=typed).signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig
        # formato estandar x402 v2 (lo que espera el facilitador)
        return {"x402Version": 2, "scheme": acc.get("scheme", "exact"),
                "network": acc.get("network", f"eip155:{chain}"),
                "payload": {"signature": sig,
                            "authorization": {"from": payer, "to": acc["payTo"],
                                              "value": str(amount), "validAfter": "0",
                                              "validBefore": str(ahora + 300),
                                              "nonce": nonce}}}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="x402 payment with a spend guard")
    ap.add_argument("url")
    ap.add_argument("--budget", type=float, default=10.0)
    ap.add_argument("--max-usd", type=float, default=None)
    ap.add_argument("--key-file", default=os.environ.get("EVM_KEY_FILE", ""))
    ap.add_argument("--orders", type=int, default=6)
    a = ap.parse_args()
    key = open(a.key_file).read().strip() if a.key_file else os.environ.get("EVM_KEY")
    gp = GuardPay(budget_usd=a.budget, key=key)
    orders = [{"root": "BUDGET.USD", "action": "READ"} for _ in range(a.orders)]
    out = gp.pay(a.url, body={"jsonrpc": "2.0", "id": 1, "method": "SendMessage",
                              "params": {"message": {"parts": [{"data": {"orders": orders}}]}}},
                 max_usd=a.max_usd)
    print(json.dumps({k: (v.decode()[:200] if isinstance(v, bytes) else v)
                      for k, v in out.items()}, ensure_ascii=False, indent=2))
