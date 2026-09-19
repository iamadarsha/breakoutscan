"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchCompanyInfo } from "@/lib/api";
import { Globe, Building2 } from "lucide-react";

interface CompanyInfoPanelProps {
  symbol: string;
}

export function CompanyInfoPanel({ symbol }: CompanyInfoPanelProps) {
  const { data: info, isLoading } = useQuery({
    queryKey: ["companyInfo", symbol],
    queryFn: () => fetchCompanyInfo(symbol),
    retry: 0,
    staleTime: 60_000 * 10,
  });

  if (isLoading) {
    return (
      <div className="rounded-panel border border-border bg-card p-4 animate-pulse">
        <div className="h-4 w-32 rounded bg-elevated" />
        <div className="mt-3 h-3 w-full rounded bg-elevated" />
        <div className="mt-2 h-3 w-3/4 rounded bg-elevated" />
      </div>
    );
  }

  if (!info) return null;

  return (
    <div className="rounded-panel border border-border bg-card p-4 sm:p-5">
      <h3 className="mb-2 text-data font-semibold text-text-primary flex items-center gap-2">
        <Building2 className="h-4 w-4 text-text-muted" />
        {info.name ?? symbol}
      </h3>

      {info.description && (
        <p className="text-label leading-relaxed text-text-secondary mb-3">
          {info.description}
        </p>
      )}

      <div className="flex flex-wrap gap-4 text-label text-text-muted">
        {info.sector && (
          <span>
            Sector: <span className="text-text-secondary">{info.sector}</span>
          </span>
        )}
        {info.industry && (
          <span>
            Industry: <span className="text-text-secondary">{info.industry}</span>
          </span>
        )}
        {info.website && (
          <a
            href={info.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-accent hover:underline"
          >
            <Globe className="h-3 w-3" />
            Website
          </a>
        )}
      </div>
    </div>
  );
}
