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

function Controls({ params, setParams }) {
  const handleChange = useCallback((key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }, [setParams])

  return (
    <div className="controls">
      <h3>Material Properties</h3>

      <div className="control-group">
        <label>
          IOR (Index of Refraction)
          <span>{params.ior.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min="1.0"
          max="2.5"
          step="0.01"
          value={params.ior}
          onChange={(e) => handleChange('ior', parseFloat(e.target.value))}
        />
        <p className="hint">1.0=air, 1.33=water, 1.5=glass, 2.4=diamond</p>
      </div>

      <div className="control-group">
        <label>
          Chromatic Aberration
          <span>{params.chromaticAberration.toFixed(3)}</span>
        </label>
        <input
          type="range"
          min="0"
          max="0.15"
          step="0.001"
          value={params.chromaticAberration}
          onChange={(e) =>
            handleChange('chromaticAberration', parseFloat(e.target.value))
          }
        />
        <p className="hint">RGB edge separation (stronger = more rainbow)</p>
      </div>

      <div className="control-group">
        <label>
          Distortion
          <span>{params.distortionScale.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min="0"
          max="2"
          step="0.01"
          value={params.distortionScale}
          onChange={(e) =>
            handleChange('distortionScale', parseFloat(e.target.value))
          }
        />
        <p className="hint">Liquid flow & surface distortion</p>
      </div>

      <div className="control-group">
        <label>
          Thickness
          <span>{params.thickness.toFixed(1)}</span>
        </label>
        <input
          type="range"
          min="0.5"
          max="5"
          step="0.1"
          value={params.thickness}
          onChange={(e) => handleChange('thickness', parseFloat(e.target.value))}
        />
        <p className="hint">Material thickness for refraction depth</p>
      </div>

      <div className="preset-buttons">
        <button onClick={() => setParams({
          ior: 1.5,
          chromaticAberration: 0.08,
          distortionScale: 1.0,
          thickness: 2,
        })}>Glass</button>
        <button onClick={() => setParams({
          ior: 2.42,
          chromaticAberration: 0.12,
          distortionScale: 0.5,
          thickness: 3,
        })}>Diamond</button>
        <button onClick={() => setParams({
          ior: 1.33,
          chromaticAberration: 0.03,
          distortionScale: 1.5,
          thickness: 1.5,
        })}>Water</button>
        <button onClick={() => setParams({
          ior: 1.8,
          chromaticAberration: 0.14,
          distortionScale: 1.8,
          thickness: 2.5,
        })}>Prism</button>
      </div>
    </div>
  )
}

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
        <p>WebGL Refraction + Chromatic Aberration + Edge Distortion</p>
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
          <color attach="background" args={['#1a1a1a']} />

          <ambientLight intensity={0.6} />
          <pointLight position={[10, 10, 10]} intensity={2.5} color="#ff6b6b" />
          <pointLight position={[-10, -10, 10]} intensity={2.5} color="#4ecdc4" />
          <pointLight position={[0, 15, -10]} intensity={2} color="#ffe66d" />
          <pointLight position={[0, -15, -10]} intensity={1.5} color="#c7d2fe" />

          <Suspense fallback={null}>
            <BackgroundCubes />
            <BackgroundRings />
            <BackgroundOrbs />

            <LiquidGlassSphere
              ior={params.ior}
              chromaticAberration={params.chromaticAberration}
              distortionScale={params.distortionScale}
              thickness={params.thickness}
            />

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
      </main>

      <aside className="controls-sidebar">
        <Controls params={params} setParams={setParams} />
      </aside>

      <footer>
        <p>Drag to rotate | Scroll to zoom | Adjust parameters live</p>
        <p className="tech-stack">REACT THREE FIBER | THREE.JS | GLSL SHADERS</p>
      </footer>
    </div>
  )
}

export default App
