from pathlib import Path
import json
import time

from faster_whisper import WhisperModel


VIDEO = Path(r"C:\Users\miqba\Videos\2026-08-20 20-02-51.mp4")
OUT_DIR = Path(r"C:\Users\miqba\projects\Indonesia Wildfire Analysis\meeting_transcript")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading transcription model...", flush=True)
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
    cpu_threads=8,
    num_workers=1,
)

print("Transcribing...", flush=True)
segments, info = model.transcribe(
    str(VIDEO),
    language="id",
    task="transcribe",
    beam_size=5,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500},
    condition_on_previous_text=False,
    word_timestamps=False,
)

rows = []
for segment in segments:
    row = {
        "start": round(segment.start, 3),
        "end": round(segment.end, 3),
        "text": segment.text.strip(),
    }
    rows.append(row)
    print(f"[{row['start']:8.1f} -> {row['end']:8.1f}] {row['text']}", flush=True)

payload = {
    "language": info.language,
    "language_probability": info.language_probability,
    "duration": info.duration,
    "segments": rows,
}
(OUT_DIR / "transcript.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
)

lines = []
for row in rows:
    start = int(row["start"])
    h, rem = divmod(start, 3600)
    m, s = divmod(rem, 60)
    lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {row['text']}")
(OUT_DIR / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"Saved {len(rows)} segments to {OUT_DIR}", flush=True)
