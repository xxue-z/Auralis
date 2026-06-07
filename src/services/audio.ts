/**
 * 音频播放服务
 * 播放 TTS 音频 + 精灵口型同步
 */

let currentAudio: HTMLAudioElement | null = null;
let onPlayCallback: (() => void) | null = null;
let onStopCallback: (() => void) | null = null;

/**
 * 播放 base64 音频
 */
export async function playAudio(
  audioBase64: string,
  onPlay?: () => void,
  onStop?: () => void,
): Promise<void> {
  // 停止当前播放
  stopAudio();

  onPlayCallback = onPlay;
  onStopCallback = onStop;

  try {
    const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
    currentAudio = audio;

    audio.onplay = () => onPlayCallback?.();
    audio.onended = () => {
      onStopCallback?.();
      currentAudio = null;
    };
    audio.onerror = () => {
      onStopCallback?.();
      currentAudio = null;
    };

    await audio.play();
  } catch (e) {
    console.error("Audio play failed:", e);
    onStopCallback?.();
  }
}

/**
 * 停止当前播放
 */
export function stopAudio(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
    onStopCallback?.();
  }
}

/**
 * 检查是否正在播放
 */
export function isPlaying(): boolean {
  return currentAudio !== null && !currentAudio.paused;
}
