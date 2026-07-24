import av, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

for p in [r"C:\Users\Marty\Downloads\Live with Farouk, Friday, 10 July 2026.mp4",
          r"C:\Users\Marty\Downloads\Schermopname 2026-07-08 om 16.19.48.mov"]:
    c = av.open(p)
    dur = c.duration / 1e6 if c.duration else None
    v = c.streams.video[0] if c.streams.video else None
    a = c.streams.audio[0] if c.streams.audio else None
    print(os.path.basename(p))
    print(f"  duration: {dur/60:.1f} min" if dur else "  duration: unknown")
    if v:
        print(f"  video: {v.codec_context.name} {v.codec_context.width}x{v.codec_context.height}")
    if a:
        print(f"  audio: {a.codec_context.name} {a.codec_context.sample_rate}Hz ch={a.codec_context.channels}")
    c.close()

# whisper model cache check
cache = os.path.expanduser("~/.cache/huggingface")
print("\nHF cache:", os.path.exists(cache))
if os.path.exists(cache):
    for root, dirs, files in os.walk(cache):
        for d in dirs:
            if "whisper" in d.lower():
                print("  cached:", os.path.join(root, d))
        break_depth = root.count(os.sep) - cache.count(os.sep)
        if break_depth > 3:
            dirs[:] = []
