/**
 * guardFetch — cumulative spend budget in front of x402-fetch v2.
 *
 * The protocol client (@x402/fetch) can pay a challenge but has no memory: it
 * has no idea how much it has spent today. This wrapper keeps the running total
 * for the UTC day and refuses before signing, so an agent loop cannot drain the
 * wallet. Free calls (HTTP 200 without payment) never touch the budget.
 *
 *   npm i @x402/fetch @x402/evm viem
 *
 *   import { privateKeyToAccount } from "viem/accounts";
 *   import { guardFetch } from "./x402_fetch_guard";
 *
 *   const account = privateKeyToAccount(process.env.EVM_KEY as `0x${string}`);
 *   const fetchPaid = guardFetch({ account, chain: "eip155:8453", budgetUsd: 5, maxPerCallUsd: 0.05 });
 *   const res = await fetchPaid("https://service.example/paid", { method: "POST", body });
 *
 * Tested against A2P-32 Guard on eip155:84532: three paid calls, then the budget
 * refusal, plus the per-call cap and the free tier.
 */
import { decodePaymentResponseHeader, wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme, type ClientEvmSigner } from "@x402/evm";

export class GuardError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GuardError";
  }
}

export interface GuardOptions {
  /** viem LocalAccount (address + signTypedData) or any ClientEvmSigner. */
  account: ClientEvmSigner;
  /** CAIP-2 network of the signer, e.g. "eip155:8453" or "eip155:84532". */
  chain: string;
  /** Cumulative budget for the UTC day, in USD (5 = 5 USDC). */
  budgetUsd: number;
  /** Per-call cap in USD; defaults to the whole budget. */
  maxPerCallUsd?: number;
}

const micro = (usd: number): bigint => BigInt(Math.round(usd * 1e6));
const usd = (units: bigint): string => (Number(units) / 1e6).toFixed(6);

export function guardFetch(opts: GuardOptions) {
  const budget = micro(opts.budgetUsd);
  const perCall = micro(opts.maxPerCallUsd ?? opts.budgetUsd);
  const client = new x402Client().register(opts.chain, new ExactEvmScheme(opts.account));
  const payFetch = wrapFetchWithPayment(globalThis.fetch, client);

  let spent = 0n;
  let day = new Date().toISOString().slice(0, 10);

  const roll = (): void => {
    const today = new Date().toISOString().slice(0, 10);
    if (today !== day) {
      day = today;
      spent = 0n;
    }
  };

  return async function guardedFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> {
    roll();

    // 1. Try without paying: the free tier answers 200 and costs nothing.
    const probe = await globalThis.fetch(input, init);
    if (probe.status !== 402) return probe;

    // 2. Read the price from the challenge.
    let price = 0n;
    try {
      const challenge = await probe.clone().json();
      const acc = (challenge?.accepts ?? [])[0] ?? {};
      price = BigInt(acc.amount ?? acc.maxAmountRequired ?? "0");
    } catch {
      return probe; // not a v2 x402 body: hand it back untouched
    }
    if (price === 0n) return probe;

    // 3. Refuse before signing.
    if (price > perCall) {
      throw new GuardError(`per-call cap: ${usd(price)} > ${usd(perCall)} USDC`);
    }
    if (spent + price > budget) {
      throw new GuardError(
        `daily budget: spent ${usd(spent)} + ${usd(price)} > ${usd(budget)} USDC`,
      );
    }

    // 4. Pay and retry.
    const res = await payFetch(input, init);
    if (res.ok) spent += price;
    return res;
  };
}

export { decodePaymentResponseHeader };
