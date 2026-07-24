"""Extract JPEG frames from a video at given timestamps (seconds)."""
import av, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

src = sys.argv[1]
outdir = sys.argv[2]
stamps = [float(x) for x in sys.argv[3].split(",")]
os.makedirs(outdir, exist_ok=True)

c = av.open(src)
vs = c.streams.video[0]
tb = vs.time_base
for t in stamps:
    c.seek(int(t / tb), stream=vs)
    for frame in c.decode(vs):
        if frame.time is None or frame.time >= t - 0.5:
            img = frame.to_image()
            if img.width > 1600:
                img = img.resize((1600, int(img.height * 1600 / img.width)))
            name = os.path.join(outdir, f"f{int(t):04d}.jpg")
            img.save(name, quality=80)
            print(f"saved {name} (frame at {frame.time:.1f}s)")
            break
c.close()
