import ctypes
import time
import math
import struct
import io
import wave
import threading
from typing import Optional, Callable, Dict, Any

winmm = ctypes.windll.winmm

class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", ctypes.c_ushort),
        ("nChannels", ctypes.c_ushort),
        ("nSamplesPerSec", ctypes.c_ulong),
        ("nAvgBytesPerSec", ctypes.c_ulong),
        ("nBlockAlign", ctypes.c_ushort),
        ("wBitsPerSample", ctypes.c_ushort),
        ("cbSize", ctypes.c_ushort),
    ]

class WAVEHDR(ctypes.Structure):
    pass

WAVEHDR._fields_ = [
    ("lpData", ctypes.c_char_p),
    ("dwBufferLength", ctypes.c_ulong),
    ("dwBytesRecorded", ctypes.c_ulong),
    ("dwUser", ctypes.c_ulong),
    ("dwFlags", ctypes.c_ulong),
    ("dwLoops", ctypes.c_ulong),
    ("lpNext", ctypes.POINTER(WAVEHDR)),
    ("reserved", ctypes.c_ulong),
]

def calculate_rms(raw_bytes: bytes) -> float:
    if len(raw_bytes) < 2:
        return 0.0
    count = len(raw_bytes) // 2
    format_str = f"<{count}h"
    try:
        shorts = struct.unpack(format_str, raw_bytes[:count*2])
        sum_squares = sum(s * s for s in shorts)
        return math.sqrt(sum_squares / count)
    except Exception:
        return 0.0

