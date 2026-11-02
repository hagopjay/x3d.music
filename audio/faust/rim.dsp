// A rim shot: a short bright ping over a woody body.
declare name "rim";
import("common.lib");
ping = os.osc(1750) * ex(0.012);
wood = os.osc(480 * (1 + 0.3 * ex(0.01))) * ex(0.05);
click = noise : fi.highpass(1, 2500) : *(ex(0.004)) : *(0.5);
process = (0.7 * ping + 0.8 * wood + click) * 0.55 * (0.35 + 0.65 * gain) <: _, _;
