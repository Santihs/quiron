# quiron-voice

Local voice loop for quiron vaults: Claude speaks (Kokoro-82M TTS), you answer out loud (faster-whisper STT).
One warm daemon on `127.0.0.1:47811` keeps both models on the GPU, so each call skips model loading.

| Command | What |
|---|---|
| `qv-say "text"` / `-f note.md` / `--es` / `--bg` / `--stop` | Speak text or a markdown note (markup stripped) |
| `qv-answer [--es] [--target 60]` | Record until 3 s of silence, transcribe, report wpm/pauses/fillers |
| `qv-server start\|status\|stop\|run` | Manage the daemon (`say`/`answer` auto-start it) |

Vault commands `/talk`, `/explain`, `/drill` come from `quiron migrate` (`--voice-lang es` for Spanish).

## Install

```bash
uv tool install './packages/quiron-voice[all]'   # from the quiron repo root
qv-server start                                   # first run downloads models
qv-server status                                  # expect device "tts=cuda stt=cuda/float16"
```

- **Windows:** nothing else. Verified on an RTX 3050 with driver 621.
- **Debian:** `sudo apt install libportaudio2 espeak-ng`. You also need an NVIDIA driver ≥ 570, since torch comes from the cu128 index. Not yet verified. If you hit `libcublas.so.12 not found`, open an issue.
- **macOS:** TTS runs on `mps` and STT on the CPU (`int8`).

`status` shows the device actually in use. An old driver makes torch fall back to the CPU without warning.

## Tests

```bash
uv run --package quiron-voice pytest packages/quiron-voice            # fakes, no GPU/audio (CI)
<tool-python> -m pytest packages/quiron-voice/tests/test_gpu.py -m gpu  # real models
QV_BENCH=1 ...                                                        # + latency asserts; idle GPU only
```
