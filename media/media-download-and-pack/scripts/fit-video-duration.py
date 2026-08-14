#!/usr/bin/env python3
"""
Fit a video under a hard DURATION cap by cutting an interval and speeding up
slightly -- and remap an SRT's timestamps through the same transform.

Why the remap matters: cutting video silently desynchronises every subtitle cue
after the cut point. The mapping below is the load-bearing part of this script.

Usage:
    python3 fit-video-duration.py <src.mp4> <out.mp4> \\
        --cut 5.96 12.16 --speed 1.02 \\
        [--srt-in in.srt --srt-out out.srt]

--cut A B : the interval [A, B] is REMOVED (pick the most repetitive stretch)
--speed   : 1.02-1.05 is imperceptible; past ~1.10 audio starts chipmunking

Omit --srt-in/--srt-out to process video only (e.g. when you will author the
subtitles afterwards against the NEW timeline).
"""
import argparse
import os
import re
import subprocess
import sys


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def cut_and_join(src, cut_a, cut_b, out):
    """Remove [cut_a, cut_b] by re-encoding both halves identically, then concat.

    Both halves MUST share codec/params for the concat demuxer's `-c copy` to
    work -- hence the explicit re-encode and matching -ar on each side.
    """
    pa, pb, lst = "/tmp/_fit_pa.mp4", "/tmp/_fit_pb.mp4", "/tmp/_fit_concat.txt"

    subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-t", str(cut_a),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-ar", "48000", pa, "-y"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(cut_b), "-i", src,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-ar", "48000", pb, "-y"], check=True)

    with open(lst, "w") as f:
        f.write(f"file '{pa}'\nfile '{pb}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out, "-y"], check=True)


def speed_up(src, speed, out):
    subprocess.run(["ffmpeg", "-v", "error", "-i", src,
                    "-filter_complex",
                    f"[0:v]setpts={1/speed:.6f}*PTS[v];[0:a]atempo={speed}[a]",
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    out, "-y"], check=True)


def remap(t, cut_a, cut_b, speed):
    """Original time -> time after removing [cut_a, cut_b] and speeding up."""
    nt = t if t < cut_a else cut_a + (t - cut_b)
    return max(0.0, nt / speed)


def parse_srt(path):
    raw = open(path, encoding="utf-8").read().strip()
    cues = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            continue
        m = re.match(r"([\d:,]+)\s*-->\s*([\d:,]+)", lines[1])
        if not m:
            continue

        def ts(t):
            h, mi, rest = t.split(":")
            s, ms = rest.split(",")
            return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000.0

        cues.append({"start": ts(m.group(1)), "end": ts(m.group(2)),
                     "text": "\n".join(lines[2:])})
    return cues


def fmt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--cut", nargs=2, type=float, metavar=("A", "B"))
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--cap", type=float, default=60.0,
                    help="duration cap to warn about (default 60s)")
    ap.add_argument("--srt-in")
    ap.add_argument("--srt-out")
    a = ap.parse_args()

    print(f"source: {duration(a.src):.2f}s")

    mid = a.src
    cut_a, cut_b = (a.cut if a.cut else (0.0, 0.0))
    if a.cut:
        mid = "/tmp/_fit_mid.mp4"
        cut_and_join(a.src, cut_a, cut_b, mid)
        print(f"after cut: {duration(mid):.2f}s")

    if abs(a.speed - 1.0) > 1e-6:
        speed_up(mid, a.speed, a.out)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-i", mid, "-c", "copy",
                        a.out, "-y"], check=True)

    final = duration(a.out)
    print(f"RESULT: {a.out}  {final:.2f}s  {os.path.getsize(a.out)//1024} KB")
    if final > a.cap:
        print(f"WARNING: still over {a.cap}s -- widen the cut or raise --speed",
              file=sys.stderr)

    if a.srt_in and a.srt_out:
        cues = parse_srt(a.srt_in)
        lines, kept = [], 0
        for c in cues:
            s = remap(c["start"], cut_a, cut_b, a.speed)
            e = remap(c["end"], cut_a, cut_b, a.speed)
            if e <= s:            # cue fell entirely inside the removed range
                continue
            kept += 1
            lines += [str(kept), f"{fmt(s)} --> {fmt(e)}", c["text"], ""]
        open(a.srt_out, "w", encoding="utf-8").write("\n".join(lines))
        print(f"SRT remapped: {a.srt_out} ({kept}/{len(cues)} cues kept)")


if __name__ == "__main__":
    main()
