"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonTable } from "@/components/ui/skeleton";
import { FilterSidebar } from "@/components/fundamentals/filter-sidebar";
import { FundamentalsResultsTable } from "@/components/fundamentals/results-table";
import { fetchFundamentals } from "@/lib/api";
import type { FundamentalFilters } from "@/lib/api-types";
import { Badge } from "@/components/ui/badge";

const defaultFilters: FundamentalFilters = {};

export default function FundamentalsPage() {
  const [filters, setFilters] = useState<FundamentalFilters>(defaultFilters);
  const [appliedFilters, setAppliedFilters] =
    useState<FundamentalFilters>(defaultFilters);
  const [search, setSearch] = useState("");
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const { data: rawData, isLoading, isError } = useQuery({
    queryKey: ["fundamentals", appliedFilters],
    queryFn: () => fetchFundamentals(appliedFilters),
    retry: 1,
  });

  const data = rawData ?? [];

  return (
    <AppShell>
      <PageTransition>
        <div className="space-y-5">
          <SectionHeading
            title="Fundamentals"
            subtitle="Screen stocks by fundamental metrics"
            action={
              data && (
                <Badge variant="accent">
                  {data.length} results
                </Badge>
              )
            }
          />

          <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
            {/* Filter Sidebar */}
            <FilterSidebar
              filters={filters}
              onChange={(next) => {
                setFilters(next);
                setActivePreset(null);
              }}
              onApply={() => setAppliedFilters({ ...filters })}
              onReset={() => {
                setFilters(defaultFilters);
                setAppliedFilters(defaultFilters);
                setActivePreset(null);
              }}
              onApplyPreset={(name, presetFilters) => {
                setFilters(presetFilters);
                setAppliedFilters(presetFilters);
                setActivePreset(name);
              }}
              activePreset={activePreset}
            />

            {/* Results */}
            <div className="min-w-0 space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter results by symbol..."
                  className="h-10 w-full max-w-sm rounded-lg border border-border bg-page pl-10 pr-3 text-data text-text-primary placeholder-text-muted outline-none focus:border-accent"
                />
              </div>

              {isLoading ? (
                <SkeletonTable rows={8} />
              ) : (
                <div className="rounded-panel border border-border bg-card">
                  <FundamentalsResultsTable
                    data={data ?? []}
                    searchValue={search}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </PageTransition>
    </AppShell>
  );
}
