// A gated-reverb-era snare: a noise body, a bright snap, and two drum-head modes that drop a little in pitch.
declare name "snare";
import("common.lib");
body = noise : fi.highpass(1, 1400) : fi.lowpass(2, 9500) : *(ex(0.17));
snap = noise : fi.highpass(2, 4200) : *(ex(0.035));
head = (os.osc(190 * (1 + 0.5 * ex(0.02))) * ex(0.11) + 0.6 * os.osc(330 * (1 + 0.3 * ex(0.02))) * ex(0.07));
process = (0.55 * body + 0.5 * snap + 0.75 * head) * 1.6 : ma.tanh : *(0.4 + 0.6 * gain) <: _, _;
