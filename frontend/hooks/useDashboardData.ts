"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  ActivityEvent,
  DashboardAlert,
  DashboardKpis,
  MyDayItem,
} from "@/lib/types";

/**
 * Dashboard endpoints (admin cockpit · FASE 2 H4 wire-up real):
 *   GET /api/v1/dashboard/kpis
 *   GET /api/v1/dashboard/my-day
 *   GET /api/v1/dashboard/alerts
 *   GET /api/v1/dashboard/activity
 *
 * Backend service: backend/app/services/admin_dashboard_service.py
 * Cross-motor aggregator (M13 leads · M15 invoices · M23 retainers · etc.).
 */

export function useDashboardKpis() {
  return useQuery({
    queryKey: ["dashboard", "kpis"],
    queryFn: () => api<DashboardKpis>("/api/v1/dashboard/kpis"),
  });
}

export function useMyDay() {
  return useQuery({
    queryKey: ["dashboard", "my-day"],
    queryFn: () => api<MyDayItem[]>("/api/v1/dashboard/my-day"),
  });
}

export function useAlerts() {
  return useQuery({
    queryKey: ["dashboard", "alerts"],
    queryFn: () => api<DashboardAlert[]>("/api/v1/dashboard/alerts"),
  });
}

export function useActivity() {
  return useQuery({
    queryKey: ["dashboard", "activity"],
    queryFn: () => api<ActivityEvent[]>("/api/v1/dashboard/activity"),
  });
}
