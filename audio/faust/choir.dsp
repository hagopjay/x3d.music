// A choir pad on vowels only (no words): a saw with vibrato through three formants that drift slowly between "ah" and "oh".
declare name "choir";
import("common.lib");
env = en.asr(0.55, 1, 0.9, gate);
morph = 0.5 + 0.5 * os.osc(0.09);
f1 = 800 + (450 - 800) * morph;
f2 = 1150 + (800 - 1150) * morph;
f3 = 2900 + (2830 - 2900) * morph;
vib = 1 + 0.004 * os.osc(5.3) * en.ar(0.9, 1, gate);
src(d) = os.sawtooth(freq * d * vib) + 0.7 * os.sawtooth(freq * d * 1.004 * vib);
formants = _ <: (fi.resonbp(f1, 9, 1.0), fi.resonbp(f2, 11, 0.55), fi.resonbp(f3, 22, 0.18)) :> _;
voice(d) = src(d) : formants : *(env * (0.4 + 0.6 * gain) * 0.28);
process = voice(0.998), voice(1.002);
