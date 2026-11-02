// A Minimoog-style bass: three detuned saws and a quiet sub sine into a resonant low-pass that opens with the note and closes as it decays.
// The amplitude envelope comes before the filter, so the filter never sees the saws begin with a step.
declare name "bass";
import("common.lib");
env = en.adsr(0.006, 0.22, 0.6, 0.09, gate);
fenv = en.adsr(0.002, 0.14, 0.18, 0.09, gate);
saws = os.sawtooth(freq) * 0.5 + os.sawtooth(freq * 1.0045) * 0.35 + os.sawtooth(freq * 0.9955) * 0.35;
sub = os.osc(freq * 0.5) * 0.22;
cut = max(150, si.smoo(min(300 + freq * 4.0 + (2400 + 12.0 * freq) * fenv * (0.35 + gain), 9000)));
filt = _ : fi.resonlp(cut, 1.0, 1.0) : fi.resonlp(cut * 1.3, 0.7, 1.0);
process = ((saws * env : filt) * 0.9 + sub * env) * (0.55 + 0.45 * gain) * 0.9 <: _, _;
