"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { formatPrice, formatPercent, formatVolume } from "@/lib/format";
import { sectorFor } from "@/lib/nse-stocks";
import type { ScanResultItem } from "@/lib/api-types";

interface SortableResultsTableProps {
  items: ScanResultItem[];
}

export function SortableResultsTable({ items }: SortableResultsTableProps) {
  const router = useRouter();

  const hasSignal = items.some((i) => i.signal_strength);

  const columns = useMemo<ColumnDef<ScanResultItem, unknown>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: "Symbol",
        cell: ({ row }) => (
          <div>
            <span className="font-mono font-semibold text-text-primary">
              {row.original.symbol}
            </span>
            {row.original.company_name && row.original.company_name !== row.original.symbol && (
              <div className="text-label text-text-muted">{row.original.company_name}</div>
            )}
          </div>
        ),
      },
      {
        id: "sector",
        header: "Sector",
        accessorFn: (row) => row.sector || sectorFor(row.symbol),
        cell: ({ getValue }) => (
          <span className="text-label text-text-secondary">{(getValue() as string) || "—"}</span>
        ),
      },
      {
        accessorKey: "ltp",
        header: "LTP",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-primary">
            {formatPrice(row.original.ltp ?? 0)}
          </span>
        ),
      },
      {
        accessorKey: "change_pct",
        header: "Change %",
        meta: { numeric: true },
        cell: ({ row }) => (
          <Badge
            variant={
              (row.original.change_pct ?? 0) >= 0 ? "bullish" : "bearish"
            }
          >
            {formatPercent(row.original.change_pct ?? 0)}
          </Badge>
        ),
      },
      {
        accessorKey: "volume",
        header: "Volume",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {formatVolume(row.original.volume ?? 0)}
          </span>
        ),
      },
      ...(hasSignal ? [{
        accessorKey: "signal_strength",
        header: "Signal",
        cell: ({ row }) => {
          const strength = row.original.signal_strength;
          if (!strength) return <span className="text-text-muted">-</span>;
          return (
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-16 overflow-hidden rounded-full bg-border">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.min(strength * 100, 100)}%` }}
                />
              </div>
              <span className="font-mono text-label text-text-secondary">
                {(strength * 100).toFixed(0)}%
              </span>
            </div>
          );
        },
      } as ColumnDef<ScanResultItem, unknown>] : []),
    ],
    [hasSignal]
  );

  return (
    <DataTable
      data={items}
      columns={columns}
      onRowClick={(row) => router.push(`/chart/${row.symbol}`)}
    />
  );
}
