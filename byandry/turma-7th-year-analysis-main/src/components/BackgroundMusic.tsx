import { useEffect, useRef, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

export function BackgroundMusic({ videoId }: { videoId: string }) {
  const playerRef = useRef<any>(null);
  const [ready, setReady] = useState(false);
  const [muted, setMuted] = useState(true);

  useEffect(() => {
    if (!videoId) return;
    let cancelled = false;

    function create() {
      if (cancelled || playerRef.current) return;
      playerRef.current = new window.YT.Player("byandry-bgm", {
        videoId,
        playerVars: { autoplay: 1, controls: 0, loop: 1, playlist: videoId, playsinline: 1 },
        events: {
          onReady: (e: any) => {
            e.target.mute();
            e.target.playVideo();
            setReady(true);
          },
          onStateChange: (e: any) => {
            if (e.data === 0) e.target.playVideo();
          },
        },
      });
    }

    if (window.YT?.Player) {
      create();
    } else {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        prev?.();
        create();
      };
      if (!document.getElementById("yt-iframe-api")) {
        const s = document.createElement("script");
        s.id = "yt-iframe-api";
        s.src = "https://www.youtube.com/iframe_api";
        document.body.appendChild(s);
      }
    }

    return () => {
      cancelled = true;
    };
  }, [videoId]);

  if (!videoId) return null;

  function toggle() {
    const p = playerRef.current;
    if (!p) return;
    if (muted) {
      p.unMute();
      p.setVolume(35);
      p.playVideo();
      setMuted(false);
    } else {
      p.mute();
      setMuted(true);
    }
  }

  return (
    <>
      <div
        id="byandry-bgm"
        aria-hidden="true"
        className="pointer-events-none absolute h-px w-px overflow-hidden opacity-0"
      />
      <button
        type="button"
        onClick={toggle}
        disabled={!ready}
        aria-label={muted ? "Ativar música de fundo" : "Desligar música de fundo"}
        title={muted ? "Ativar música" : "Desligar música"}
        className="fixed right-4 top-4 z-50 flex h-11 w-11 items-center justify-center rounded-full border border-border bg-card/80 text-foreground shadow-[var(--shadow-soft)] backdrop-blur transition-all hover:scale-105 hover:text-primary disabled:opacity-40"
      >
        {muted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
      </button>
    </>
  );
}
