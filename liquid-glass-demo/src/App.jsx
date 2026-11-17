import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei'
import { Suspense, useState, useCallback } from 'react'
import { LiquidGlassSphere, BackgroundGeometry, CustomLiquidGlass } from './LiquidGlass'
import './App.css'

/**
 * Control Panel for adjusting liquid glass parameters
 */
function Controls({ params, setParams }) {
  const handleChange = useCallback((key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }, [setParams])

  return (
    <div className="controls">
      <h3>Liquid Glass Parameters</h3>

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
        <p className="hint">1.0 = air, 1.33 = water, 1.5 = glass, 2.4 = diamond</p>
      </div>

      <div className="control-group">
        <label>
          Chromatic Aberration
          <span>{params.chromaticAberration.toFixed(3)}</span>
        </label>
        <input
          type="range"
          min="0"
          max="0.1"
          step="0.001"
          value={params.chromaticAberration}
          onChange={(e) =>
            handleChange('chromaticAberration', parseFloat(e.target.value))
          }
        />
        <p className="hint">RGB channel separation at edges</p>
      </div>

      <div className="control-group">
        <label>
          Distortion Scale
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
        <p className="hint">Liquid flow intensity</p>
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
        <p className="hint">Glass material thickness</p>
      </div>

      <div className="control-group">
        <label>
          Roughness
          <span>{params.roughness.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={params.roughness}
          onChange={(e) => handleChange('roughness', parseFloat(e.target.value))}
        />
        <p className="hint">Surface smoothness (0 = mirror)</p>
      </div>

      <div className="preset-buttons">
        <button onClick={() => setParams({
          ior: 1.5,
          chromaticAberration: 0.02,
          distortionScale: 0.5,
          thickness: 2,
          roughness: 0.05,
        })}>Standard Glass</button>
        <button onClick={() => setParams({
          ior: 2.42,
          chromaticAberration: 0.05,
          distortionScale: 0.3,
          thickness: 3,
          roughness: 0.02,
        })}>Diamond</button>
        <button onClick={() => setParams({
          ior: 1.33,
          chromaticAberration: 0.01,
          distortionScale: 0.8,
          thickness: 1,
          roughness: 0.1,
        })}>Water</button>
        <button onClick={() => setParams({
          ior: 1.8,
          chromaticAberration: 0.08,
          distortionScale: 1.5,
          thickness: 2.5,
          roughness: 0.15,
        })}>Prism</button>
      </div>
    </div>
  )
}

/**
 * Scene loader with fallback
 */
function SceneLoader({ children }) {
  const [hasError, setHasError] = useState(false)

  if (hasError) {
    return (
      <div className="fallback">
        <p>WebGL not supported</p>
        <p>Falling back to CSS blur effect</p>
        <div className="css-fallback">
          <div className="css-glass"></div>
        </div>
      </div>
    )
  }

  return (
    <Suspense fallback={<div className="loading">Loading 3D scene...</div>}>
      {children}
    </Suspense>
  )
}

/**
 * Main App Component
 */
function App() {
  const [params, setParams] = useState({
    ior: 1.5,
    chromaticAberration: 0.02,
    distortionScale: 0.5,
    thickness: 2,
    roughness: 0.05,
  })

  return (
    <div className="app">
      <header>
        <h1>Liquid Glass Demo</h1>
        <p>True WebGL refraction with chromatic aberration & edge distortion</p>
      </header>

      <main className="scene-container">
        <Canvas
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true }}
          className="canvas"
        >
          <PerspectiveCamera makeDefault position={[0, 0, 8]} fov={50} />
          <OrbitControls
            enablePan={false}
            minDistance={5}
            maxDistance={15}
            autoRotate
            autoRotateSpeed={0.5}
          />

          <color attach="background" args={['#0a0a0f']} />

          {/* Lighting for scene depth */}
          <ambientLight intensity={0.3} />
          <pointLight position={[10, 10, 10]} intensity={1} color="#ff6b6b" />
          <pointLight position={[-10, -10, 10]} intensity={0.8} color="#4ecdc4" />
          <pointLight position={[0, 10, -10]} intensity={0.5} color="#ffe66d" />
          <spotLight
            position={[0, 20, 5]}
            angle={0.3}
            penumbra={0.5}
            intensity={0.5}
            color="#ffffff"
          />

          <SceneLoader>
            {/* Background geometry that gets refracted */}
            <BackgroundGeometry />

            {/* Main liquid glass sphere */}
            <LiquidGlassSphere
              ior={params.ior}
              chromaticAberration={params.chromaticAberration}
              distortionScale={params.distortionScale}
              thickness={params.thickness}
              roughness={params.roughness}
              color="#ffffff"
            />

            {/* Secondary glass elements */}
            <CustomLiquidGlass
              ior={params.ior * 1.2}
              chromaticAberration={params.chromaticAberration * 1.5}
              distortionScale={params.distortionScale * 0.8}
            />
          </SceneLoader>

          <Environment preset="night" />
        </Canvas>
      </main>

      <aside className="controls-sidebar">
        <Controls params={params} setParams={setParams} />
      </aside>

      <footer>
        <p>
          Drag to rotate • Scroll to zoom • Parameters adjust in real-time
        </p>
        <p className="tech-stack">
          React Three Fiber • Three.js • GLSL Shaders
        </p>
      </footer>
    </div>
  )
}

export default App
