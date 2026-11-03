/**
 * Schedules raw PCM16 mono chunks from `POST /tts/stream` on WebAudio as
 * they arrive (ported from `client/client.html`'s fetch-stream loop, minus
 * the 44-byte WAV header handling — the portal's stream endpoint sends raw
 * PCM16 directly, with the sample rate in the `X-Sample-Rate` header).
 */
const DEFAULT_SAMPLE_RATE = 24_000;

export interface PcmStreamPlayerHandle {
  stop: () => void;
  /** Resolves once every received chunk has been scheduled (not necessarily
   * finished playing — `stop()` is still needed to cut playback short). */
  finished: Promise<void>;
}

export async function playPcmStream(response: Response): Promise<PcmStreamPlayerHandle> {
  const sampleRateHeader = response.headers.get("X-Sample-Rate");
  const sampleRate = sampleRateHeader ? Number(sampleRateHeader) : DEFAULT_SAMPLE_RATE;
  const AudioContextClass =
    window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const audioCtx = new AudioContextClass();
  let playHead = audioCtx.currentTime + 0.1;
  let stopped = false;
  const sources: AudioBufferSourceNode[] = [];

  function scheduleChunk(bytes: Uint8Array): void {
    const sampleCount = bytes.length >> 1;
    if (sampleCount === 0) return;
    const buffer = audioCtx.createBuffer(1, sampleCount, sampleRate);
    const channel = buffer.getChannelData(0);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let i = 0; i < sampleCount; i++) {
      channel[i] = view.getInt16(i * 2, true) / 32768;
    }
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);
    const startAt = Math.max(playHead, audioCtx.currentTime);
    source.start(startAt);
    playHead = startAt + buffer.duration;
    sources.push(source);
  }

  function stop(): void {
    if (stopped) return;
    stopped = true;
    for (const source of sources) {
      try {
        source.stop();
      } catch {
        // Already finished playing on its own.
      }
    }
    void audioCtx.close();
  }

  const reader = response.body?.getReader();
  const finished = (async () => {
    if (!reader) return;
    let leftover = new Uint8Array(0);
    while (!stopped) {
      const { done, value } = await reader.read();
      if (done) break;
      let combined = value;
      if (leftover.length) {
        combined = new Uint8Array(leftover.length + value.length);
        combined.set(leftover, 0);
        combined.set(value, leftover.length);
      }
      // Only schedule whole 16-bit samples; carry an odd trailing byte forward.
      const usable = combined.length - (combined.length % 2);
      leftover = usable < combined.length ? combined.slice(usable) : new Uint8Array(0);
      if (usable > 0) {
        scheduleChunk(combined.slice(0, usable));
      }
    }
  })();

  return { stop, finished };
}
