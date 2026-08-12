// VisionCorrect engine — pure JavaScript port of backend/vision_engine.
// No dependencies, runs in the browser (and in Node for testing).
// Mirrors: optical_model.py, psf.py, deconvolution.py, color.py, renderer.py.
//
// Exposed on `globalThis.VC` (browser) and via module.exports (Node).
(function (root) {
  "use strict";

  // ---- 1D FFT (iterative radix-2, in place). sign=-1 forward, +1 inverse ----
  function fft1d(re, im, n, sign) {
    // bit-reversal permutation
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) {
        const tr = re[i]; re[i] = re[j]; re[j] = tr;
        const ti = im[i]; im[i] = im[j]; im[j] = ti;
      }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const ang = sign * 2 * Math.PI / len;
      const wr = Math.cos(ang), wi = Math.sin(ang);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let k = 0; k < len / 2; k++) {
          const a = i + k, b = i + k + len / 2;
          const xr = re[b] * cr - im[b] * ci;
          const xi = re[b] * ci + im[b] * cr;
          re[b] = re[a] - xr; im[b] = im[a] - xi;
          re[a] += xr;        im[a] += xi;
          const ncr = cr * wr - ci * wi;
          ci = cr * wi + ci * wr; cr = ncr;
        }
      }
    }
  }

  // ---- 2D FFT over W*H arrays (row-major). sign=-1 forward, +1 inverse ----
  function fft2(re, im, W, H, sign) {
    const rr = new Float64Array(W), ri = new Float64Array(W);
    for (let y = 0; y < H; y++) {
      const off = y * W;
      for (let x = 0; x < W; x++) { rr[x] = re[off + x]; ri[x] = im[off + x]; }
      fft1d(rr, ri, W, sign);
      for (let x = 0; x < W; x++) { re[off + x] = rr[x]; im[off + x] = ri[x]; }
    }
    const cr = new Float64Array(H), ci = new Float64Array(H);
    for (let x = 0; x < W; x++) {
      for (let y = 0; y < H; y++) { cr[y] = re[y * W + x]; ci[y] = im[y * W + x]; }
      fft1d(cr, ci, H, sign);
      for (let y = 0; y < H; y++) { re[y * W + x] = cr[y]; im[y * W + x] = ci[y]; }
    }
    if (sign > 0) {
      const inv = 1 / (W * H);
      for (let i = 0; i < W * H; i++) { re[i] *= inv; im[i] *= inv; }
    }
  }

  // ---- PSF: rotated anisotropic Gaussian, normalised (sum==1) ----
  function generatePsf(size, sigmaX, sigmaY, angleDeg) {
    sigmaX = Math.max(sigmaX, 1e-3); sigmaY = Math.max(sigmaY, 1e-3);
    const c = (size - 1) / 2, th = angleDeg * Math.PI / 180;
    const cos = Math.cos(th), sin = Math.sin(th);
    const psf = new Float64Array(size * size);
    let sum = 0;
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const dx = x - c, dy = y - c;
      const xr = dx * cos + dy * sin, yr = -dx * sin + dy * cos;
      const v = Math.exp(-0.5 * ((xr / sigmaX) ** 2 + (yr / sigmaY) ** 2));
      psf[y * size + x] = v; sum += v;
    }
    for (let i = 0; i < psf.length; i++) psf[i] /= sum;
    return psf;
  }

  function kernelSizeForSigma(sigma) {
    let s = Math.ceil(sigma * 6) | 1; return Math.max(s, 3);
  }

  const nextPow2 = n => { let p = 1; while (p < n) p <<= 1; return p; };

  // Embed a (possibly larger-than-image) PSF into WxH with its centre at origin.
  function psfToPadded(psf, ksize, W, H) {
    // center-crop if larger than image, then renormalise
    let src = psf, ph = ksize, pw = ksize;
    if (ksize > H || ksize > W) {
      const nh = Math.min(ksize, H), nw = Math.min(ksize, W);
      const ch = ksize >> 1, cw = ksize >> 1, h2 = nh >> 1, w2 = nw >> 1;
      const cropped = new Float64Array(nh * nw); let s = 0;
      for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) {
        const v = psf[(ch - h2 + y) * ksize + (cw - w2 + x)];
        cropped[y * nw + x] = v; s += v;
      }
      for (let i = 0; i < cropped.length; i++) cropped[i] /= s;
      src = cropped; ph = nh; pw = nw;
    }
    const re = new Float64Array(W * H);
    const shy = ph >> 1, shx = pw >> 1;
    for (let y = 0; y < ph; y++) for (let x = 0; x < pw; x++) {
      const ty = ((y - shy) % H + H) % H, tx = ((x - shx) % W + W) % W;
      re[ty * W + tx] = src[y * pw + x];
    }
    return re;
  }

  // Regularised (Wiener) inverse filter of a single 2-D channel.
  // img: Float64Array length W*H (linear light). Returns Float64Array (may exceed [0,1]).
  function wienerPrecompensate(img, W, H, psf, ksize, K) {
    K = Math.max(K, 1e-8);
    const hre = psfToPadded(psf, ksize, W, H), him = new Float64Array(W * H);
    fft2(hre, him, W, H, -1);
    const ire = Float64Array.from(img), iim = new Float64Array(W * H);
    fft2(ire, iim, W, H, -1);
    const N = W * H, ore = new Float64Array(N), oim = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      const mag = hre[i] * hre[i] + him[i] * him[i] + K;
      const gre = hre[i] / mag, gim = -him[i] / mag;    // conj(H)/(|H|^2+K)
      ore[i] = ire[i] * gre - iim[i] * gim;
      oim[i] = ire[i] * gim + iim[i] * gre;
    }
    fft2(ore, oim, W, H, +1);
    return ore; // real part
  }

  // Forward blur (simulate the eye). Same FFT machinery.
  function applyPsf(img, W, H, psf, ksize) {
    const hre = psfToPadded(psf, ksize, W, H), him = new Float64Array(W * H);
    fft2(hre, him, W, H, -1);
    const ire = Float64Array.from(img), iim = new Float64Array(W * H);
    fft2(ire, iim, W, H, -1);
    const N = W * H, ore = new Float64Array(N), oim = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      ore[i] = ire[i] * hre[i] - iim[i] * him[i];
      oim[i] = ire[i] * him[i] + iim[i] * hre[i];
    }
    fft2(ore, oim, W, H, +1);
    return ore;
  }

  // ---- colour ----
  const srgbToLinear = x => (x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4));
  const linearToSrgb = x => (x <= 0.0031308 ? x * 12.92 : 1.055 * Math.pow(x, 1 / 2.4) - 0.055);

  // ---- optical model ----
  const MM_PER_INCH = 25.4;
  function prescriptionToBlur(p, viewingDistanceMm, ppi, opts) {
    opts = opts || {};
    const pupil = (opts.pupilMm || 4.0) / 1000;
    const sigmaPerDia = opts.sigmaPerDiameter || 0.25;
    const minSigma = opts.minSigmaPx || 0.35;
    const strength = opts.correctionStrength == null ? 1.0 : opts.correctionStrength;
    const pitch = MM_PER_INCH / ppi;
    const diaPx = D => (pupil * Math.abs(D)) * viewingDistanceMm / pitch;
    const d1 = diaPx(p.sphere), d2 = diaPx(p.sphere + p.cylinder);
    return {
      sigmaX: Math.max(d1 * sigmaPerDia * strength, minSigma),
      sigmaY: Math.max(d2 * sigmaPerDia * strength, minSigma),
      angle: p.axis,
    };
  }

  // ---- full render pipeline on an ImageData-like {data,width,height} ----
  // Returns a new Uint8ClampedArray (RGBA). precompensate=false => contrast-only control.
  function render(rgba, W, H, prescription, opts) {
    opts = opts || {};
    const dr = opts.dynamicRange == null ? 0.55 : opts.dynamicRange;
    const K = opts.regularization == null ? 0.012 : opts.regularization;
    const contrastBoost = opts.contrastBoost == null ? 1.0 : opts.contrastBoost;
    const precomp = opts.precompensate !== false;
    const blur = prescriptionToBlur(prescription, opts.viewingDistanceMm || 350,
      opts.ppi || 264, { correctionStrength: opts.correctionStrength });
    const ksize = Math.max(kernelSizeForSigma(blur.sigmaX), kernelSizeForSigma(blur.sigmaY));
    const psf = generatePsf(ksize, blur.sigmaX, blur.sigmaY, blur.angle);

    // work at power-of-two padded size to keep the FFT radix-2
    const PW = nextPow2(W), PH = nextPow2(H);
    const out = new Uint8ClampedArray(rgba.length);
    let clipped = 0;
    const chan = new Float64Array(PW * PH);
    for (let c = 0; c < 3; c++) {
      // load channel into padded buffer (edge-replicate padding)
      for (let y = 0; y < PH; y++) for (let x = 0; x < PW; x++) {
        const sx = Math.min(x, W - 1), sy = Math.min(y, H - 1);
        const lin = srgbToLinear(rgba[(sy * W + sx) * 4 + c] / 255);
        chan[y * PW + x] = 0.5 + (lin - 0.5) * dr;         // contrast reduction
      }
      let res;
      if (precomp) res = wienerPrecompensate(chan, PW, PH, psf, ksize, K);
      else res = chan;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        let v = res[y * PW + x];
        if (v < 0 || v > 1) clipped++;
        v = Math.min(1, Math.max(0, 0.5 + (v - 0.5) * contrastBoost));
        out[(y * W + x) * 4 + c] = Math.round(linearToSrgb(v) * 255);
      }
    }
    for (let i = 3; i < out.length; i += 4) out[i] = 255; // alpha
    return { data: out, blur, ksize, clippedFraction: clipped / (3 * W * H) };
  }

  // Simulate what the prescribed eye perceives when looking at an RGBA image.
  function simulateEyeView(rgba, W, H, prescription, opts) {
    opts = opts || {};
    const blur = prescriptionToBlur(prescription, opts.viewingDistanceMm || 350,
      opts.ppi || 264, { correctionStrength: opts.correctionStrength });
    const ksize = Math.max(kernelSizeForSigma(blur.sigmaX), kernelSizeForSigma(blur.sigmaY));
    const psf = generatePsf(ksize, blur.sigmaX, blur.sigmaY, blur.angle);
    const PW = nextPow2(W), PH = nextPow2(H);
    const out = new Uint8ClampedArray(rgba.length);
    const chan = new Float64Array(PW * PH);
    for (let c = 0; c < 3; c++) {
      for (let y = 0; y < PH; y++) for (let x = 0; x < PW; x++) {
        const sx = Math.min(x, W - 1), sy = Math.min(y, H - 1);
        chan[y * PW + x] = srgbToLinear(rgba[(sy * W + sx) * 4 + c] / 255);
      }
      const res = applyPsf(chan, PW, PH, psf, ksize);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const v = Math.min(1, Math.max(0, res[y * PW + x]));
        out[(y * W + x) * 4 + c] = Math.round(linearToSrgb(v) * 255);
      }
    }
    for (let i = 3; i < out.length; i += 4) out[i] = 255;
    return out;
  }

  const VC = {
    fft1d, fft2, generatePsf, kernelSizeForSigma, nextPow2, psfToPadded,
    wienerPrecompensate, applyPsf, srgbToLinear, linearToSrgb,
    prescriptionToBlur, render, simulateEyeView,
  };
  root.VC = VC;
  if (typeof module !== "undefined" && module.exports) module.exports = VC;
})(typeof globalThis !== "undefined" ? globalThis : this);
