"use client";

import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/cn";

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData, TValue> {
    /** Right-align figures so decimals line up down the column. */
    numeric?: boolean;
  }
}

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  searchValue?: string;
  searchColumn?: string;
  className?: string;
  onRowClick?: (row: T) => void;
}

export function DataTable<T>({
  data,
  columns,
  searchValue,
  searchColumn,
  className,
  onRowClick,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter: searchColumn ? undefined : searchValue,
      columnFilters: searchColumn && searchValue
        ? [{ id: searchColumn, value: searchValue }]
        : [],
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className={cn("overflow-x-auto scroll-touch", className)}>
      <table className="w-full text-data">
        <thead className="bg-elevated">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border">
              {hg.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sorted = header.column.getIsSorted();
                const numeric = header.column.columnDef.meta?.numeric;
                return (
                  <th
                    key={header.id}
                    aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                    className={cn(
                      "whitespace-nowrap px-3 py-2 text-label font-semibold uppercase text-text-muted sm:px-4",
                      numeric ? "text-right" : "text-left",
                      canSort && "cursor-pointer select-none hover:text-text-primary",
                      sorted && "text-text-primary"
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className={cn("inline-flex items-center gap-1", numeric && "flex-row-reverse")}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                      {canSort && (
                        <span className={sorted ? "text-accent" : "text-text-muted/60"}>
                          {sorted === "asc" ? (
                            <ArrowUp className="h-3 w-3" />
                          ) : sorted === "desc" ? (
                            <ArrowDown className="h-3 w-3" />
                          ) : (
                            <ArrowUpDown className="h-3 w-3" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row.original)}
              className={cn(
                "border-b border-border-subtle transition-colors last:border-0",
                onRowClick && "cursor-pointer hover:bg-accent/[0.04]"
              )}
            >
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  className={cn(
                    "whitespace-nowrap px-3 py-2 text-text-primary sm:px-4",
                    cell.column.columnDef.meta?.numeric && "text-right font-mono tabular-nums"
                  )}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {table.getRowModel().rows.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-12 text-center text-text-muted"
              >
                No results found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
