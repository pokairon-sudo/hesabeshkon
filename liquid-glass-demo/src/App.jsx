import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/fiber'
import { Suspense, useState, useCallback } from 'react'
import {
  LiquidGlassSphere,
  BackgroundCubes,
  BackgroundRings,
  BackgroundOrbs,
  CustomGlassIcosahedron
} from './LiquidGlass'
import './App.css'

/**
 * Glass morphism control panel with enhanced UI
 */
function Controls({ params, setParams }) {
  const handleChange = useCallback((key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }, [setParams])

  const presets = [
    { label: 'Glass', ior: 1.5, chromaticAberration: 0.08, distortionScale: 1.0, thickness: 2 },
    { label: 'Diamond', ior: 2.42, chromaticAberration: 0.12, distortionScale: 0.5, thickness: 3 },
    { label: 'Water', ior: 1.33, chromaticAberration: 0.03, distortionScale: 1.5, thickness: 1.5 },
    { label: 'Prism', ior: 1.8, chromaticAberration: 0.14, distortionScale: 1.8, thickness: 2.5 },
  ]

  const controls = [
    {
      key: 'ior',
      label: 'Index of Refraction',
      value: params.ior,
      min: 1.0,
      max: 2.5,
      step: 0.01,
      format: (v) => v.toFixed(2),
      hint: '1.0=air, 1.33=water, 1.5=glass, 2.4=diamond'
    },
    {
      key: 'chromaticAberration',
      label: 'Chromatic Aberration',
      value: params.chromaticAberration,
      min: 0,
      max: 0.15,
      step: 0.001,
      format: (v) => v.toFixed(3),
      hint: 'RGB edge separation (stronger = more rainbow)'
    },
    {
      key: 'distortionScale',
      label: 'Surface Distortion',
      value: params.distortionScale,
      min: 0,
      max: 2,
      step: 0.01,
      format: (v) => v.toFixed(2),
      hint: 'Liquid flow & surface distortion'
    },
    {
      key: 'thickness',
      label: 'Material Thickness',
      value: params.thickness,
      min: 0.5,
      max: 5,
      step: 0.1,
      format: (v) => v.toFixed(1),
      hint: 'Material thickness for refraction depth'
    }
  ]

  return (
    <aside className="controls-sidebar">
      <div className="controls">
        <h3>Material Properties</h3>

        {controls.map((control) => (
          <div key={control.key} className="control-group">
            <label>
              {control.label}
              <span>{control.format(control.value)}</span>
            </label>
            <input
              type="range"
              min={control.min}
              max={control.max}
              step={control.step}
              value={control.value}
              onChange={(e) => handleChange(control.key, parseFloat(e.target.value))}
            />
            <p className="hint">{control.hint}</p>
          </div>
        ))}

        <h3>Quick Presets</h3>
        <div className="preset-buttons">
          {presets.map((preset) => (
            <button
              key={preset.label}
              onClick={() => setParams({
                ior: preset.ior,
                chromaticAberration: preset.chromaticAberration,
                distortionScale: preset.distortionScale,
                thickness: preset.thickness,
              })}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}

/**
 * Floating info badge
 */
function InfoBadge() {
  return (
    <div className="info-badge">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 16v-4"/>
        <path d="M12 8h.01"/>
      </svg>
      <span>Drag to rotate</span>
    </div>
  )
}

/**
 * Main App Component
 */
function App() {
  const [params, setParams] = useState({
    ior: 1.5,
    chromaticAberration: 0.08,
    distortionScale: 1.0,
    thickness: 2,
  })

  return (
    <div className="app">
      <header>
        <h1>Liquid Glass</h1>
        <p>True WebGL refraction with chromatic aberration & edge distortion</p>
      </header>

      <main className="scene-container">
        <Canvas
          dpr={[1, 2]}
          gl={{
            antialias: true,
            alpha: false,
            powerPreference: "high-performance"
          }}
          className="canvas"
          camera={{ position: [0, 0, 8], fov: 50 }}
        >
          <color attach="background" args={['#030305']} />

          {/* Enhanced lighting for better refraction visibility */}
          <ambientLight intensity={0.6} />
          <pointLight position={[10, 10, 10]} intensity={2.5} color="#ff6b6b" />
          <pointLight position={[-10, -10, 10]} intensity={2.5} color="#4ecdc4" />
          <pointLight position={[0, 15, -10]} intensity={2} color="#ffe66d" />
          <pointLight position={[0, -15, -10]} intensity={1.5} color="#c7d2fe" />

          <Suspense fallback={null}>
            {/* Background objects to be refracted through the glass */}
            <BackgroundCubes />
            <BackgroundRings />
            <BackgroundOrbs />

            {/* Main transparent glass sphere */}
            <LiquidGlassSphere
              ior={params.ior}
              chromaticAberration={params.chromaticAberration}
              distortionScale={params.distortionScale}
              thickness={params.thickness}
            />

            {/* Secondary glass element */}
            <CustomGlassIcosahedron
              chromaticAberration={params.chromaticAberration}
            />
          </Suspense>

          <OrbitControls
            enablePan={false}
            minDistance={5}
            maxDistance={15}
            autoRotate
            autoRotateSpeed={0.8}
            enableZoom={true}
            enableDamping={true}
            dampingFactor={0.05}
          />
        </Canvas>

        <InfoBadge />
      </main>

      <Controls params={params} setParams={setParams} />

      <footer>
        <p>Interactive WebGL Demo</p>
        <p className="tech-stack">REACT THREE FIBER &#8226; THREE.JS &#8226; GLSL SHADERS</p>
      </footer>
    </div>
  )
}

export default App
