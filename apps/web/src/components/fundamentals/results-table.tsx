"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { formatMarketCap } from "@/lib/format";
import type { FundamentalData } from "@/lib/api-types";

interface FundamentalsResultsTableProps {
  data: FundamentalData[];
  searchValue?: string;
}

export function FundamentalsResultsTable({
  data,
  searchValue,
}: FundamentalsResultsTableProps) {
  const router = useRouter();

  const columns = useMemo<ColumnDef<FundamentalData, unknown>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: "Symbol",
        cell: ({ row }) => (
          <div>
            <span className="font-mono font-semibold text-text-primary">
              {row.original.symbol}
            </span>
            <div className="text-label text-text-muted">{row.original.name}</div>
          </div>
        ),
      },
      {
        accessorKey: "sector",
        header: "Sector",
        cell: ({ row }) => (
          <span className="text-label text-text-secondary">{row.original.sector}</span>
        ),
      },
      {
        accessorKey: "market_cap",
        header: "Market Cap",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-primary">
            {formatMarketCap(row.original.market_cap)}
          </span>
        ),
      },
      {
        accessorKey: "pe_ratio",
        header: "P/E",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.pe_ratio?.toFixed(1) ?? "-"}
          </span>
        ),
      },
      {
        accessorKey: "pb_ratio",
        header: "P/B",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.pb_ratio?.toFixed(2) ?? "-"}
          </span>
        ),
      },
      {
        accessorKey: "roe",
        header: "ROE %",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.roe?.toFixed(1) ?? "-"}
          </span>
        ),
      },
      {
        accessorKey: "dividend_yield",
        header: "Div Yield",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.dividend_yield?.toFixed(2) ?? "-"}%
          </span>
        ),
      },
      {
        accessorKey: "debt_to_equity",
        header: "D/E",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.debt_to_equity?.toFixed(2) ?? "-"}
          </span>
        ),
      },
      {
        accessorKey: "eps",
        header: "EPS",
        meta: { numeric: true },
        cell: ({ row }) => (
          <span className="font-mono text-text-secondary">
            {row.original.eps?.toFixed(2) ?? "-"}
          </span>
        ),
      },
    ],
    []
  );

  return (
    <DataTable
      data={data}
      columns={columns}
      searchValue={searchValue}
      searchColumn="symbol"
      onRowClick={(row) => router.push(`/chart/${row.symbol}`)}
    />
  );
}
