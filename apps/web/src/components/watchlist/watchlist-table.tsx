"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { PriceCell } from "@/components/ui/price-cell";
import { Badge } from "@/components/ui/badge";
import { formatPercent, formatVolume } from "@/lib/format";
import type { WatchlistItem, LivePrice } from "@/lib/api-types";

interface WatchlistRow extends WatchlistItem {
  livePrice?: LivePrice;
}

interface WatchlistTableProps {
  items: WatchlistRow[];
  onRemove: (symbol: string) => void;
}

export function WatchlistTable({ items, onRemove }: WatchlistTableProps) {
  const router = useRouter();

  const columns = useMemo<ColumnDef<WatchlistRow, unknown>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: "Symbol",
        cell: ({ row }) => (
          <div>
            <span className="font-mono font-semibold text-text-primary">
              {row.original.symbol}
            </span>
            <div className="text-xs text-text-muted">{row.original.name}</div>
          </div>
        ),
      },
      {
        accessorKey: "ltp",
        header: "LTP",
        accessorFn: (row) => row.livePrice?.ltp ?? 0,
        cell: ({ row }) => {
          const lp = row.original.livePrice;
          if (!lp) return <span className="text-text-muted">--</span>;
          return <PriceCell price={lp.ltp} />;
        },
      },
      {
        accessorKey: "change_pct",
        header: "Change",
        accessorFn: (row) => row.livePrice?.change_pct ?? 0,
        cell: ({ row }) => {
          const pct = row.original.livePrice?.change_pct ?? 0;
          return (
            <Badge variant={pct >= 0 ? "bullish" : "bearish"}>
              {formatPercent(pct)}
            </Badge>
          );
        },
      },
      {
        accessorKey: "volume",
        header: "Volume",
        accessorFn: (row) => row.livePrice?.volume ?? 0,
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.livePrice
              ? formatVolume(row.original.livePrice.volume)
              : "--"}
          </span>
        ),
      },
      {
        accessorKey: "high",
        header: "High",
        accessorFn: (row) => row.livePrice?.high ?? 0,
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.livePrice?.high.toFixed(2) ?? "--"}
          </span>
        ),
      },
      {
        accessorKey: "low",
        header: "Low",
        accessorFn: (row) => row.livePrice?.low ?? 0,
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.livePrice?.low.toFixed(2) ?? "--"}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove(row.original.symbol);
            }}
            className="rounded-full p-1.5 text-text-muted transition hover:bg-elevated hover:text-bearish"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        ),
      },
    ],
    [onRemove]
  );

  return (
    <DataTable
      data={items}
      columns={columns}
      onRowClick={(row) => router.push(`/chart/${row.symbol}`)}
    />
  );
}
