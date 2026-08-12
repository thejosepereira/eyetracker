# VisionCorrect SDK (planned)

The strategic product is not the consumer app — it is the **reusable
vision-correction rendering engine**. This directory is a placeholder for that
SDK.

Today the engine lives in [`../backend/vision_engine`](../backend/vision_engine)
as a pure, UI-independent Python package. The SDK track will expose the same
correction pipeline across runtimes:

| Target | Technology |
|--------|------------|
| Apple | Metal / Metal Performance Shaders / Core Image |
| Android | Vulkan / OpenGL ES / GPU compute |
| Windows | DirectX / DirectCompute |
| Web | WebGPU |

Intended surface (conceptual):

```
VisionCorrect.render(frame, visionProfile) -> correctedFrame
```

The near-term commercial goal is local, real-time, on-device correction
(<16 ms/frame for 60 FPS) to remove cloud latency and keep vision data private.
The current Python engine is the reference implementation these ports must match.
