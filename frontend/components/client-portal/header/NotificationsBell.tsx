"use client";

/**
 * NotificationsBell · MB-7 atom 7.4 plan v6.
 *
 * Bell icon header · badge unread · dropdown last 10 · mark-read on click.
 * Polls every 30s (no SSE wire yet · stays within existing inbox endpoints).
 */
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Bell, Check, CheckCheck, Loader2 } from "lucide-react";

import {
  type PortalNotification,
  fetchInbox,
  fetchUnreadCount,
  markAllRead,
  markRead,
} from "@/lib/api/notifications";


const POLL_INTERVAL_MS = 30_000;


function formatRelative(iso: string): string {
  try {
    const then = new Date(iso).getTime();
    const now = Date.now();
    const minutes = Math.floor((now - then) / 60_000);
    if (minutes < 1) return "ahora";
    if (minutes < 60) return `hace ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `hace ${hours} h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `hace ${days} d`;
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
    });
  } catch {
    return iso;
  }
}


export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<PortalNotification[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Poll unread count every 30s + on mount
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const n = await fetchUnreadCount();
        if (!cancelled) setUnread(n);
      } catch {
        // ignore · silent failure does not block user
      }
    };
    void tick();
    const id = window.setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  // Load inbox when dropdown opens
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingItems(true);
    fetchInbox(10)
      .then((notifs) => {
        if (!cancelled) setItems(notifs);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingItems(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Click outside to close
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (
        containerRef.current
        && !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  const onItemClick = async (notif: PortalNotification) => {
    if (!notif.read_at) {
      try {
        await markRead(notif.id);
        setUnread((n) => Math.max(0, n - 1));
        setItems((prev) =>
          prev.map((p) =>
            p.id === notif.id
              ? { ...p, read_at: new Date().toISOString() }
              : p,
          ),
        );
      } catch {
        // ignore · user navigates anyway
      }
    }
  };

  const onMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await markAllRead();
      setUnread(0);
      setItems((prev) =>
        prev.map((p) =>
          p.read_at ? p : { ...p, read_at: new Date().toISOString() },
        ),
      );
    } catch {
      // ignore
    } finally {
      setMarkingAll(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notificaciones${unread > 0 ? ` · ${unread} sin leer` : ""}`}
        className="relative grid h-9 w-9 place-items-center rounded-lg text-white hover:bg-white/10"
        data-testid="notifications-bell"
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span
            className="absolute -right-0.5 -top-0.5 grid h-5 min-w-[20px] place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white"
            data-testid="notifications-badge"
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-12 z-40 max-h-[500px] w-[360px] max-w-[calc(100vw-1rem)] overflow-hidden rounded-xl border border-fulkro-surface-glass-border bg-white shadow-2xl"
          data-testid="notifications-dropdown"
        >
          <header className="flex items-center justify-between border-b border-fulkro-surface-glass-border px-4 py-3">
            <h3 className="text-sm font-bold text-[color:var(--fulkro-title)]">
              Notificaciones
            </h3>
            <button
              type="button"
              onClick={onMarkAllRead}
              disabled={markingAll || unread === 0}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-bold text-[color:var(--fulkro-accent)] hover:bg-fulkro-surface-glass-strong disabled:opacity-40"
            >
              {markingAll ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <CheckCheck className="h-3 w-3" />
              )}
              Marcar todo
            </button>
          </header>

          <div className="max-h-[380px] overflow-y-auto">
            {loadingItems ? (
              <div className="grid place-items-center py-8 text-[color:var(--fulkro-muted)]">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm font-medium text-[color:var(--fulkro-muted)]">
                Sin notificaciones.
              </p>
            ) : (
              <ul>
                {items.map((notif) => {
                  const isUnread = !notif.read_at;
                  return (
                    <li
                      key={notif.id}
                      className={`border-b border-fulkro-surface-glass-border/50 last:border-b-0 ${
                        isUnread ? "bg-[color:var(--fulkro-accent)]/5" : ""
                      }`}
                    >
                      <Link
                        href={notif.target_url}
                        onClick={() => void onItemClick(notif)}
                        className="block px-4 py-3 hover:bg-fulkro-surface-glass-strong"
                      >
                        <div className="flex items-start gap-2">
                          {isUnread && (
                            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[color:var(--fulkro-accent)]" />
                          )}
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <h4 className="truncate text-sm font-bold text-[color:var(--fulkro-title)]">
                                {notif.title}
                              </h4>
                              <span className="shrink-0 text-[11px] font-medium text-[color:var(--fulkro-muted)]">
                                {formatRelative(notif.created_at)}
                              </span>
                            </div>
                            {notif.body && (
                              <p className="mt-0.5 line-clamp-2 text-xs text-[color:var(--fulkro-body)]">
                                {notif.body}
                              </p>
                            )}
                          </div>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <footer className="border-t border-fulkro-surface-glass-border px-4 py-2 text-center">
            <Link
              href="/client-portal/inbox"
              onClick={() => setOpen(false)}
              className="text-xs font-bold text-[color:var(--fulkro-accent)] hover:underline"
            >
              Ver todas →
            </Link>
          </footer>
        </div>
      )}
    </div>
  );
}
