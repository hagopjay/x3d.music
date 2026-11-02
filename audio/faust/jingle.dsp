// The jingle stick (Turkish crescent): a rapid run of small bright bursts, like a shaken ring of discs.
declare name "jingle";
import("common.lib");
gap = int(ma.SR * 0.013);
b = ex(0.028);
run = b + 0.8 * b@(gap) + 0.65 * b@(2 * gap) + 0.55 * b@(3 * gap) + 0.4 * b@(4 * gap);
ring = os.osc(4320) * 0.5 + os.osc(6790) * 0.35 + os.osc(9100) * 0.25;
process = ((noise : fi.highpass(2, 5800) : fi.lowpass(1, 12500)) * 0.7 + ring * 0.25) * run * 0.6 * (0.35 + 0.65 * gain) <: _, _;
