// A timpani: five inharmonic modes that sink a few percent after the stick lands, plus a short thud of low-passed noise.
declare name "timp";
import("common.lib");
bend = 1 + 0.045 * ex(0.09);
mode(r, d, a) = os.osc(freq * r * bend) * ex(d) * a;
stick = noise : fi.lowpass(2, 700) : *(ex(0.014)) : *(0.6);
process = (mode(1, 1.5, 1.0) + mode(1.5, 0.95, 0.55) + mode(1.99, 0.6, 0.4) + mode(2.44, 0.38, 0.26) + mode(2.9, 0.25, 0.18) + stick) * (0.35 + 0.65 * gain) * 0.9 : ma.tanh <: _, _;
