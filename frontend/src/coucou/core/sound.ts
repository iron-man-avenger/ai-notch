// SoundEngine — port of SoundEngine.swift.
// The 29 WAVs are the macOS app's own files (see SOUNDS_DIR in vite.config.ts);
// they are served at /sounds/<name>.wav. Default volume 0.12, slider range 0–0.2,
// exactly like the Mac player, and several sounds may overlap.

export const SOUND_NAMES = [
  "peek", "open", "close", "hover", "blip", "slap", "annoyed", "dizzy", "greet",
  "work", "finish", "error", "approval", "question", "approve", "gulp", "tick",
  "send", "love", "pop", "proud", "wink", "yawn", "attach", "think", "search",
  "rate", "sleep", "greeting",
] as const;

export type SoundName = (typeof SOUND_NAMES)[number];

class SoundEngine {
  enabled = true;
  volume = 0.12;

  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private buffers = new Map<string, AudioBuffer>();
  private rawBuffers = new Map<string, ArrayBuffer>();
  private loading: Promise<void> | null = null;
  private idleTimer: number | null = null;
  /** Sounds still playing, by name, so one can be faded out (the greeting). */
  private playing = new Map<string, Set<{ src: AudioBufferSourceNode; gain: GainNode }>>();

  constructor() {
    // Automatically initialize/resume AudioContext on first user interaction (pointerdown or keydown)
    if (typeof window !== "undefined") {
      const unlock = () => {
        this.resume();
        window.removeEventListener("pointerdown", unlock);
        window.removeEventListener("keydown", unlock);
      };
      window.addEventListener("pointerdown", unlock, { passive: true, once: true });
      window.addEventListener("keydown", unlock, { passive: true, once: true });
    }
  }

  /** Lazily creates the AudioContext upon user gesture to comply with browser autoplay policies */
  private getOrCreateContext(): AudioContext | null {
    if (this.ctx) {
      if (this.ctx.state === "suspended") {
        void this.ctx.resume();
      }
      return this.ctx;
    }
    if (typeof window === "undefined") return null;
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    try {
      const ctx = new Ctor();
      this.ctx = ctx;
      const master = ctx.createGain();
      master.gain.value = this.volume;
      master.connect(ctx.destination);
      this.master = master;

      // Decode any preloaded raw audio buffers
      for (const [name, raw] of this.rawBuffers.entries()) {
        if (!this.buffers.has(name)) {
          ctx.decodeAudioData(raw.slice(0)).then((buf) => {
            this.buffers.set(name, buf);
          }).catch(() => {});
        }
      }
      return ctx;
    } catch {
      return null;
    }
  }

  /** Preloads WAV assets into memory without triggering autoplay warnings */
  preload(): Promise<void> {
    if (this.loading) return this.loading;
    this.loading = (async () => {
      await Promise.all(
        SOUND_NAMES.map(async (name) => {
          try {
            const res = await fetch(`/sounds/${name}.wav`);
            if (!res.ok) return;
            const arrayBuf = await res.arrayBuffer();
            this.rawBuffers.set(name, arrayBuf);
            if (this.ctx && this.ctx.state !== "suspended") {
              const buf = await this.ctx.decodeAudioData(arrayBuf.slice(0));
              this.buffers.set(name, buf);
            }
          } catch {
            /* a missing sound must never break the island */
          }
        }),
      );
    })();
    return this.loading;
  }

  /** Call after any user input to resume the audio context */
  resume() {
    if (this.idleTimer != null) {
      window.clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
    const ctx = this.getOrCreateContext();
    if (ctx && ctx.state === "suspended") {
      void ctx.resume();
    }
  }

  /**
   * Called when the island goes quiet. A running AudioContext keeps an audio
   * thread and its render quantum alive even with nothing playing.
   */
  idle() {
    if (!this.ctx || this.ctx.state !== "running" || this.idleTimer != null) return;
    this.idleTimer = window.setTimeout(() => {
      this.idleTimer = null;
      void this.ctx?.suspend();
    }, 1500);
  }

  setVolume(v: number) {
    this.volume = Math.max(0, Math.min(0.2, v));
    if (this.master) this.master.gain.value = this.volume;
  }

  setEnabled(on: boolean) {
    this.enabled = on;
  }

  play(name: SoundName | string) {
    if (!this.enabled) return;
    const ctx = this.getOrCreateContext();
    const master = this.master;
    if (!ctx || !master) return;

    if (this.idleTimer != null) {
      window.clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
    if (ctx.state === "suspended") void ctx.resume();

    const playBuffer = (buf: AudioBuffer) => {
      const src = ctx.createBufferSource();
      src.buffer = buf;
      const gain = ctx.createGain();
      src.connect(gain);
      gain.connect(master);
      const voice = { src, gain };
      let voices = this.playing.get(name);
      if (!voices) this.playing.set(name, (voices = new Set()));
      voices.add(voice);
      src.onended = () => {
        voices.delete(voice);
        gain.disconnect();
      };
      src.start();
    };

    const buf = this.buffers.get(name);
    if (buf) {
      playBuffer(buf);
      return;
    }

    // If buffer not decoded yet but raw data is available, decode and play
    const raw = this.rawBuffers.get(name);
    if (raw) {
      ctx.decodeAudioData(raw.slice(0)).then((decoded) => {
        this.buffers.set(name, decoded);
        playBuffer(decoded);
      }).catch(() => {});
    }
  }

  /** Fades every playing copy of `name` to silence over `seconds`, then stops it. */
  fadeOut(name: string, seconds: number) {
    const ctx = this.ctx;
    const voices = this.playing.get(name);
    if (!ctx || !voices) return;
    const t = ctx.currentTime;
    for (const { src, gain } of voices) {
      gain.gain.cancelScheduledValues(t);
      gain.gain.setValueAtTime(gain.gain.value, t);
      gain.gain.linearRampToValueAtTime(0, t + seconds);
      try {
        src.stop(t + seconds);
      } catch {
        /* already stopped */
      }
    }
  }
}

export const Sound = new SoundEngine();
