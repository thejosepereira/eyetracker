# VisionCorrect — Mobile (Expo / React Native)

Calibration & demonstration client for the VisionCorrect engine. This is the
consumer-facing calibration/demo interface; the reusable value is the backend
[`vision_engine`](../backend/vision_engine).

## Screens (spec flow)

```
Welcome → VisionProfile → Calibration → Demo → Settings(Advanced)
```

- **Welcome** — entry point.
- **VisionProfile** — per-eye Sphere / Cylinder / Axis + viewing distance, saved
  to `AsyncStorage`.
- **Calibration** — pairwise A/B staircase to refine correction strength (mirrors
  `vision_engine.PairwiseStaircase`).
- **Demo** — pick a photo, toggle correction ON/OFF, calls `POST /v1/correct`.
- **Settings** — API URL + backend health.

## Run

```bash
cd mobile
npm install
# point the app at your backend (defaults to http://localhost:8000):
#   edit app.json  -> expo.extra.apiUrl
#   or set EXPO_PUBLIC_API_URL
npx expo start
```

On a physical device, use your machine's LAN IP (not `localhost`) for `apiUrl`.

## Notes

- This is a v0.1 skeleton: on-device GPU rendering, camera feed and real-time
  video (spec v0.3–v0.4) are future work. Today the heavy lifting is done by the
  backend and the result is displayed.
- `expo-image-picker` needs photo-library permission (handled at first use).
