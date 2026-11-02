// A triangle: a few high partials with a long, quiet ring.
declare name "triangle";
import("common.lib");
partial(f, a, d) = os.osc(f) * a * ex(d);
click = noise : fi.highpass(1, 6000) : *(ex(0.004)) : *(0.4);
process = (partial(5120, 1.0, 1.4) + partial(7684, 0.55, 1.0) + partial(10240, 0.35, 0.7) + partial(13120, 0.2, 0.4) + click) * 0.28 * (0.35 + 0.65 * gain) <: _, _;
