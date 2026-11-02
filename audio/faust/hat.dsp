// Metallic hats from six square oscillators (the classic ratios), high-passed. Note 42 and below is closed (45 ms); above is open (320 ms).
declare name "hat";
import("common.lib");
open = freq > 100;
d = ba.if(open, 0.32, 0.045);
sq(f) = os.square(f);
metal = (sq(205.3) + sq(304.4) + sq(369.6) + sq(522.7) + sq(540) + sq(800)) * 0.16;
process = metal : fi.highpass(4, 7200) : fi.peak_eq(6, 10500, 3000) : *(ex(d)) : *(0.35 + 0.65 * gain) <: _, _;
