// A two-operator FM electric piano in the DX7 manner: a body at 1:1 whose brightness fades over about a second, and a short bell-like tine at 14 times the pitch.
declare name "ep";
import("common.lib");
env = en.adsr(0.002, 2.2, 0.14, 0.28, gate);
body = sin(2 * ma.PI * os.phasor(1, freq) + sin(2 * ma.PI * os.phasor(1, freq)) * (1.0 + 3.0 * gain) * ex(0.9));
tine = sin(2 * ma.PI * os.phasor(1, freq * 14)) * ex(0.07) * gain * 0.25;
process = (body + tine) * env * (0.3 + 0.7 * gain) * 0.55 <: _, _;
