import { useRef, useMemo, Suspense } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Float, MeshTransmissionMaterial } from '@react-three/drei'

/**
 * True Liquid Glass Shader Component
 * Uses refraction, chromatic aberration, and edge distortion
 * to simulate realistic Apple-style material glass
 */
function LiquidGlassSphere({
  ior = 1.5,
  chromaticAberration = 0.02,
  distortionScale = 0.5,
  thickness = 2,
  color = '#ffffff',
  roughness = 0.05,
  transmission = 1,
}) {
  const meshRef = useRef()
  const materialRef = useRef()

  // Animate subtle rotation
  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.1
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.1
    }
  })

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
      <mesh ref={meshRef} castShadow receiveShadow>
        <sphereGeometry args={[1.5, 64, 64]} />
        <MeshTransmissionMaterial
          ref={materialRef}
          backside
          backsideThickness={0.5}
          thickness={thickness}
          roughness={roughness}
          transmission={transmission}
          ior={ior}
          chromaticAberration={chromaticAberration}
          distortion={distortionScale}
          anisotropy={20}
          distortionScale={distortionScale}
          color={color}
          attenuationDistance={5}
          attenuationColor={0x4444ff}
          clearcoat={1}
          clearcoatRoughness={0.05}
        />
      </mesh>
    </Float>
  )
}

/**
 * Background geometry that gets refracted through the glass
 */
function BackgroundGeometry() {
  const gridRef = useRef()

  useFrame((state, delta) => {
    if (gridRef.current) {
      gridRef.current.rotation.z += delta * 0.05
    }
  })

  return (
    <group ref={gridRef}>
      {/* Glowing geometric patterns */}
      {Array.from({ length: 8 }).map((_, i) => (
        <mesh
          key={i}
          rotation={[Math.PI / 4, (i / 8) * Math.PI * 2, 0]}
          position={[
            Math.cos((i / 8) * Math.PI * 2) * 5,
            Math.sin((i / 8) * Math.PI * 2) * 5,
            -2,
          ]}
        >
          <torusGeometry args={[0.3, 0.08, 16, 32]} />
          <meshStandardMaterial
            emissive={`hsl(${(i * 45) % 360}, 100%, 50%)`}
            emissiveIntensity={2}
            toneEmitted
          />
        </mesh>
      ))}

      {/* Floating cubes */}
      {Array.from({ length: 12 }).map((_, i) => (
        <mesh
          key={`cube-${i}`}
          position={[
            (i % 4 - 1.5) * 3,
            Math.floor(i / 4) * 2 - 1,
            -3 - Math.random() * 3,
          ]}
          rotation={[
            (i * 0.5) % Math.PI,
            (i * 0.3) % Math.PI,
            0,
          ]}
        >
          <boxGeometry args={[0.5, 0.5, 0.5]} />
          <meshStandardMaterial
            color={`hsl(${(i * 30 + 180) % 360}, 70%, 60%)`}
            metalness={0.8}
            roughness={0.2}
          />
        </mesh>
      ))}

      {/* Text-like planes with high contrast */}
      <mesh position={[0, 0, -5]} rotation={[0, 0.2, 0]}>
        <planeGeometry args={[6, 1]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <mesh position={[-2.5, -1.5, -4]}>
        <planeGeometry args={[4, 1]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <mesh position={[2.5, -1.5, -4]}>
        <planeGeometry args={[4, 1]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>

      {/* Chromatic edge rings */}
      {Array.from({ length: 3 }).map((_, i) => (
        <mesh
          key={`ring-${i}`}
          position={[0, 0, -6 + i * 0.5]}
          rotation={[Math.PI / 2, 0, (i / 3) * Math.PI]}
        >
          <torusGeometry args={[4 + i * 0.5, 0.02, 8, 64]} />
          <meshBasicMaterial
            color={`hsl(${i * 120}, 100%, 70%)`}
            transparent
            opacity={0.3}
          />
        </mesh>
      ))}
    </group>
  )
}

/**
 * Custom GLSL shader material for advanced liquid glass effect
 * Includes: FBM noise, refraction, chromatic aberration, edge distortion
 */
const liquidGlassShader = {
  uniforms: {
    uTime: { value: 0 },
    uIor: { value: 1.5 },
    uChromaticAberration: { value: 0.02 },
    uDistortionScale: { value: 0.5 },
    uColor: { value: new THREE.Color('#ffffff') },
  },
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    // FBM noise for liquid flow
    float random(vec2 st) {
      return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
    }

    float fbm(vec2 st) {
      float value = 0.0;
      float amplitude = 0.5;
      for (int i = 0; i < 5; i++) {
        value += amplitude * random(st);
        st *= 2.0;
        amplitude *= 0.5;
      }
      return value;
    }

    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);

      // Subtle vertex displacement for liquid effect
      vec3 pos = position;
      float noise = fbm(uv * 3.0 + uTime * 0.2);
      pos += normal * noise * uDistortionScale * 0.1;

      vViewPosition = cameraPosition - pos;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform float uIor;
    uniform float uChromaticAberration;
    uniform float uDistortionScale;
    uniform vec3 uColor;

    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    // FBM for liquid distortion
    float random(vec2 st) {
      return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
    }

    float fbm(vec2 st) {
      float value = 0.0;
      float amplitude = 0.5;
      for (int i = 0; i < 5; i++) {
        value += amplitude * random(st);
        st *= 2.0;
        amplitude *= 0.5;
      }
      return value;
    }

    void main() {
      vec3 viewDir = normalize(vViewPosition);
      vec3 normal = normalize(vNormal);

      // Fresnel effect for edge glow
      float fresnel = pow(1.0 - abs(dot(viewDir, normal)), 3.0);

      // Simulate refraction offset per channel (chromatic aberration)
      vec2 distortion = vec2(
        fbm(vUv * 3.0 + uTime * 0.2),
        fbm(vUv * 3.0 - uTime * 0.2)
      ) * uDistortionScale;

      // Chromatic aberration: offset RGB channels
      float rOffset = fbm(vUv * 5.0 + uTime * 0.1) * uChromaticAberration;
      float gOffset = fbm(vUv * 5.0 + uTime * 0.1 + 0.5) * uChromaticAberration;
      float bOffset = fbm(vUv * 5.0 + uTime * 0.1 + 1.0) * uChromaticAberration;

      // Base refracted color (simplified - in production, sample actual scene)
      vec3 refracted = uColor * (0.8 + fresnel * 0.2);

      // Add chromatic edges
      refracted.r += rOffset * 0.3;
      refracted.g += gOffset * 0.2;
      refracted.b += bOffset * 0.3;

      // IOR affects transmission depth
      refracted *= 1.0 + (uIor - 1.0) * 0.2;

      // Edge distortion glow
      refracted += fresnel * distortion.x * 0.1;

      gl_FragColor = vec4(refracted, 0.95);
    }
  `,
}

function CustomLiquidGlass({ ior, chromaticAberration, distortionScale }) {
  const materialRef = useRef()
  const meshRef = useRef()

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime
    }
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005
    }
  })

  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.3}>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.2, 4]} />
        <shaderMaterial
          ref={materialRef}
          fragmentShader={liquidGlassShader.fragmentShader}
          vertexShader={liquidGlassShader.vertexShader}
          uniforms={{
            uTime: { value: 0 },
            uIor: { value: ior },
            uChromaticAberration: { value: chromaticAberration },
            uDistortionScale: { value: distortionScale },
            uColor: { value: new THREE.Color('#e0e7ff') },
          }}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </Float>
  )
}

export { LiquidGlassSphere, BackgroundGeometry, CustomLiquidGlass }
