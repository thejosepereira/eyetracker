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

  // ---- Disk / pillbox PSF: the physically-correct geometric defocus PSF ----
  // Elliptical uniform disk (semi-axes rx, ry px, rotated by angleDeg), edge
  // anti-aliased by 3x3 supersampling, normalised to sum 1. Unlike the Gaussian,
  // its OTF has genuine nulls (this is the real eye's defocus PSF).
  function generateDiskPsf(size, rx, ry, angleDeg) {
    rx = Math.max(rx, 0.5); ry = Math.max(ry, 0.5);
    const c = (size - 1) / 2, th = angleDeg * Math.PI / 180;
    const cos = Math.cos(th), sin = Math.sin(th);
    const psf = new Float64Array(size * size); let sum = 0;
    const ss = 3, inv = 1 / ss, off = (ss - 1) / (2 * ss);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      let frac = 0;
      for (let sy = 0; sy < ss; sy++) for (let sx = 0; sx < ss; sx++) {
        const dx = (x - c) + (sx * inv - off), dy = (y - c) + (sy * inv - off);
        const xr = dx * cos + dy * sin, yr = -dx * sin + dy * cos;
        if ((xr / rx) ** 2 + (yr / ry) ** 2 <= 1) frac += 1;
      }
      const v = frac / (ss * ss); psf[y * size + x] = v; sum += v;
    }
    if (sum <= 0) { psf[((size * size) - 1) >> 1] = 1; return psf; }
    for (let i = 0; i < psf.length; i++) psf[i] /= sum;
    return psf;
  }

  // Band-limit an image below a radial cutoff (cycles/pixel) via an ideal
  // frequency low-pass. Used to keep the target below a disk-OTF's first null so
  // the inverse never has to reconstruct across a zero-crossing.
  function bandLimit(img, W, H, cutoff) {
    const re = Float64Array.from(img), im = new Float64Array(W * H);
    fft2(re, im, W, H, -1);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const fx = (x <= W / 2 ? x : x - W) / W, fy = (y <= H / 2 ? y : y - H) / H;
      if (Math.sqrt(fx * fx + fy * fy) > cutoff) { const i = y * W + x; re[i] = 0; im[i] = 0; }
    }
    fft2(re, im, W, H, +1);
    return re;
  }

  const nextPow2 = n => { let p = 1; while (p < n) p <<= 1; return p; };

  // Soften a PSF by convolving it with a Gaussian of sigma `softPx` (models the
  // diffraction + higher-order aberrations that round a real eye's disk edge).
  // softPx=0 -> unchanged hard disk; large softPx -> approaches a Gaussian blob.
  function softenPsf(psf, size, softPx) {
    if (softPx <= 0) return psf;
    const g = generatePsf(size, softPx, softPx, 0);
    const out = applyPsf(psf, size, size, g, size);
    let s = 0; for (const v of out) s += v > 0 ? v : 0;
    const res = new Float64Array(out.length);
    for (let i = 0; i < out.length; i++) res[i] = (out[i] > 0 ? out[i] : 0) / (s || 1);
    return res;
  }

  // Build the correction/eye PSF from blur params. psfType: "disk" (physically
  // correct geometric defocus, DEFAULT) or "gaussian" (smooth, no OTF nulls).
  // `softness` (px) rounds the disk edge toward a real eye's PSF (see softenPsf).
  function buildPsf(blur, psfType, softness) {
    if (psfType === "gaussian") {
      const ksize = Math.max(kernelSizeForSigma(blur.sigmaX), kernelSizeForSigma(blur.sigmaY));
      return { psf: generatePsf(ksize, blur.sigmaX, blur.sigmaY, blur.angle), ksize };
    }
    // disk: diameter = 4σ (σ = disk radius / 2), so radius = 2σ
    const soft = softness || 0;
    let ksize = Math.max(Math.ceil(Math.max(blur.sigmaX, blur.sigmaY) * 4 * 1.2) | 1, 3);
    if (soft > 0) ksize = (ksize + (Math.ceil(soft * 6) | 1)) | 1;   // room for softening, keep odd
    let psf = generateDiskPsf(ksize, 2 * blur.sigmaX, 2 * blur.sigmaY, blur.angle);
    if (soft > 0) psf = softenPsf(psf, ksize, soft);
    return { psf, ksize };
  }

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

  // ---- Phase 2: constrained + total-variation deconvolution ----
  // Precompute the PSF's OTF once so the iterative solve is cheap.
  function _otf(psf, ksize, W, H) {
    const re = psfToPadded(psf, ksize, W, H), im = new Float64Array(W * H);
    fft2(re, im, W, H, -1);
    return { re, im };
  }
  // Convolve img with the (real, symmetric) PSF given its OTF. For a symmetric
  // PSF H^T = H, so this serves as both the forward blur and its transpose.
  function _applyOTF(img, W, H, otf) {
    const N = W * H, ire = Float64Array.from(img), iim = new Float64Array(N);
    fft2(ire, iim, W, H, -1);
    const ore = new Float64Array(N), oim = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      ore[i] = ire[i] * otf.re[i] - iim[i] * otf.im[i];
      oim[i] = ire[i] * otf.im[i] + iim[i] * otf.re[i];
    }
    fft2(ore, oim, W, H, +1);
    return ore;
  }
  // Gradient of a smoothed anisotropic total-variation penalty (edge-preserving).
  function _tvGrad(p, W, H) {
    const g = new Float64Array(W * H), eps = 1e-3;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = y * W + x, c = p[i];
      const r = x + 1 < W ? p[i + 1] : c, l = x > 0 ? p[i - 1] : c;
      const d = y + 1 < H ? p[i + W] : c, u = y > 0 ? p[i - W] : c;
      g[i] = (c - r) / Math.sqrt((c - r) * (c - r) + eps * eps)
           + (c - l) / Math.sqrt((c - l) * (c - l) + eps * eps)
           + (c - d) / Math.sqrt((c - d) * (c - d) + eps * eps)
           + (c - u) / Math.sqrt((c - u) * (c - u) + eps * eps);
    }
    return g;
  }
  // Solve  min_p ‖H·p − target‖² + λ·TV(p)  s.t. 0 ≤ p ≤ 1  (projected gradient).
  // The box constraint lives INSIDE the solve, so contrast headroom is allocated
  // adaptively (no fixed pre-squeeze) and ringing is controlled by TV, not by
  // clipping a linear inverse after the fact.
  function tvPrecompensate(target, W, H, psf, ksize, opts) {
    opts = opts || {};
    const iters = opts.iters || 30;
    const lam = opts.lambda == null ? 0.003 : opts.lambda;
    const step = opts.step || 0.9;                 // ‖HᵀH‖ ≤ 1 for a normalised PSF
    const otf = _otf(psf, ksize, W, H), N = W * H;
    const p = new Float64Array(N);
    for (let i = 0; i < N; i++) p[i] = Math.min(1, Math.max(0, target[i]));
    for (let k = 0; k < iters; k++) {
      const Hp = _applyOTF(p, W, H, otf);
      const resid = new Float64Array(N);
      for (let i = 0; i < N; i++) resid[i] = Hp[i] - target[i];
      const gdata = _applyOTF(resid, W, H, otf);   // Hᵀ(H p − t)
      const gtv = _tvGrad(p, W, H);
      for (let i = 0; i < N; i++) {
        const v = p[i] - step * (gdata[i] + lam * gtv[i]);
        p[i] = v < 0 ? 0 : (v > 1 ? 1 : v);
      }
    }
    return p;
  }

  // ---- colour ----
  const srgbToLinear = x => (x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4));
  const linearToSrgb = x => (x <= 0.0031308 ? x * 12.92 : 1.055 * Math.pow(x, 1 / 2.4) - 0.055);

  // ---- optical model ----
  const MM_PER_INCH = 25.4;
  function prescriptionToBlur(p, viewingDistanceMm, ppi, opts) {
    opts = opts || {};
    const pupilMm = opts.pupilMm || 3.5;           // photopic indoor screen default
    const pupil = pupilMm / 1000;
    const sigmaPerDia = opts.sigmaPerDiameter || 0.25;
    const minSigma = opts.minSigmaPx || 0.35;
    const strength = opts.correctionStrength == null ? 1.0 : opts.correctionStrength;
    const age = opts.ageYears == null ? 35 : opts.ageYears;
    const aMax = Math.max(0, 15 - 0.25 * age);     // accommodation amplitude (Hofstetter)
    const dofHalf = 1.0 / pupilMm;                  // depth-of-focus half-band (D)
    const pitch = MM_PER_INCH / ppi;
    const dm = Math.max(viewingDistanceMm / 1000, 1e-3);
    // Accommodation-aware residual defocus per meridian (signed power R). Blur
    // appears beyond the far point AND nearer than the near point; sub-DoF defocus
    // is not perceived. Sharp at the far point; handles hyperopia & presbyopia.
    const defocus = R => { const v = 1 / dm + R; return Math.max(0, Math.max(-v, v - aMax) - dofHalf); };
    const diaPx = R => (pupil * defocus(R)) * viewingDistanceMm / pitch;
    const d1 = diaPx(p.sphere), d2 = diaPx(p.sphere + p.cylinder);
    return {
      sigmaX: Math.max(d1 * sigmaPerDia * strength, minSigma),
      sigmaY: Math.max(d2 * sigmaPerDia * strength, minSigma),
      angle: p.axis,
    };
  }

  // ---- combine sphero-cylindrical prescriptions via dioptric power vectors ----
  // A screen shows one image to both eyes, so binocular use needs a single Rx.
  // Naive averaging of axis is wrong; the correct method converts each Rx to the
  // (M, J0, J45) power-vector space, averages there, and converts back.
  function averagePrescriptions(list) {
    let M = 0, J0 = 0, J45 = 0;
    for (const p of list) {
      const c = p.cylinder || 0, a = (p.axis || 0) * Math.PI / 180;
      M += p.sphere + c / 2;
      J0 += -(c / 2) * Math.cos(2 * a);
      J45 += -(c / 2) * Math.sin(2 * a);
    }
    const n = list.length || 1; M /= n; J0 /= n; J45 /= n;
    const Jmag = Math.sqrt(J0 * J0 + J45 * J45);
    const cylinder = -2 * Jmag;                 // minus-cyl convention
    const sphere = M - cylinder / 2;
    let axis = 0.5 * Math.atan2(J45, J0) * 180 / Math.PI;
    axis = ((axis % 180) + 180) % 180;
    return { sphere, cylinder, axis };
  }

  // Resolve an eye-mode ("right" | "left" | "both") + a two-eye profile into the
  // single prescription to render with.
  function resolveRx(mode, rightEye, leftEye) {
    if (mode === "left") return leftEye;
    if (mode === "both") return averagePrescriptions([rightEye, leftEye]);
    return rightEye;
  }

  // ---- full render pipeline on an ImageData-like {data,width,height} ----
  // Returns a new Uint8ClampedArray (RGBA). precompensate=false => contrast-only control.
  function render(rgba, W, H, prescription, opts) {
    opts = opts || {};
    const dr = opts.dynamicRange == null ? 0.55 : opts.dynamicRange;
    const K = opts.regularization == null ? 0.012 : opts.regularization;
    const contrastBoost = opts.contrastBoost == null ? 1.0 : opts.contrastBoost;
    const precomp = opts.precompensate !== false;
    // opts.overrideBlur = {sigmaX, sigmaY, angle} bypasses the prescription->blur
    // step (used by the "dial to clear" page, which sweeps blur directly).
    const blur = opts.overrideBlur || prescriptionToBlur(prescription, opts.viewingDistanceMm || 350,
      opts.ppi || 264, { correctionStrength: opts.correctionStrength, ageYears: opts.ageYears,
                         pupilMm: opts.pupilMm, sigmaPerDiameter: opts.sigmaPerDiameter });
    // Scale the contrast squeeze by how much blur there actually is: with ~no
    // blur to invert, DON'T grey the image (was turning black text grey for no
    // benefit). drEff -> 1 (no squeeze) at the sigma floor, -> dr for real blur.
    const _maxSig = Math.max(blur.sigmaX, blur.sigmaY);
    const _blurAmt = Math.min(1, Math.max(0, (_maxSig - 0.36) / (1.5 - 0.36)));
    const drEff = precomp ? 1 - (1 - dr) * _blurAmt : dr;
    const built = buildPsf(blur, opts.psfType, opts.softness);
    const psf = built.psf, ksize = built.ksize;
    // Optional band-limit cutoff (cycles/px) just below the disk-OTF first null.
    const blCutoff = opts.bandlimit ? 0.9 * 1.22 / (4 * Math.max(blur.sigmaX, blur.sigmaY)) : 0;

    // work at power-of-two padded size to keep the FFT radix-2
    const PW = nextPow2(W), PH = nextPow2(H);
    const out = new Uint8ClampedArray(rgba.length);
    let clipped = 0;

    // ---- HQ path: luma-only, box-constrained + TV deconvolution ----
    // (Phase 2) One expensive solve on luminance; chroma passes through. The
    // constraint allocates contrast adaptively, so no fixed pre-squeeze is needed
    // beyond the optional `dynamicRange` headroom bias.
    if (precomp && opts.method === "tv") {
      const N = PW * PH;
      const Rl = new Float64Array(N), Gl = new Float64Array(N), Bl = new Float64Array(N), Y = new Float64Array(N);
      for (let y = 0; y < PH; y++) for (let x = 0; x < PW; x++) {
        const sx = Math.min(x, W - 1), sy = Math.min(y, H - 1), i = y * PW + x, o = (sy * W + sx) * 4;
        const r = 0.5 + (srgbToLinear(rgba[o] / 255) - 0.5) * drEff;
        const g = 0.5 + (srgbToLinear(rgba[o + 1] / 255) - 0.5) * drEff;
        const b = 0.5 + (srgbToLinear(rgba[o + 2] / 255) - 0.5) * drEff;
        Rl[i] = r; Gl[i] = g; Bl[i] = b; Y[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      }
      const Ytar = blCutoff > 0 ? bandLimit(Y, PW, PH, blCutoff) : Y;
      const Yp = tvPrecompensate(Ytar, PW, PH, psf, ksize,
        { iters: opts.iters || 30, lambda: opts.tvLambda == null ? 0.003 : opts.tvLambda });
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const i = y * PW + x, yv = Y[i], yp = Yp[i];
        if (yp <= 0 || yp >= 1) clipped++;
        const ratio = yv > 1e-4 ? yp / yv : 1;
        const px = (y * W + x) * 4;
        const rc = yv > 1e-4 ? Rl[i] * ratio : yp;
        const gc = yv > 1e-4 ? Gl[i] * ratio : yp;
        const bc = yv > 1e-4 ? Bl[i] * ratio : yp;
        out[px]     = Math.round(linearToSrgb(Math.min(1, Math.max(0, rc))) * 255);
        out[px + 1] = Math.round(linearToSrgb(Math.min(1, Math.max(0, gc))) * 255);
        out[px + 2] = Math.round(linearToSrgb(Math.min(1, Math.max(0, bc))) * 255);
        out[px + 3] = 255;
      }
      return { data: out, blur, ksize, clippedFraction: clipped / (W * H), method: "tv" };
    }

    const chan = new Float64Array(PW * PH);
    for (let c = 0; c < 3; c++) {
      // load channel into padded buffer (edge-replicate padding)
      for (let y = 0; y < PH; y++) for (let x = 0; x < PW; x++) {
        const sx = Math.min(x, W - 1), sy = Math.min(y, H - 1);
        const lin = srgbToLinear(rgba[(sy * W + sx) * 4 + c] / 255);
        chan[y * PW + x] = 0.5 + (lin - 0.5) * drEff;         // contrast reduction
      }
      let res;
      if (precomp) {
        const src = blCutoff > 0 ? bandLimit(chan, PW, PH, blCutoff) : chan;
        res = wienerPrecompensate(src, PW, PH, psf, ksize, K);
      } else res = chan;
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
      opts.ppi || 264, { correctionStrength: opts.correctionStrength, ageYears: opts.ageYears,
                         pupilMm: opts.pupilMm, sigmaPerDiameter: opts.sigmaPerDiameter });
    const built = buildPsf(blur, opts.psfType, opts.softness);
    const psf = built.psf, ksize = built.ksize;
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
    fft1d, fft2, generatePsf, generateDiskPsf, bandLimit, kernelSizeForSigma, nextPow2, psfToPadded,
    wienerPrecompensate, tvPrecompensate, applyPsf, srgbToLinear, linearToSrgb,
    prescriptionToBlur, render, simulateEyeView,
    averagePrescriptions, resolveRx,
  };
  root.VC = VC;
  if (typeof module !== "undefined" && module.exports) module.exports = VC;
})(typeof globalThis !== "undefined" ? globalThis : this);
