"""Command-line entry points: qv-say, qv-answer, qv-server (and `python -m quiron_voice.cli`)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from . import client, paths, protocol
from .metrics import Segment, build
from .text import to_speech


def _lang(args: argparse.Namespace) -> str:
    return "es" if args.es else "en"


def _fail(msg: str) -> int:
    print(f"quiron-voice: {msg}", file=sys.stderr)
    return 1


# --- say ---------------------------------------------------------------------
def say_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="say", description="Speak text or a markdown note out loud.")
    p.add_argument("text", nargs="*", help="text to speak (default: stdin)")
    p.add_argument("-f", "--file", type=Path, help="speak a markdown file")
    p.add_argument("--es", action="store_true", help="Spanish voice")
    p.add_argument("--voice", help="Kokoro voice id (default af_heart / ef_dora)")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--bg", action="store_true", help="return at once; keep speaking")
    p.add_argument("--stop", action="store_true", help="stop current and queued speech")
    return p


def say(argv: Sequence[str] | None = None) -> int:
    a = say_parser().parse_args(argv)
    try:
        client.ensure_server()
        if a.stop:
            client.request({"op": "stop"})
            return 0
        if a.file:
            raw = a.file.read_text(encoding="utf-8")
        elif a.text:
            raw = " ".join(a.text)
        else:
            raw = sys.stdin.read()
        text = to_speech(raw)
        if not text:
            return 0
        msg = {"op": "say", "text": text, "lang": _lang(a), "voice": a.voice, "speed": a.speed}
        resp = client.request(msg, wait=not a.bg)
    except (OSError, client.ServerUnavailable) as e:
        return _fail(str(e))
    if resp is not None and not resp.get("ok"):
        return _fail(resp.get("error", "say failed"))
    return 0


# --- answer --------------------------------------------------------------------
def answer_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="answer", description="Record a spoken answer, transcribe it, report pacing.")
    p.add_argument("--es", action="store_true", help="Spanish")
    p.add_argument("--target", type=int, help="target answer length in seconds (report only)")
    p.add_argument("--silence", type=float, default=3.0, help="seconds of quiet that end the answer")
    p.add_argument("--threshold", type=float, default=0.004, help="RMS level counted as speech (lower = more sensitive)")
    p.add_argument("--max", type=float, default=240.0, help="hard cap in seconds")
    p.add_argument("--no-beep", action="store_true")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p


def answer(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - needs a microphone
    import numpy as np

    from .audio import STT_RATE, SilenceDetector, beep, record

    a = answer_parser().parse_args(argv)
    lang = _lang(a)
    try:
        client.ensure_server()
        client.wait_ready("stt")  # first run downloads the model; don't record into the void
    except (OSError, client.ServerUnavailable) as e:
        return _fail(str(e))

    def start_beep() -> None:
        if not a.no_beep:
            import sounddevice as sd

            sd.play(beep(880), 24_000, blocking=True)

    detector = SilenceDetector(silence_s=a.silence, max_s=a.max, threshold=a.threshold)
    print("recording… (stops after %.0fs of silence)" % a.silence, file=sys.stderr)
    audio, spoken = record(detector, on_start=start_beep)
    if not a.no_beep:
        import sounddevice as sd

        sd.play(beep(660), 24_000, blocking=True)

    t0 = time.perf_counter()
    payload = np.ascontiguousarray(audio, dtype=np.float32).tobytes()
    resp = client.request({"op": "transcribe", "lang": lang, "nbytes": len(payload)}, payload)
    if not resp or not resp.get("ok"):
        return _fail((resp or {}).get("error", "transcription failed"))
    latency = time.perf_counter() - t0

    segs = [Segment(*s) for s in resp["segments"]]
    report = build(segs, spoken or len(audio) / STT_RATE, lang, a.target)
    paths.last_transcript().write_text(resp["text"], encoding="utf-8")
    if a.json:
        print(json.dumps({"text": resp["text"], "report": report.__dict__, "stt_seconds": latency}))
    else:
        print("TRANSCRIPT:\n" + resp["text"] + "\n")
        print(report.render())
        print(f"stt: {latency:.2f}s")
    return 0


# --- server ----------------------------------------------------------------------
def server_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="voice-server", description="Manage the warm voice daemon.")
    sub = p.add_subparsers(dest="action", required=True)
    for name, help_ in (
        ("run", "run in the foreground"),
        ("start", "start in the background and wait until it answers"),
        ("stop", "shut the daemon down"),
        ("status", "print device and model state"),
    ):
        sp = sub.add_parser(name, help=help_)
        if name in {"run", "start"}:
            sp.add_argument("--device", choices=["cuda", "mps", "cpu"], help="override auto-detection")
            sp.add_argument("--whisper-model", default="small")
    return p


def server(argv: Sequence[str] | None = None) -> int:
    a = server_parser().parse_args(argv)
    if a.action == "run":  # pragma: no cover - loads real models
        from .server import main

        main(a.device, a.whisper_model)
        return 0
    try:
        if a.action == "start":
            extra = ["--whisper-model", a.whisper_model] + (["--device", a.device] if a.device else [])
            h = client.ensure_server(spawn=lambda: client.spawn_server(extra))
            print(json.dumps(h))
        elif a.action == "status":
            print(json.dumps(client.request({"op": "health"})))
        elif a.action == "stop":
            client.request({"op": "shutdown"})
            print("stopped")
    except OSError:
        print(json.dumps(protocol.err("not running")))
        return 1
    except client.ServerUnavailable as e:
        return _fail(str(e))
    return 0


# --- entry points ---------------------------------------------------------------------
def say_main() -> None:
    sys.exit(say())


def answer_main() -> None:
    sys.exit(answer())


def server_main() -> None:
    sys.exit(server())


def main(argv: Sequence[str] | None = None) -> int:
    """`python -m quiron_voice.cli {say|answer|server} ...` — used by spawn and by quiron."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in {"say", "answer", "server"}:
        print("usage: quiron_voice.cli {say|answer|server} ...", file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    return {"say": say, "answer": answer, "server": server}[cmd](rest)


if __name__ == "__main__":
    sys.exit(main())
