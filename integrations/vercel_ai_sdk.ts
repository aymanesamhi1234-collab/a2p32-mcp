/**
 * Vercel AI SDK tool: ask A2P-32 Guard before an agent spends or writes.
 *
 *   npm i ai zod
 *   import { guardBatch } from "./integrations/vercel_ai_sdk";
 *   const result = await generateText({ model, tools: { guardBatch }, prompt });
 *
 * The first 5 actions of a call are free, so the tool works with no wallet.
 */
import { tool } from "ai";
import { z } from "zod";

const GUARD = "https://zealous-unburned-tameness.ngrok-free.dev";

export const guardBatch = tool({
  description:
    "Decide a batch of spend/limit changes atomically before acting. " +
    "Roots: BUDGET.USD, API.RATE, DB.WRITE, TRANSFER.LIMIT, TOKEN.BURN, " +
    "QUEUE.BATCH, RETRY.LOOP, SESSION.LOCK; actions READ, SET, INCREASE, " +
    "DECREASE, OPEN, CLOSE, STOP.",
  parameters: z.object({
    orders: z.array(
      z.object({
        root: z.string(),
        action: z.string().optional(),
        value: z.number().optional(),
        value_dec: z.number().optional(),
        lock: z.boolean().optional(),
      }),
    ),
  }),
  execute: async ({ orders }) => {
    const res = await fetch(`${GUARD}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orders }),
    });
    return await res.text();
  },
});
