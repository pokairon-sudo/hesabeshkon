# Liquid Glass Demo

A true "Liquid Glass" effect demo built with React Three Fiber, featuring:

- **Real optical refraction** using `MeshTransmissionMaterial`
- **Chromatic aberration** - RGB channel separation at edges
- **Edge distortion** with Fresnel glow effects
- **Custom GLSL shaders** with FBM noise for liquid flow animation
- **Real-time parameter controls** for IOR, aberration, distortion

## Stack

- **React 19** - UI framework
- **Three.js 0.187** - 3D engine
- **@react-three/fiber** - Declarative Three.js
- **@react-three/drei** - Helper components (MeshTransmissionMaterial, Float, OrbitControls)
- **@khoivudev/liquid-glass-react** - Procedural liquid glass shaders
- **Vite** - Build tool

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

Then open http://localhost:5173

## Controls

| Parameter | Range | Description |
|-----------|-------|-------------|
| IOR | 1.0 - 2.5 | Index of Refraction (1.33=water, 1.5=glass, 2.4=diamond) |
| Chromatic Aberration | 0 - 0.1 | RGB channel separation intensity |
| Distortion Scale | 0 - 2 | Liquid flow/FBM noise intensity |
| Thickness | 0.5 - 5 | Material thickness for transmission |
| Roughness | 0 - 1 | Surface smoothness (0 = mirror-like) |

### Presets

- **Standard Glass** - Default IOR 1.5, low distortion
- **Diamond** - High IOR 2.42, strong chromatic aberration
- **Water** - IOR 1.33, higher distortion
- **Prism** - High distortion with strong RGB separation

## Project Structure

```
src/
├── App.jsx           # Main component with Canvas and Controls
├── App.css           # Dark theme styling
├── index.css         # Global resets
├── LiquidGlass.jsx   # 3D components and GLSL shaders
│   ├── LiquidGlassSphere    # MeshTransmissionMaterial sphere
│   ├── BackgroundGeometry   # Objects behind glass
│   └── CustomLiquidGlass    # Custom GLSL shader version
└── main.jsx         # React entry point
```

## Key Features

### 1. True Refraction (MeshTransmissionMaterial)

The glass sphere uses real ray-traced refraction:

```jsx
<MeshTransmissionMaterial
  backside
  thickness={2}
  roughness={0.05}
  transmission={1}
  ior={1.5}
  chromaticAberration={0.02}
  distortion={0.5}
/>
```

### 2. Custom GLSL Shader

The `CustomLiquidGlass` component uses a fragment shader with:

- **FBM noise** for organic liquid flow
- **Per-channel offset** for chromatic aberration
- **Fresnel calculation** for edge glow
- **Time-based animation** for flowing effect

### 3. Performance Safeguards

- `dpr={[1, 2]}` - Limits pixel ratio for performance
- `Suspense` - Lazy loading with fallback
- Error boundaries for WebGL fallback
- CSS fallback for unsupported browsers

## Browser Support

| Browser | Support |
|---------|---------|
| Chrome/Edge | Full WebGL 2.0 support |
| Firefox | Full WebGL 2.0 support |
| Safari | Good support (metal-based) |
| Mobile Chrome | Supported (lower pixel ratio) |
| Mobile Safari | Supported |

For browsers without WebGL, a CSS `backdrop-filter` fallback is provided.

## Building for Production

```bash
npm run build
npm run preview  # Local preview
```

## License

MIT
