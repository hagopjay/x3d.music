"""Active-RMS per stem (400 ms windows above -60 dBFS), plus suggested trims to targets."""
import sys, glob, os, json, re, numpy as np, soundfile as sf
TARGET = dict(piano=-17, strings=-23, choir=-27, glass=-27, sub=-22, acid=-24, reese=-21,
              brass=-23, timp=-24, kick=-17, heart=-22, snare=-21, hat=-29, ohat=-31,
              crash=-29, riser=-27)
NAMES = {1:'piano',2:'glass',3:'choir',4:'strings',5:'sub',6:'acid',7:'reese',8:'brass',9:'timp',
         10:'kick',11:'heart',12:'snare',13:'hat',14:'ohat',15:'crash',16:'riser'}
trims = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else {}
new = dict(trims)
for f in sorted(glob.glob(sys.argv[1] + '/*.wav'), key=lambda f: int(os.path.basename(f).split('_')[0])):
    k = NAMES[int(os.path.basename(f).split('_')[0])]
    x, sr = sf.read(f); m = x.mean(1)
    w = int(sr * 0.4); n = len(m) // w
    r = np.sqrt((m[:n*w].reshape(n, w) ** 2).mean(1)); db = 20 * np.log10(r + 1e-12)
    act = db[db > -60]
    a = 20 * np.log10(np.sqrt((10 ** (act / 10)).mean())) if len(act) else -120
    pk = 20 * np.log10(np.abs(x).max() + 1e-12)
    d = TARGET[k] - a
    new[k] = round(trims.get(k, 0) + d, 1)
    print(f"{k:8s} active-RMS {a:6.1f}  peak {pk:6.1f}  target {TARGET[k]:4d}  -> trim {new[k]:+.1f} dB")
if len(sys.argv) > 3:
    json.dump(new, open(sys.argv[3], 'w'), indent=1)
