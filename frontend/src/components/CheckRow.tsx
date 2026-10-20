export function CheckRow({
  name,
  ok,
  result,
  source,
}: {
  name: string;
  ok: boolean;
  result: string;
  source?: string;
}) {
  return (
    <div className="grid grid-cols-[14px_1fr] gap-3 border-b border-line/70 py-2.5 text-[13px]">
      <span className={`mt-1 h-2 w-2 ${ok ? "bg-mint" : "bg-warn"}`} />
      <div>
        <div className="flex justify-between gap-4">
          <span>{name}</span>
          <span className="text-mute">{ok ? "ok" : "obs"}</span>
        </div>
        <p className="text-[12px] text-mute">{result}</p>
        {source && <p className="text-[11px] text-mute/80">{source}</p>}
      </div>
    </div>
  );
}
