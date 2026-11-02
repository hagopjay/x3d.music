// A tom or small kettle drum: a sine that settles from 1.7 times its pitch, with a touch of stick noise.
declare name "tom";
import("common.lib");
f = freq * (1 + 0.7 * ex(0.05));
process = (os.osc(f) * ex(0.34) + 0.15 * (noise : fi.bandpass(2, 900, 4000)) * ex(0.012)) * 1.3 : ma.tanh : *(0.35 + 0.65 * gain) <: _, _;
