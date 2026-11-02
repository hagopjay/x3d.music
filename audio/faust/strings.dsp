// A string machine: three detuned saws per channel, a slow swell, a gentle vibrato, a bright-but-soft low-pass.
declare name "strings";
import("common.lib");
env = en.asr(0.24, 1, 0.42, gate);
vib = 1 + 0.0028 * os.osc(5.1) * en.ar(0.6, 1, gate);
osc(d) = os.sawtooth(freq * d * vib) * 0.4 + os.sawtooth(freq * d * 1.0058 * vib) * 0.3 + os.sawtooth(freq * d * 0.9942 * vib) * 0.3;
voice(d) = osc(d) : fi.lowpass(2, 2600 + 1.2 * freq) : fi.highpass(1, 110) : *(env * (0.4 + 0.6 * gain) * 0.6);
process = voice(0.9992), voice(1.0008);
