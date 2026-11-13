import sys, numpy as np, soundfile as sf
x, sr = sf.read(sys.argv[1]); m = x.mean(1) if x.ndim > 1 else x
print(f"dur {len(m)/sr:.1f}s  peak {20*np.log10(np.abs(x).max()+1e-12):.2f} dBFS  rms {20*np.log10(np.sqrt((m**2).mean())+1e-12):.1f} dBFS")
win = int(sr * 5)
print("5s-window RMS dBFS:", ' '.join(f"{20*np.log10(np.sqrt((m[i:i+win]**2).mean())+1e-12):.0f}" for i in range(0, len(m), win)))
clip = (np.abs(x) > 0.999).sum(); print("clipped samples", clip)
