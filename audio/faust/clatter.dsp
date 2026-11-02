// The loom's clatter: a wooden clack and the shuttle's answering tick, tuned by the MIDI note.
declare name "clatter";
import("common.lib");
gap = int(ma.SR * 0.045);
clack = noise : fi.resonbp(freq * 9, 7, 1.0) : *(ex(0.018));
tick = noise : fi.resonbp(freq * 13, 9, 1.0) : *(ex(0.009)) : *(0.45);
process = (clack + tick@(gap)) * 0.4 * (0.35 + 0.65 * gain) <: _, _;
