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
import { useAlerts, useCreateAlert } from "@/hooks/use-alerts";
import { useAuth } from "@/hooks/use-auth";

export default function AlertsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { data: alerts, isLoading } = useAlerts();
  const createMutation = useCreateAlert();

  // While the auth check is in flight, show a skeleton rather than
  // flashing the full (unauthenticated) page content or the sign-in gate
  // before we actually know which one is correct.
  if (authLoading) {
    return (
      <AppShell>
        <PageTransition>
          <div className="space-y-6">
            <SectionHeading
              title="Alerts"
              subtitle="Set price and indicator alerts for your stocks"
            />
            <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
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
          <div className="space-y-6">
            <SectionHeading
              title="Alerts"
              subtitle="Set price and indicator alerts for your stocks"
            />
            <div className="rounded-panel border border-border bg-card p-12 text-center">
              <Bell className="mx-auto h-12 w-12 text-text-muted/50" />
              <h3 className="mt-4 text-lg font-semibold text-text-primary">
                Sign in to use Alerts
              </h3>
              <p className="mt-2 text-sm text-text-secondary max-w-sm mx-auto">
                Create custom price and indicator alerts to get notified when your stocks hit key levels.
              </p>
              <button
                onClick={() => router.push("/login")}
                className="mt-6 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-6 py-3 text-sm font-semibold text-accent transition hover:bg-accent/20"
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
        <div className="space-y-6">
          <SectionHeading
            title="Alerts"
            subtitle="Set price and indicator alerts for your stocks"
          />

          <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
            {/* Alert Form */}
            <AlertForm
              onSubmit={(req) => createMutation.mutate(req)}
              isLoading={createMutation.isPending}
            />

            {/* Active Alerts + History */}
            <div className="space-y-6">
              {isLoading ? (
                <>
                  <SkeletonCard />
                  <SkeletonCard />
                </>
              ) : (
                <>
                  <ActiveAlertsList alerts={alerts ?? []} />
                  <HistoryTimeline alerts={alerts ?? []} />
                </>
              )}
            </div>
          </div>
        </div>
      </PageTransition>
    </AppShell>
  );
}
