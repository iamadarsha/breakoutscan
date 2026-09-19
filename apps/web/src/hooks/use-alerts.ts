"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchAlerts, createAlert, deleteAlert, fetchAlertHistory } from "@/lib/api";
import type { AlertCreateRequest } from "@/lib/api-types";
import { toast } from "sonner";

export function useAlerts(enabled = true) {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: () => fetchAlerts(),
    enabled,
    retry: 0,
  });
}

export function useAlertHistory(enabled = true) {
  return useQuery({
    queryKey: ["alert-history"],
    queryFn: () => fetchAlertHistory(),
    enabled,
    retry: 0,
  });
}

export function useCreateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: AlertCreateRequest) => createAlert(req),
    onSuccess: (alert) => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast.success(`Alert set for ${alert.symbol}`);
    },
    onError: (error: Error) => {
      toast.error(error.message.includes("401") ? "Please sign in to create alerts" : "Failed to create alert");
    },
  });
}

export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAlert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast.success("Alert removed");
    },
    onError: () => {
      toast.error("Couldn't remove the alert");
    },
  });
}
