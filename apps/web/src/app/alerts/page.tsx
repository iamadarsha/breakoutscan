"use client";

import { Bell, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonCard } from "@/components/ui/skeleton";
import { AlertForm } from "@/components/alerts/alert-form";
import { ActiveAlertsList } from "@/components/alerts/active-alerts-list";
import { HistoryTimeline } from "@/components/alerts/history-timeline";
import { useAlerts, useAlertHistory, useCreateAlert, useDeleteAlert } from "@/hooks/use-alerts";
import { toast } from "sonner";
import { useAuth } from "@/hooks/use-auth";

export default function AlertsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { data: alerts, isLoading } = useAlerts(!!user);
  const { data: history } = useAlertHistory(!!user);
  const createMutation = useCreateAlert();
  const deleteMutation = useDeleteAlert();

  // While the auth check is in flight, show a skeleton rather than
  // flashing the full (unauthenticated) page content or the sign-in gate
  // before we actually know which one is correct.
  if (authLoading) {
    return (
      <AppShell>
        <PageTransition>
          <div className="space-y-5">
            <SectionHeading
              title="Alerts"
              subtitle="Get notified when a stock confirms a breakout"
            />
            <div className="grid gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          </div>
        </PageTransition>
      </AppShell>
    );
  }

  // Auth gate
  if (!authLoading && !user) {
    return (
      <AppShell>
        <PageTransition>
          <div className="space-y-5">
            <SectionHeading
              title="Alerts"
              subtitle="Get notified when a stock confirms a breakout"
            />
            <div className="rounded-panel border border-border bg-card p-12 text-center">
              <Bell className="mx-auto h-12 w-12 text-text-muted/50" />
              <h3 className="mt-4 text-panel font-semibold text-text-primary">
                Sign in to use Alerts
              </h3>
              <p className="mx-auto mt-1.5 max-w-sm text-data text-text-secondary">
                Pick the stocks you care about and get notified the moment one confirms a breakout.
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
        <div className="space-y-5">
          <SectionHeading
            title="Alerts"
            subtitle="Get notified when a stock confirms a breakout"
          />

          <div className="grid gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
            {/* Alert Form */}
            <AlertForm
              onSubmit={(req) => {
                if ((alerts ?? []).some((a) => a.is_active && a.symbol === req.symbol)) {
                  toast.info(`You already have an alert for ${req.symbol}`);
                  return;
                }
                createMutation.mutate(req);
              }}
              isLoading={createMutation.isPending}
            />

            {/* Active Alerts + History */}
            <div className="space-y-5">
              {isLoading ? (
                <>
                  <SkeletonCard />
                  <SkeletonCard />
                </>
              ) : (
                <>
                  <ActiveAlertsList
                    alerts={alerts ?? []}
                    onDelete={(id) => deleteMutation.mutate(id)}
                    deletingId={deleteMutation.isPending ? deleteMutation.variables : null}
                  />
                  <HistoryTimeline history={history ?? []} />
                </>
              )}
            </div>
          </div>
        </div>
      </PageTransition>
    </AppShell>
  );
}
