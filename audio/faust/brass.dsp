// A polysynth brass stab: two saws and a pulse, a resonant low-pass that swells open in 60 ms and settles.
declare name "brass";
import("common.lib");
env = en.adsr(0.025, 0.14, 0.72, 0.1, gate);
fenv = en.adsr(0.06, 0.28, 0.35, 0.12, gate);
vib = 1 + 0.0035 * os.osc(5.4) * en.ar(0.25, 1, gate);
osc = os.sawtooth(freq * 1.003 * vib) * 0.5 + os.sawtooth(freq * 0.997 * vib) * 0.5 + os.pulsetrain(freq * vib, 0.35) * 0.3;
cut = min(500 + (1100 + 3200 * gain) * fenv + 1.5 * freq, 12000);
process = osc : fi.resonlp(si.smoo(cut), 1.4, 1) : *(env * (0.45 + 0.55 * gain) * 0.45) <: _, _;
