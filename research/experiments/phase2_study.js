// Phase 2 definitive study: which pre-compensation algorithm helps most, and how
// much is achievable on a single flat screen, vs a physically-correct (disk-blur)
// simulated eye. Run with:  node research/experiments/phase2_study.js
//
// Outputs (for the python companion to turn into chart + montage):
//   /tmp/claude-0/.../scratchpad/phase2_study.csv
//   /tmp/claude-0/.../scratchpad/phase2_montage.json
const VC = require('../../standalone/engine.js');
const fs = require('fs');

const SCRATCH = process.env.SCRATCH || '/tmp/vc';
try { fs.mkdirSync(SCRATCH, { recursive: true }); } catch {}

const W = 128, H = 128;

// ---- grayscale test content: shrinking letters (acuity-like) ----
function content() {
  // draw with a crude bitmap font via block strokes is hard headless; use bars of
  // decreasing width as a resolution target (proxy for shrinking letters).
  const d = new Float64Array(W * H).fill(1); // white=1
  let y = 8;
  for (let bw = 6; bw >= 1; bw--) {
    for (let x = 8; x < W - 8; x += bw * 2)
      for (let yy = y; yy < y + 14 && yy < H; yy++)
        for (let xx = x; xx < x + bw && xx < W - 8; xx++) d[yy * W + xx] = 0;
    y += 19;
  }
  return d; // linear-ish grayscale in [0,1]
}

// ---- helpers ----
function stretch(g) {
  const s = [...g].sort((a, b) => a - b);
  const lo = s[(s.length * 0.02) | 0], hi = s[(s.length * 0.98) | 0], r = Math.max(1e-6, hi - lo);
  return g.map(v => Math.min(1, Math.max(0, (v - lo) / r)));
}
// Pearson correlation of contrast-normalised images: scale/offset invariant
// "structural legibility" in [~0,1].
function legibility(view, ideal) {
  const a = stretch(view), b = stretch(ideal);
  let ma = 0, mb = 0; for (let i = 0; i < a.length; i++) { ma += a[i]; mb += b[i]; }
  ma /= a.length; mb /= b.length;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < a.length; i++) { const x = a[i] - ma, y = b[i] - mb; num += x * y; da += x * x; db += y * y; }
  return num / Math.sqrt(da * db + 1e-12);
}
function michelson(g) { let mn = 1, mx = 0; for (const v of g) { if (v < mn) mn = v; if (v > mx) mx = v; } return (mx - mn) / (mx + mn + 1e-6); }
const clip01 = g => g.map(v => v < 0 ? 0 : v > 1 ? 1 : v);

// Build the eye's TRUE PSF (physically-correct disk) from sigma (diameter=4σ, radius=2σ).
function eyeDisk(sigmaX, sigmaY, angle) {
  const ks = (Math.ceil(Math.max(sigmaX, sigmaY) * 4 * 1.2) | 1);
  return { psf: VC.generateDiskPsf(Math.max(ks, 3), 2 * sigmaX, 2 * sigmaY, angle), ks: Math.max(ks, 3) };
}
function eyeGauss(sigmaX, sigmaY, angle) {
  const ks = Math.max(VC.kernelSizeForSigma(sigmaX), VC.kernelSizeForSigma(sigmaY));
  return { psf: VC.generatePsf(ks, sigmaX, sigmaY, angle), ks };
}

const DR = 0.55, K = 0.012, ITERS = 30;

// One correction pipeline -> returns perceived (eye-view) grayscale + on-screen.
function runConfig(cfg, target, sigmaX, sigmaY, angle, eye) {
  let tgt = target.map(v => 0.5 + (v - 0.5) * DR);         // contrast headroom
  // correction PSF: gaussian or disk
  const corr = cfg.disk ? eyeDisk(sigmaX, sigmaY, angle) : eyeGauss(sigmaX, sigmaY, angle);
  if (cfg.bandlimit) {                                     // low-pass below disk OTF null
    const diameter = 4 * Math.max(sigmaX, sigmaY);
    const cutoff = 0.9 * 1.22 / diameter;                  // first jinc zero ~1.22/D
    tgt = VC.bandLimit(tgt, W, H, cutoff);
  }
  let p;
  if (cfg.tv) p = VC.tvPrecompensate(tgt, W, H, corr.psf, corr.ks, { iters: ITERS, lambda: 0.006 });
  else p = clip01(VC.wienerPrecompensate(tgt, W, H, corr.psf, corr.ks, K));
  const view = clip01(VC.applyPsf(p, W, H, eye.psf, eye.ks)); // blurred by the TRUE eye
  return { view, screen: p };
}

const CONFIGS = [
  { name: 'wiener_gauss', disk: false, tv: false, bandlimit: false },
  { name: 'tv_gauss', disk: false, tv: true, bandlimit: false },
  { name: 'wiener_disk', disk: true, tv: false, bandlimit: false },
  { name: 'tv_disk', disk: true, tv: true, bandlimit: false },
  { name: 'tv_disk_bandlimit', disk: true, tv: true, bandlimit: true },
];

const target = content();
const rows = [['sphere', 'dist_cm', 'sigma_px', 'config', 'legibility', 'contrast', 'improve_vs_off']];
const montagePanels = [];
const MON_SPH = -2.0, MON_DIST = 70;                       // representative case to visualise

console.log('sphere dist sigma  OFF   ' + CONFIGS.map(c => c.name.padEnd(18)).join(''));
for (const sph of [-1.0, -1.5, -2.0, -3.0]) {
  for (const dcm of [50, 60, 70, 90]) {
    const bl = VC.prescriptionToBlur({ sphere: sph, cylinder: 0, axis: 0 }, dcm * 10, 140, { ageYears: 30 });
    const eye = eyeDisk(bl.sigmaX, bl.sigmaY, bl.angle);   // reality = disk blur
    const off = clip01(VC.applyPsf(target, W, H, eye.psf, eye.ks));
    const offLeg = legibility(off, target);
    let line = `${sph.toFixed(1)}   ${dcm}  ${bl.sigmaX.toFixed(1)}   ${offLeg.toFixed(2)}  `;
    if (sph === MON_SPH && dcm === MON_DIST) {
      montagePanels.push({ label: 'ideal target', data: [...target] });
      montagePanels.push({ label: `eye OFF (${offLeg.toFixed(2)})`, data: [...off] });
    }
    for (const cfg of CONFIGS) {
      const r = runConfig(cfg, target, bl.sigmaX, bl.sigmaY, bl.angle, eye);
      const leg = legibility(r.view, target), con = michelson(r.view);
      rows.push([sph, dcm, bl.sigmaX.toFixed(2), cfg.name, leg.toFixed(4), con.toFixed(4), (leg - offLeg).toFixed(4)]);
      line += (leg.toFixed(2) + (leg > offLeg ? '+' : ' ')).padEnd(18);
      if (sph === MON_SPH && dcm === MON_DIST)
        montagePanels.push({ label: `${cfg.name} (${leg.toFixed(2)})`, data: [...r.view] });
    }
    console.log(line);
  }
}

fs.writeFileSync(`${SCRATCH}/phase2_study.csv`, rows.map(r => r.join(',')).join('\n'));
fs.writeFileSync(`${SCRATCH}/phase2_montage.json`, JSON.stringify({ W, H, panels: montagePanels }));
console.log(`\nWrote ${SCRATCH}/phase2_study.csv and phase2_montage.json`);
