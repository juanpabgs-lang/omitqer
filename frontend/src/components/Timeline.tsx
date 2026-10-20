export function Timeline({
  items,
}: {
  items: { kind: string; created_at: string; payload?: string }[];
}) {
  return (
    <ol className="space-y-3">
      {items.map((e, i) => (
        <li key={i} className="grid grid-cols-[12px_1fr] gap-3 text-[13px]">
          <span className="mt-1.5 h-2 w-2 rounded-full border border-ink" />
          <div>
            <div className="font-medium">{e.kind}</div>
            <div className="text-[12px] text-mute">{e.created_at}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
