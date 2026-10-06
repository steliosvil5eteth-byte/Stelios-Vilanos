"""Read-only verification of hosted MP4 audio against the renderer composition.

Writes QA references/reports only; never modifies delivery media.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import wave
from datetime import datetime, timezone

import numpy as np

BASE = Path(__file__).resolve().parent
RENDERER = BASE / "render_final_carousels.py"
source = RENDERER.read_text()
tree = ast.parse(source)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "original_music")
function_source = ast.get_source_segment(source, node)
scope = {"np": np, "wave": wave}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(RENDERER), "exec"), scope)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def db(value):
    return 20 * math.log10(max(float(value), 1e-20))

def compare(x, y):
    xf = x.reshape(-1).astype(np.float64)
    yf = y.reshape(-1).astype(np.float64)
    ex = float(np.dot(xf, xf))
    ey = float(np.dot(yf, yf))
    gain = float(np.dot(xf, yf) / ex) if ex else 0.0
    err = yf - xf
    rms_ref = math.sqrt(ex / len(xf))
    rms_observed = math.sqrt(ey / len(yf))
    error_rms = float(np.sqrt(np.mean(err * err)))
    return {
        "pearson_correlation": float(np.corrcoef(xf, yf)[0, 1]),
        "cosine_similarity": float(np.dot(xf, yf) / math.sqrt(ex * ey)),
        "observed_gain_relative_to_reference": gain,
        "reference_rms_dbfs": db(rms_ref),
        "observed_rms_dbfs": db(rms_observed),
        "error_rms_dbfs": db(error_rms),
        "signal_to_error_db": db(rms_ref / max(error_rms, 1e-20)),
        "max_absolute_sample_error": float(np.max(np.abs(err))),
    }

summaries = []
series_names = sys.argv[1:] or ["zodiac", "survival", "myth_or_truth"]
for series in series_names:
    final_folder = BASE / "final" / series
    folder = final_folder / "hosted"
    original = json.loads((final_folder / "manifest.json").read_text())
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    candidates = [a for a in manifest.get("assets", []) if a["type"] == "video"] if isinstance(manifest, dict) else []
    if candidates:
        asset = candidates[0]
        hosted = True
    else:
        source_path = Path(original["video"]["path"])
        hosted_path = folder / "video.mp4"
        hosted = hosted_path.exists()
        asset = {"path": str(hosted_path if hosted else source_path),
                 "source_path": str(source_path), "sha256": original["video"]["sha256"],
                 "file_id": None, "url": None}
    video = Path(asset["path"])
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)
    ]))
    astream = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    vstream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    duration = float(vstream["duration"])
    audio_duration = float(astream["duration"])
    sr = int(astream["sample_rate"])
    assert sr == 48000 and astream["channels"] == 2
    qa = folder / "qa" if hosted else final_folder / "qa_audio"
    qa.mkdir(exist_ok=True)
    reference_path = qa / "deterministic_music_reference.wav"
    scope["original_music"](reference_path, duration)
    with wave.open(str(reference_path), "rb") as f:
        assert f.getframerate() == sr and f.getnchannels() == 2
        reference = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768.0
    decoded = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0",
        "-ac", "2", "-ar", str(sr), "-f", "f32le", "pipe:1"
    ], check=True, capture_output=True)
    observed_all = np.frombuffer(decoded.stdout, dtype="<f4").reshape(-1, 2)
    n = len(reference)
    assert len(observed_all) >= n
    observed = observed_all[:n]
    finite = bool(np.isfinite(observed_all).all())
    full = compare(reference, observed)
    windows = []
    for i in range(0, n, sr):
        j = min(n, i + sr)
        windows.append({"start_sample": i, "end_sample_exclusive": j,
                        "start_seconds": i / sr, "end_seconds": j / sr,
                        "sample_frames_compared": j-i,
                        **compare(reference[i:j], observed[i:j])})
    min_corr = min(w["pearson_correlation"] for w in windows)
    all_frames_compared = sum(w["sample_frames_compared"] for w in windows) == n
    max_silence = 0
    run = 0
    for value in np.max(np.abs(observed), axis=1) < 0.001:
        run = run + 1 if value else 0
        max_silence = max(max_silence, run)
    unchanged = sha(video) == sha(asset["source_path"]) == asset["sha256"]
    approved = (finite and unchanged and all_frames_compared and
                full["pearson_correlation"] >= 0.995 and min_corr >= 0.98 and
                abs(audio_duration - duration) <= 1/sr)
    report = {
        "status": "APPROVED_TECHNICAL_MATCH" if approved else "REVIEW_REQUIRED",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "series": series,
        "listened": False,
        "method": "Regenerate the exact original_music function from the authoritative renderer, decode every AAC sample, compare both channels over the entire stated audio/video duration plus exhaustive consecutive one-second windows.",
        "scope_limit": "Mathematical content/coverage verification; no human or model audio audition and no subjective listening-quality assessment.",
        "asset": {"path": str(video), "file_id": asset["file_id"], "url": asset["url"],
                  "sha256": sha(video), "source_sha256": sha(asset["source_path"]),
                  "is_hosted_copy": hosted,
                  "matches_authoritative_final_manifest_sha256": unchanged,
                  "byte_identical_to_local_final": unchanged if hosted else None},
        "composition_source": {"path": str(RENDERER), "sha256": sha(RENDERER),
                               "function": "original_music", "function_sha256": hashlib.sha256(function_source.encode()).hexdigest(),
                               "reference_wav": str(reference_path), "reference_wav_sha256": sha(reference_path),
                               "instrumental_by_construction": True,
                               "definition": "Deterministic sine-wave arpeggio with fixed notes, harmonic partials, exponential envelopes and fades; no sampled voices or prerecorded sound."},
        "stream_count": len(probe["streams"]),
        "audio_stream_count": sum(s["codec_type"] == "audio" for s in probe["streams"]),
        "video_stream_count": sum(s["codec_type"] == "video" for s in probe["streams"]),
        "audio_codec": astream["codec_name"], "sample_rate": sr, "channels": 2,
        "video_duration_seconds": duration, "audio_duration_seconds": audio_duration,
        "reference_sample_frames": n,
        "decoded_sample_frames_including_codec_padding": len(observed_all),
        "compared_sample_frames": n,
        "extra_decoded_codec_padding_frames": len(observed_all)-n,
        "extra_padding_seconds": (len(observed_all)-n)/sr,
        "coverage_fraction_of_stated_duration": n/(sr*duration),
        "all_declared_audio_samples_compared": all_frames_compared,
        "alignment_offset_samples": 0,
        "decoded_pcm_sha256": hashlib.sha256(decoded.stdout).hexdigest(),
        "all_decoded_samples_finite": finite,
        "clipped_samples": int(np.sum(np.abs(observed_all) >= 1)),
        "peak_dbfs": db(np.max(np.abs(observed_all))),
        "rms_dbfs": full["observed_rms_dbfs"],
        "maximum_consecutive_below_minus60_dbfs_seconds": max_silence/sr,
        "full_track_comparison": full,
        "channel_comparisons": [compare(reference[:, c], observed[:, c]) for c in range(2)],
        "minimum_one_second_window_correlation": min_corr,
        "one_second_windows": windows,
        "volume_review": "Soft background instrumental is intentional. No volume change requested or performed.",
        "delivery_assets_modified": False,
        "publication_action": "None",
    }
    report_path = final_folder / "final_audio_qa.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if hosted:
        (folder / "technical_audio_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    result = {"series": series, "status": report["status"], "full_correlation": full["pearson_correlation"],
              "minimum_window_correlation": min_corr, "coverage": report["coverage_fraction_of_stated_duration"],
              "extra_padding_frames": report["extra_decoded_codec_padding_frames"], "report": str(report_path)}
    summaries.append(result)
    print(json.dumps(result), flush=True)
(BASE / ("audio_qa_summary_" + "_".join(series_names) + ".json")).write_text(json.dumps(summaries, indent=2))