class WindowsJarvisListener:
    """Native Windows hands-free microphone listener using winmm.
    Captures live user voice on Windows, performs Voice Activity Detection (VAD),
    and sends speech audio directly to Gemini without requiring any browser speech APIs.
    """
    def __init__(
        self,
        on_speech_captured: Optional[Callable[[bytes], None]] = None,
        sample_rate: int = 16000,
        energy_threshold: float = 450.0,
        silence_timeout_ms: int = 800
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_timeout_ms = silence_timeout_ms
        self.on_speech_captured = on_speech_captured

        self.chunk_ms = 100
        self.chunk_bytes = int(sample_rate * (self.chunk_ms / 1000.0) * 2)

        self.is_running = False
        self.is_speaking = False # Suppress mic while Mochi speaks
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[WindowsJarvisListener] Native Windows microphone listener active.")

    def stop(self):
        self.is_running = False

    def set_speaking(self, speaking: bool):
        self.is_speaking = speaking

    def _run_loop(self):
        hWaveIn = ctypes.c_void_p()
        wfx = WAVEFORMATEX()
        wfx.wFormatTag = 1 # PCM
        wfx.nChannels = 1  # Mono
        wfx.nSamplesPerSec = self.sample_rate
        wfx.wBitsPerSample = 16
        wfx.nBlockAlign = wfx.nChannels * (wfx.wBitsPerSample // 8)
        wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign
        wfx.cbSize = 0

        res = winmm.waveInOpen(ctypes.byref(hWaveIn), -1, ctypes.byref(wfx), 0, 0, 0)
        if res != 0:
            print(f"[WindowsJarvisListener Warning] Could not open microphone (code {res}).")
            self.is_running = False
            return

        speech_buffer = []
        is_recording_utterance = False
        silence_chunks = 0
        max_silence_chunks = int(self.silence_timeout_ms / self.chunk_ms)

        buf = (ctypes.c_char * self.chunk_bytes)()
        hdr = WAVEHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
        hdr.dwBufferLength = self.chunk_bytes
        hdr.dwFlags = 0

        try:
            while self.is_running:
                # If Mochi is speaking, skip audio processing to avoid echo
                if self.is_speaking:
                    if is_recording_utterance:
                        speech_buffer.clear()
                        is_recording_utterance = False
                    time.sleep(0.1)
                    continue

                # Read one 100ms chunk
                winmm.waveInPrepareHeader(hWaveIn, ctypes.byref(hdr), ctypes.sizeof(hdr))
                winmm.waveInAddBuffer(hWaveIn, ctypes.byref(hdr), ctypes.sizeof(hdr))
                winmm.waveInStart(hWaveIn)

                time.sleep(self.chunk_ms / 1000.0)

                winmm.waveInStop(hWaveIn)
                winmm.waveInReset(hWaveIn)
                winmm.waveInUnprepareHeader(hWaveIn, ctypes.byref(hdr), ctypes.sizeof(hdr))

                rec_bytes = hdr.dwBytesRecorded
                if rec_bytes <= 0:
                    continue

                chunk_data = bytes(buf[:rec_bytes])
                rms = calculate_rms(chunk_data)

                # Voice Activity Detection
                if rms > self.energy_threshold:
                    if not is_recording_utterance:
                        is_recording_utterance = True
                        speech_buffer = []
                    speech_buffer.append(chunk_data)
                    silence_chunks = 0
                elif is_recording_utterance:
                    speech_buffer.append(chunk_data)
                    silence_chunks += 1

                    # Finished utterance after silence pause (or max 10 seconds of speech)
                    if silence_chunks >= max_silence_chunks or len(speech_buffer) >= 100:
                        total_audio = b"".join(speech_buffer)
                        speech_buffer.clear()
                        is_recording_utterance = False
                        silence_chunks = 0

                        # Ignore brief non-speech blips under 0.8 seconds (throat clearing, typing clicks)
                        if len(total_audio) >= (self.sample_rate * 2 * 0.8):
                            wav_bytes = self._pcm_to_wav(total_audio)
                            if self.on_speech_captured:
                                try:
                                    self.on_speech_captured(wav_bytes)
                                except Exception as err:
                                    print(f"[WindowsJarvisListener Callback Error] {err}")
        finally:
            try:
                winmm.waveInClose(hWaveIn)
            except Exception:
                pass
            print("[WindowsJarvisListener] Microphone closed.")

    def record_single_utterance(self, max_seconds: float = 6.0, silence_timeout_ms: int = 900) -> Optional[bytes]:
        """Records a single voice query on-demand (Click-to-Speak).
        Listens until speech ends or max_seconds elapses, returning WAV bytes.
        """
        hWaveIn = ctypes.c_void_p()
        wfx = WAVEFORMATEX()
        wfx.wFormatTag = 1 # PCM
        wfx.nChannels = 1  # Mono
        wfx.nSamplesPerSec = self.sample_rate
        wfx.wBitsPerSample = 16
        wfx.nBlockAlign = wfx.nChannels * (wfx.wBitsPerSample // 8)
        wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign
        wfx.cbSize = 0

        res = winmm.waveInOpen(ctypes.byref(hWaveIn), -1, ctypes.byref(wfx), 0, 0, 0)
        if res != 0:
            print(f"[WindowsJarvisListener Warning] Could not open microphone (code {res}).")
            return None

        speech_buffer = []
        is_recording_utterance = False
        silence_chunks = 0
        max_silence_chunks = int(silence_timeout_ms / self.chunk_ms)
        max_chunks = int((max_seconds * 1000) / self.chunk_ms)

        buf = (ctypes.c_char * self.chunk_bytes)()
        hdr = WAVEHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
        hdr.dwBufferLength = self.chunk_bytes
        hdr.dwFlags = 0

        try:
            chunks_processed = 0
            while chunks_processed < max_chunks:
                winmm.waveInPrepareHeader(hWaveIn, ctypes.byref(hdr), ctypes.sizeof(hdr))
                winmm.waveInAddBuffer(hWaveIn, ctypes.byref(hdr), ctypes.sizeof(hdr))
                winmm.waveInStart(hWaveIn)

                time.sleep(self.chunk_ms / 1000.0)

                winmm.waveInStop(hWaveIn)
                winmm.waveInReset(hWaveIn)
                winmm.waveInUnprepareHeader(hWaveIn, ctypes.byref(hdr), ctypes.sizeof(hdr))

                rec_bytes = hdr.dwBytesRecorded
                chunks_processed += 1
                if rec_bytes <= 0:
                    continue

                chunk_data = bytes(buf[:rec_bytes])
                rms = calculate_rms(chunk_data)

                if rms > self.energy_threshold:
                    if not is_recording_utterance:
                        is_recording_utterance = True
                    speech_buffer.append(chunk_data)
                    silence_chunks = 0
                elif is_recording_utterance:
                    speech_buffer.append(chunk_data)
                    silence_chunks += 1
                    if silence_chunks >= max_silence_chunks:
                        break

            if speech_buffer:
                total_audio = b"".join(speech_buffer)
                if len(total_audio) >= (self.sample_rate * 2 * 0.3): # At least 0.3s of audio
                    return self._pcm_to_wav(total_audio)
            return None
        finally:
            try:
                winmm.waveInClose(hWaveIn)
            except Exception:
                pass

    def _pcm_to_wav(self, pcm_bytes: bytes) -> bytes:
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_bytes)
        return wav_io.getvalue()

