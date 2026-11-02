// A hand clap: three quick noise bursts and a tail through a band-pass.
declare name "clap";
import("common.lib");
gap = int(ma.SR * 0.0095);
burst = ex(0.011);
env = burst + burst@(gap) + burst@(2 * gap) + 0.9 * ex(0.17)@(3 * gap);
process = noise : fi.resonbp(1250, 2.2, 1.0) : fi.highpass(1, 500) : *(env) : *(1.55 * (0.4 + 0.6 * gain)) <: _, _;
