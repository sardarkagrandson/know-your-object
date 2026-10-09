import { useState, type FormEvent } from "react";

const EXAMPLES = ["NGC 1365", "M 87", "NGC 4038", "3C 273", "03h33m36.4s -36d08m25s", "187.706, 12.391"];

interface Props {
  busy: boolean;
  onSearch: (query: string) => void;
}

export default function TargetSearch({ busy, onSearch }: Props) {
  const [value, setValue] = useState("NGC 1365");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (q) onSearch(q);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-2">
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Object name or J2000 coordinates (e.g. NGC 1365, 53.40 -36.14)"
          className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none"
          autoFocus
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:cursor-wait disabled:opacity-60"
        >
          {busy ? "Resolving…" : "Resolve"}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-1 text-xs text-slate-400">
        <span>Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => {
              setValue(ex);
              onSearch(ex);
            }}
            className="rounded bg-slate-800 px-2 py-0.5 font-mono text-slate-300 hover:bg-slate-700"
          >
            {ex}
          </button>
        ))}
      </div>
    </form>
  );
}
