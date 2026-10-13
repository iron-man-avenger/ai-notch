// Native Real-Time Voice Stack with J.A.R.V.I.S. Hands-Free Ambient Listening
// 100% Free: Web Speech API (STT with Hindi/Hinglish support) + SpeechSynthesis (TTS) + Gemini 3.8 Flash

export type JarvisStatus = 'off' | 'standby' | 'listening' | 'thinking' | 'speaking';
type TalkingListener = (isTalking: boolean) => void;
type JarvisStatusListener = (status: JarvisStatus) => void;
type SpeechQueryListener = (query: string, rawTranscript: string) => void;

const WAKE_WORDS = [
  'mochi',
  'hey mochi',
  'jarvis',
  'hey jarvis',
  'buddy',
  'hey buddy',
  'ok mochi',
  'suno mochi',
  'computer',
  'alexa'
];

export class VoiceEngine {
  public enabled: boolean = true;
  public jarvisMode: boolean = false; // By default OFF: Voice starts on click only
  public wakeWordRequired: boolean = true;
  public currentLanguage: string = 'hi-IN'; // Indian locale handles Hindi, Hinglish, and English
  public isSpeaking: boolean = false;
  public isListening: boolean = false;
  public status: JarvisStatus = 'off'; // By default OFF

  private talkingListeners: Set<TalkingListener> = new Set();
  private statusListeners: Set<JarvisStatusListener> = new Set();
  private queryListeners: Set<SpeechQueryListener> = new Set();

