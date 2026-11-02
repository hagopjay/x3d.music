// A 1982 drum-machine kick: a sine that drops from about four times its pitch in 45 ms, a short click, soft clipping. Pitch from the MIDI note (36 gives 65 Hz).
declare name "kick";
import("common.lib");
f = freq * (1 + 3.0 * ex(0.045));
thump = os.osc(f) * ex(0.30);
click = noise : fi.highpass(2, 2800) : *(ex(0.007)) : *(0.25 + 0.6 * gain);
process = (thump * 1.15 + click) * 1.7 : ma.tanh : *(0.85 * gain + 0.15) <: _, _;
