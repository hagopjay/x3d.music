// A polysynth lead: two saws and a square, a low-pass that opens with the note, vibrato that arrives after about a third of a second.
declare name "lead";
import("common.lib");
env = en.adsr(0.012, 0.1, 0.8, 0.12, gate);
fenv = en.adsr(0.01, 0.22, 0.4, 0.12, gate);
vib = 1 + 0.0042 * os.osc(5.6) * en.asr(0.35, 1, 1, gate);
osc = os.sawtooth(freq * 1.004 * vib) * 0.5 + os.sawtooth(freq * 0.996 * vib) * 0.5 + os.square(freq * vib) * 0.3;
cut = min(900 + (1800 + 4000 * gain) * fenv + 2.5 * freq, 13000);
process = osc : fi.resonlp(si.smoo(cut), 1.1, 1) : *(env * (0.5 + 0.5 * gain) * 0.5) <: _, _;
