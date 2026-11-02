// The Janissary bass drum (davul): a deep head with a slow decay and a beater of low-passed noise. Pitch from the MIDI note (36 gives 65 Hz).
declare name "davul";
import("common.lib");
f = freq * (1 + 0.9 * ex(0.06));
head = os.osc(f) * ex(0.55) + 0.4 * os.osc(f * 1.58) * ex(0.22);
beat = noise : fi.lowpass(2, 1500) : *(ex(0.03)) : *(0.55);
process = (head + beat) * 1.2 : ma.tanh : *(0.4 + 0.6 * gain) <: _, _;
