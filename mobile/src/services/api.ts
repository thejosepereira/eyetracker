// Thin client for the VisionCorrect backend.
import Constants from "expo-constants";
import { EyePrescription, CalibrationProfile } from "../models/types";

const API_URL: string =
  (Constants.expoConfig?.extra as any)?.apiUrl ??
  process.env.EXPO_PUBLIC_API_URL ??
  "http://localhost:8000";

export interface CorrectParams {
  imageUri: string;
  prescription: EyePrescription;
  viewingDistanceMm: number;
  ppi?: number;
  calibration?: Partial<CalibrationProfile>;
}

/** POST /v1/correct — returns the pre-compensated image as a Blob. */
export async function correctImage(p: CorrectParams): Promise<Blob> {
  const form = new FormData();
  form.append("image", {
    uri: p.imageUri,
    name: "input.jpg",
    type: "image/jpeg",
  } as any);
  form.append("sphere", String(p.prescription.sphere));
  form.append("cylinder", String(p.prescription.cylinder));
  form.append("axis", String(p.prescription.axis));
  form.append("viewing_distance_mm", String(p.viewingDistanceMm));
  if (p.ppi) form.append("ppi", String(p.ppi));
  if (p.calibration?.correctionStrength != null)
    form.append("correction_strength", String(p.calibration.correctionStrength));
  if (p.calibration?.regularization != null)
    form.append("regularization", String(p.calibration.regularization));
  if (p.calibration?.dynamicRange != null)
    form.append("dynamic_range", String(p.calibration.dynamicRange));

  const res = await fetch(`${API_URL}/v1/correct`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Vision API error: ${res.status}`);
  return await res.blob();
}

/** GET /health */
export async function health(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export { API_URL };
