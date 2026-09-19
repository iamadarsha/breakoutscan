"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Plus, LogIn, Eye } from "lucide-react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { Button } from "@/components/ui/button";
import { SkeletonTable } from "@/components/ui/skeleton";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { WatchlistSummary } from "@/components/watchlist/watchlist-summary";
import { AddStockModal } from "@/components/watchlist/add-stock-modal";
import {
  useWatchlist,
  useAddToWatchlist,
  useRemoveFromWatchlist,
} from "@/hooks/use-watchlist";
import { useAuth } from "@/hooks/use-auth";
import { useQuery } from "@tanstack/react-query";
import { useLivePrices } from "@/hooks/use-live-prices";
import { fetchLivePrices } from "@/lib/api";
import type { LivePrice } from "@/lib/api-types";

export default function WatchlistPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const { data: items, isLoading, isError } = useWatchlist();
  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  const symbols = useMemo(
    () => (items ?? []).map((i) => i.symbol),
    [items]
  );

  const wsPrices = useLivePrices(symbols);
  const hasWsPrices = Object.keys(wsPrices).length > 0;

  // REST fallback for when WebSocket doesn't deliver (e.g. market closed)
  const { data: restPriceList } = useQuery({
    queryKey: ["batchPrices", symbols.join(",")],
    queryFn: () => fetchLivePrices(symbols),
    enabled: symbols.length > 0 && !hasWsPrices,
    retry: 0,
    staleTime: 30_000,
  });
  const restPrices = useMemo(() => {
    const map: Record<string, LivePrice> = {};
    for (const p of restPriceList ?? []) map[p.symbol] = p;
    return map;
  }, [restPriceList]);

  const livePrices = hasWsPrices ? wsPrices : restPrices;

  const enrichedItems = useMemo(
    () =>
      (items ?? []).map((item) => ({
        ...item,
        livePrice: livePrices[item.symbol],
      })),
    [items, livePrices]
  );

  // While the auth check is in flight, show a skeleton rather than
  // flashing the full (unauthenticated) page content or the sign-in gate
  // before we actually know which one is correct.
  if (authLoading) {
    return (
      <AppShell>
        <PageTransition>
          <div className="space-y-5">
            <SectionHeading
              title="Watchlist"
              subtitle="Track your favourite stocks with live prices"
            />
            <SkeletonTable rows={5} />
          </div>
        </PageTransition>
      </AppShell>
    );
  }

  // Auth gate — show sign-in prompt if not logged in
  if (!authLoading && !user) {
    return (
      <AppShell>
        <PageTransition>
          <div className="space-y-5">
            <SectionHeading
              title="Watchlist"
              subtitle="Track your favourite stocks with live prices"
            />
            <div className="rounded-panel border border-border bg-card p-12 text-center">
              <Eye className="mx-auto h-12 w-12 text-text-muted/50" />
              <h3 className="mt-4 text-lg font-semibold text-text-primary">
                Sign in to use Watchlist
              </h3>
              <p className="mt-2 text-data text-text-secondary max-w-sm mx-auto">
                Create a personal watchlist to track your favourite stocks with live prices, alerts, and more.
              </p>
              <button
                onClick={() => router.push("/login")}
                className="mt-6 inline-flex h-9 items-center gap-2 rounded-lg bg-accent-solid px-4 text-data font-semibold text-white transition-colors hover:bg-accent-solid-hover"
              >
                <LogIn className="h-4 w-4" />
                Sign In with Google
              </button>
            </div>
          </div>
        </PageTransition>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageTransition>
        <motion.div
          className="space-y-5"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.08 } },
          }}
        >
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            <SectionHeading
              title="Watchlist"
              subtitle="Track your favourite stocks with live prices"
              action={
                <Button
                  onClick={() => setModalOpen(true)}
                  className="flex items-center gap-2"
                >
                  <Plus className="h-4 w-4" />
                  Add Stock
                </Button>
              }
            />
          </motion.div>

          <motion.div
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            <WatchlistSummary prices={livePrices} count={items?.length ?? 0} />
          </motion.div>

          <motion.div
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            {isLoading ? (
              <SkeletonTable rows={5} />
            ) : isError ? (
              <div className="rounded-panel border border-border bg-card p-8 text-center">
                <p className="text-data text-text-muted">Couldn’t load your watchlist. Check your connection and reload.</p>
                
              </div>
            ) : enrichedItems.length === 0 ? (
              <div className="rounded-panel border border-dashed border-border bg-card px-6 py-12 text-center">
                <Eye className="mx-auto h-8 w-8 text-text-muted" />
                <h3 className="mt-3 text-panel font-semibold text-text-primary">Your watchlist is empty</h3>
                <p className="mx-auto mt-1 max-w-sm text-data text-text-secondary">
                  Add the stocks you follow to see live prices, day range and volume in one place.
                </p>
                <Button onClick={() => setModalOpen(true)} className="mt-4">
                  <Plus className="h-4 w-4" /> Add your first stock
                </Button>
              </div>
            ) : (
              <div className="rounded-panel border border-border bg-card shadow-card">
                <WatchlistTable
                  items={enrichedItems}
                  onRemove={(symbol) => removeMutation.mutate(symbol)}
                />
              </div>
            )}
          </motion.div>

          <AddStockModal
            open={modalOpen}
            onClose={() => setModalOpen(false)}
            onAdd={(symbol) => addMutation.mutate(symbol)}
            existingSymbols={symbols}
          />
        </motion.div>
      </PageTransition>
    </AppShell>
  );
}
