"use client";

/**
 * Module-level singleton so at most one `<audio>` element plays across the
 * whole app (voice samples, recent recordings, library cards) — playing a
 * second one stops whichever was already playing.
 */
import { useEffect, useRef, useState } from "react";

type StopFn = () => void;
let activeStop: StopFn | null = null;

function stopOthers(except: StopFn): void {
  if (activeStop && activeStop !== except) {
    activeStop();
  }
}

export interface SingleActiveAudio {
  isPlaying: boolean;
  toggle: () => void;
}

export function useSingleActiveAudio(url: string | null | undefined): SingleActiveAudio {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  function stop(): void {
    audioRef.current?.pause();
    setIsPlaying(false);
  }

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (activeStop === stop) {
        activeStop = null;
      }
    };
    // Unmount-only cleanup: intentionally not re-run when `url` changes.
  }, []);

  function toggle(): void {
    if (!url) return;
    if (isPlaying) {
      stop();
      return;
    }
    stopOthers(stop);
    if (!audioRef.current) {
      audioRef.current = new Audio(url);
      audioRef.current.addEventListener("ended", () => setIsPlaying(false));
    } else if (audioRef.current.src !== url) {
      audioRef.current.src = url;
    }
    activeStop = stop;
    void audioRef.current.play();
    setIsPlaying(true);
  }

  return { isPlaying, toggle };
}
