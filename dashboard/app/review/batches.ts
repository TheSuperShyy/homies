// The answers page's dropdown (owner, 22 Nov: "also on the answer", after the one on Yariv's comments): a set
// may group its chats in batches, for example the newest answers and the 10 Nov ones. A set with no batches
// shows no dropdown and every chat, as before.

export type Batch = { id: string; label: string };
type Batched = { batch?: string };

// The `show` query parameter as the page gets it: one of the set's batches, or all.
export function toBatchView(v: unknown, batches: Batch[]): string {
  return typeof v === 'string' && batches.some((b) => b.id === v) ? v : 'all';
}

export function chatsFor<T extends Batched>(view: string, chats: T[]): T[] {
  return view === 'all' ? chats : chats.filter((c) => c.batch === view);
}