  private recognition: any = null;
  private autoRestartTimer: any = null;
  private shouldBeListening: boolean = false;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];

  constructor() {
    if (typeof window !== 'undefined') {
      // By default OFF unless explicitly saved as 'true' by the user
      const savedJarvis = localStorage.getItem('coucou_jarvis_mode');
      this.jarvisMode = savedJarvis === 'true';
      const savedLang = localStorage.getItem('coucou_voice_lang');
      if (savedLang) {
        this.currentLanguage = savedLang;
      }
    }
  }

  // ── Listeners ─────────────────────────────────────────────────────────────
  onTalkingChange(fn: TalkingListener): () => void {
    this.talkingListeners.add(fn);
    return () => this.talkingListeners.delete(fn);
  }

  onStatusChange(fn: JarvisStatusListener): () => void {
    this.statusListeners.add(fn);
    fn(this.status);
    return () => this.statusListeners.delete(fn);
  }

  onQueryDetected(fn: SpeechQueryListener): () => void {
    this.queryListeners.add(fn);
    return () => this.queryListeners.delete(fn);
  }

  private setStatus(newStatus: JarvisStatus) {
    if (this.status === newStatus) return;
    this.status = newStatus;
    for (const fn of this.statusListeners) {
      try { fn(newStatus); } catch {}
    }
  }

  private setTalking(state: boolean) {
    this.isSpeaking = state;
    if (state) {
      this.setStatus('speaking');
    } else {
      this.setStatus(this.shouldBeListening ? 'standby' : 'off');
    }
    try {
      fetch('http://127.0.0.1:8765/api/voice/speaking-state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_speaking: state })
      }).catch(() => {});
    } catch {}
    for (const listener of this.talkingListeners) {
      try { listener(state); } catch {}
    }
  }

  // ── JARVIS Hands-Free Mode Toggle ──────────────────────────────────────────
  setJarvisMode(enabled: boolean) {
    this.jarvisMode = enabled;
    localStorage.setItem('coucou_jarvis_mode', String(enabled));
    if (enabled) {
      this.startJarvis();
    } else {
      this.stopJarvis();
    }
  }

  toggleListening() {
    this.setJarvisMode(!this.jarvisMode);
  }

  setLanguage(lang: string) {
    this.currentLanguage = lang;
    localStorage.setItem('coucou_voice_lang', lang);
    if (this.shouldBeListening) {
      this.restartListening();
    }
  }

  // ── TEXT-TO-SPEECH (TTS) ──────────────────────────────────────────────────
  speak(text: string, onEnd?: () => void) {
    if (!this.enabled || typeof window === 'undefined' || !window.speechSynthesis) {
      onEnd?.();
      return;
    }

    try {
      // Pause microphone while speaking to prevent Mochi hearing himself
      this.pauseListeningDuringSpeech();

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.04;
      utterance.pitch = 1.0;
      utterance.volume = 0.95;

      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => 
        v.lang.startsWith('en') && 
        (v.name.includes('Natural') || v.name.includes('Zira') || v.name.includes('David') || v.name.includes('Google') || v.name.includes('Jenny'))
      ) || voices.find(v => v.lang.startsWith('en'));

      if (preferred) {
        utterance.voice = preferred;
      }

      utterance.onstart = () => {
        this.setTalking(true);
      };

      utterance.onend = () => {
        this.setTalking(false);
        onEnd?.();
        // Resume listening automatically after speaking completes
        this.resumeListeningAfterSpeech();
      };

      utterance.onerror = () => {
        this.setTalking(false);
        onEnd?.();
        this.resumeListeningAfterSpeech();
      };

      window.speechSynthesis.speak(utterance);
    } catch {
      this.setTalking(false);
      onEnd?.();
      this.resumeListeningAfterSpeech();
    }
  }

  stop() {
    this.setTalking(false);
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  private pauseListeningDuringSpeech() {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {}
    }
  }

  private resumeListeningAfterSpeech() {
    if (this.jarvisMode && this.shouldBeListening) {
      setTimeout(() => {
        if (!this.isSpeaking) {
          this.initRecognition();
        }
      }, 350);
    }
  }

  // ── JARVIS Ambient Continuous Listening ────────────────────────────────────
  startJarvis() {
    this.shouldBeListening = true;
    this.initRecognition();
  }

  stopJarvis() {
    this.shouldBeListening = false;
    if (this.autoRestartTimer) {
      clearTimeout(this.autoRestartTimer);
      this.autoRestartTimer = null;
    }
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {}
      this.recognition = null;
    }
    this.isListening = false;
    this.setStatus('off');
  }

  private restartListening() {
    if (this.recognition) {
      try { this.recognition.abort(); } catch {}
      this.recognition = null;
    }
    if (this.shouldBeListening) {
      this.initRecognition();
    }
  }

  private initRecognition() {
    if (typeof window === 'undefined' || this.isSpeaking) return;

    // In Qt WebEngine, Chromium terminates if SpeechRecognition Mojo binder is called.
    // Ambient listening is powered by the Python WindowsJarvisListener in the OS!
    const isQtWebEngine = typeof navigator !== 'undefined' && (
      navigator.userAgent.includes('QtWebEngine') || 
      (window as any).qt !== undefined
    );

    if (isQtWebEngine) {
      this.isListening = true;
      this.setStatus('standby');
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      if (this.recognition) {
        try { this.recognition.abort(); } catch {}
      }

      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      // Indian locale seamlessly captures Hindi, Hinglish, and English
      rec.lang = this.currentLanguage;

      rec.onstart = () => {
        this.isListening = true;
        this.setStatus('standby');
      };

      rec.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const trans = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += trans;
          } else {
            interim += trans;
          }
        }

        const candidate = (final || interim).trim();
        if (!candidate) return;

        // Check if wake word or direct query is triggered
        const detectedQuery = this.extractQueryIfAddressed(candidate);
        if (detectedQuery) {
          this.setStatus('listening');
          if (final) {
            this.triggerQuery(detectedQuery, candidate);
          }
        }
      };

      rec.onerror = (event: any) => {
        // Expected errors during ambient listening (no-speech, aborted on TTS)
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.warn('[VoiceEngine Ambient STT Notice]', event.error);
        }
      };

      rec.onend = () => {
        this.isListening = false;
        // J.A.R.V.I.S. Auto-Restart Loop: Always wake back up after silence
        if (this.shouldBeListening && !this.isSpeaking) {
          if (this.autoRestartTimer) clearTimeout(this.autoRestartTimer);
          this.autoRestartTimer = setTimeout(() => {
            if (this.shouldBeListening && !this.isSpeaking) {
              this.initRecognition();
            }
          }, 300);
        }
      };

      this.recognition = rec;
      rec.start();
    } catch (err) {
      console.warn('[VoiceEngine initRecognition failed]', err);
    }
  }

  private extractQueryIfAddressed(rawText: string): string | null {
    const lower = rawText.toLowerCase().trim();

    if (!this.wakeWordRequired) {
      return rawText.trim();
    }

    for (const ww of WAKE_WORDS) {
      if (lower.startsWith(ww)) {
        const query = rawText.slice(ww.length).replace(/^[,:.\s]+/, '').trim();
        return query || ww; // If just wake word said, triggers Mochi's greeting
      }
      if (lower.includes(ww)) {
        const idx = lower.indexOf(ww);
        const query = rawText.slice(idx + ww.length).replace(/^[,:.\s]+/, '').trim();
        return query || ww;
      }
    }

    return null;
  }

  private triggerQuery(query: string, raw: string) {
    this.setStatus('thinking');
    for (const fn of this.queryListeners) {
      try { fn(query, raw); } catch {}
    }
  }

  // ── Manual Push-To-Talk Fallback ──────────────────────────────────────────
  startListening(
    onResult: (text: string, isFinal: boolean) => void,
    onError?: (err: any) => void
  ): boolean {
    if (typeof window === 'undefined') return false;

    const isQtWebEngine = typeof navigator !== 'undefined' && (
      navigator.userAgent.includes('QtWebEngine') || 
      (window as any).qt !== undefined
    );

    const SpeechRecognition = !isQtWebEngine && ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
    if (SpeechRecognition) {
      try {
        if (this.recognition) {
          try { this.recognition.abort(); } catch {}
        }

        const rec = new SpeechRecognition();
        rec.continuous = false;
        rec.interimResults = true;
        rec.lang = this.currentLanguage;

        rec.onstart = () => {
          this.isListening = true;
          this.setStatus('listening');
        };

        rec.onresult = (event: any) => {
          let interim = '';
          let final = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript;
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          if (final) {
            onResult(final.trim(), true);
          } else if (interim) {
            onResult(interim.trim(), false);
          }
        };

        rec.onerror = (event: any) => {
          this.isListening = false;
          this.setStatus(this.shouldBeListening ? 'standby' : 'off');
          onError?.(event.error);
        };

        rec.onend = () => {
          this.isListening = false;
          this.setStatus(this.shouldBeListening ? 'standby' : 'off');
        };

        this.recognition = rec;
        rec.start();
        return true;
      } catch (err) {
        console.warn('[Push to talk failed]', err);
      }
    }

    // MediaRecorder fallback
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        this.audioChunks = [];
        const recorder = new MediaRecorder(stream);
        this.mediaRecorder = recorder;
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) this.audioChunks.push(e.data);
        };
        recorder.onstop = () => {
          this.isListening = false;
          stream.getTracks().forEach(t => t.stop());
        };
        recorder.start();
        this.isListening = true;
        this.setStatus('listening');
      }).catch((err) => {
        this.isListening = false;
        onError?.(err);
      });
      return true;
    }

    return false;
  }

  stopListening(): Promise<Blob | null> {
    return new Promise((resolve) => {
      this.isListening = false;
      if (this.recognition) {
        try { this.recognition.stop(); } catch {}
      }
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.onstop = () => {
          const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
          resolve(blob);
          this.resumeListeningAfterSpeech();
        };
        this.mediaRecorder.stop();
        this.mediaRecorder = null;
      } else {
        resolve(null);
        this.resumeListeningAfterSpeech();
      }
    });
  }
}

export const voice = new VoiceEngine();
