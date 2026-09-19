"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchActiveBreakouts } from "@/lib/api";

export function useActiveBreakouts() {
  return useQuery({
    queryKey: ["activeBreakouts"],
    queryFn: fetchActiveBreakouts,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 1,
  });
}
