// Audio engine bridging Coucou's official Sound engine (29 WAVs)
// with native Web Audio synthesis fallback.

import { Sound } from '../coucou/core/sound';

class AppSoundEngine {
  public enabled: boolean = true;

  constructor() {
    // Preload Coucou sounds on startup
    if (typeof window !== 'undefined') {
      Sound.preload().catch(() => {});
    }
  }

  playExpand() {
    if (!this.enabled) return;
    Sound.play('open');
  }

  playCollapse() {
    if (!this.enabled) return;
    Sound.play('close');
  }

  playClick() {
    if (!this.enabled) return;
    Sound.play('blip');
  }

  playComplete() {
    if (!this.enabled) return;
    Sound.play('approve');
  }

  playToggle(on: boolean) {
    if (!this.enabled) return;
    Sound.play(on ? 'pop' : 'gulp');
  }

  playLove() {
    if (!this.enabled) return;
    Sound.play('love');
  }

  playError() {
    if (!this.enabled) return;
    Sound.play('error');
  }

  playReminderChime() {
    if (!this.enabled) return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) {
        Sound.play('finish');
        return;
      }
      const ctx = new AudioCtx();
      const now = ctx.currentTime;
      // High-definition 3-tone crystal bell chime (D5 -> A5 -> D6)
      const playBellTone = (freq: number, start: number, duration: number, gainVal: number) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, start);
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(gainVal, start + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(start + duration);
      };
      playBellTone(587.33, now, 0.45, 0.25);
      playBellTone(880.00, now + 0.12, 0.55, 0.28);
      playBellTone(1174.66, now + 0.24, 0.75, 0.30);
    } catch {
      Sound.play('finish');
    }
  }

  playNotification() {
    if (!this.enabled) return;
    this.playReminderChime();
  }
}

export const sounds = new AppSoundEngine();
