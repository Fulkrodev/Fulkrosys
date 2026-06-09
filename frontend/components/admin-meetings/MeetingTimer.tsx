"use client";

/**
 * MeetingTimer — stopwatch UI con start/pause/reset (sub-bloque 7.B.5).
 *
 * - Muestra elapsed time MM:SS
 * - Botones Iniciar / Pausar / Reset
 * - Cuando user clicks Pausar o Reset → callback onElapsedMinutes
 *   con duration_minutes para sync backend (parent ejecuta patch
 *   con duration_minutes opcional)
 *
 * NOTA: stopwatch local-only (no persiste timer state cross-reload).
 * Plan v4.2 menciona "started_at/ended_at" pero esos campos NO están
 * en backend ExploratoryMeetingRow. Solo persistimos duration_minutes
 * agregado en complete_meeting.
 */
import { Pause, Play, RotateCcw } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";

interface MeetingTimerProps {
  initialMinutes?: number;
  disabled?: boolean;
  onElapsedMinutes?: (minutes: number) => void;
}

function formatTime(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export function MeetingTimer({
  initialMinutes = 0,
  disabled = false,
  onElapsedMinutes,
}: MeetingTimerProps) {
  const [elapsedSec, setElapsedSec] = React.useState(initialMinutes * 60);
  const [running, setRunning] = React.useState(false);
  const intervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  React.useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setElapsedSec((prev) => prev + 1);
      }, 1_000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [running]);

  function handleStart() {
    setRunning(true);
  }

  function handlePause() {
    setRunning(false);
    const minutes = Math.floor(elapsedSec / 60);
    onElapsedMinutes?.(minutes);
  }

  function handleReset() {
    setRunning(false);
    setElapsedSec(0);
    onElapsedMinutes?.(0);
  }

  return (
    <div className="flex items-center justify-between rounded-md border border-fulkro-ink-200 bg-white p-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-2xl font-semibold text-fulkro-primary-700">
          {formatTime(elapsedSec)}
        </span>
        <span className="text-xs text-fulkro-ink-500">
          {running ? "en curso" : "pausado"}
        </span>
      </div>
      <div className="flex gap-1">
        {!running ? (
          <Button
            type="button"
            size="sm"
            onClick={handleStart}
            disabled={disabled}
            aria-label="Iniciar timer"
          >
            <Play size={14} className="mr-1" />
            Iniciar
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handlePause}
            disabled={disabled}
            aria-label="Pausar timer"
          >
            <Pause size={14} className="mr-1" />
            Pausar
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={handleReset}
          disabled={disabled || elapsedSec === 0}
          aria-label="Reset timer"
        >
          <RotateCcw size={14} />
        </Button>
      </div>
    </div>
  );
}
