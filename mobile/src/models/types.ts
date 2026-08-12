// Shared vision-profile types. Mirrors the spec's data model.

export interface EyePrescription {
  sphere: number;   // dioptres (negative = myopia)
  cylinder: number; // dioptres, minus-cyl convention
  axis: number;     // degrees 0..180
}

export interface DeviceInfo {
  model: string;
  widthPixels: number;
  heightPixels: number;
  pixelsPerInch: number;
}

export interface CalibrationProfile {
  correctionStrength: number;
  regularization: number;
  dynamicRange: number;
  contrastBoost: number;
  edgeCompensation: number;
  chromaticCompensation?: { red: number; green: number; blue: number };
}

export interface VisionProfile {
  id: string;
  name: string;
  rightEye: EyePrescription;
  leftEye: EyePrescription;
  viewingDistanceMm: number;
  device?: DeviceInfo;
  calibration?: CalibrationProfile;
}

export const emptyPrescription = (): EyePrescription => ({
  sphere: 0,
  cylinder: 0,
  axis: 0,
});

export const defaultCalibration = (): CalibrationProfile => ({
  correctionStrength: 1.0,
  regularization: 0.012,
  dynamicRange: 0.55,
  contrastBoost: 1.0,
  edgeCompensation: 0.0,
});
