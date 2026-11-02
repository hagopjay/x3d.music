// A slow polysynth pad: detuned saws, a low-pass that opens with the attack. The two channels differ a little for width.
declare name "pad";
import("common.lib");
env = en.asr(0.38, 1, 0.9, gate);
osc(d) = os.sawtooth(freq * d) + 0.8 * os.sawtooth(freq * 2 * d * 0.9985) + 0.5 * os.sawtooth(freq * 0.5 * d);
cut = 500 + 2400 * env + 0.8 * freq;
voice(a, b) = (osc(a) + osc(b)) * 0.18 : fi.lowpass(2, cut) : fi.highpass(1, 90) : *(env * (0.35 + 0.65 * gain));
process = voice(0.9965, 1.0035), voice(1.0035, 0.9965);
