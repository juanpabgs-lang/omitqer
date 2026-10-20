import { ars, compact } from "../lib/format";

export function Money({ n, compact: c = false, className = "" }: { n: number; compact?: boolean; className?: string }) {
  return <span className={`num ${className}`}>{c ? compact(n) : ars(n)}</span>;
}
