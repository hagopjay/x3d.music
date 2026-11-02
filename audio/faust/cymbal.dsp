// A crash cymbal for the Janissary band: ten inharmonic partials and bright noise with a long decay.
declare name "cymbal";
import("common.lib");
p(f) = os.square(f);
partials = (p(342) + p(617) + p(891) + p(1264) + p(1707) + p(2338) + p(3091) + p(4157) + p(5329) + p(6612)) * 0.07;
air = noise : fi.highpass(2, 5200) : *(0.55);
process = (partials : fi.highpass(2, 2400)) + air : *(ex(1.9) * (0.2 + 0.8 * ex(0.15))) : *(0.18 + 0.32 * gain) <: _, _;
