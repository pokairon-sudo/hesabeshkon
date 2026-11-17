import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Float, Environment, MeshTransmissionMaterial } from '@react-three/drei'

/**
 * True Liquid Glass Shader Component
 * Uses refraction, chromatic aberration, and edge distortion
 */
function LiquidGlassSphere({
  ior = 1.5,
  chromaticAberration = 0.08,
  distortionScale = 1.0,
  thickness = 2,
  roughness = 0.0,
}) {
  const meshRef = useRef()

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.2
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.15
    }
  })

  return (
    <Float speed={1.5} rotationIntensity={0.4} floatIntensity={0.3}>
      <mesh ref={meshRef} castShadow receiveShadow>
        <sphereGeometry args={[1.8, 128, 128]} />
        <MeshTransmissionMaterial
          backside
          backsideThickness={1}
          thickness={thickness}
          roughness={roughness}
          transmission={1}
          ior={ior}
          chromaticAberration={chromaticAberration}
          distortion={distortionScale}
          anisotropy={30}
          distortionScale={distortionScale}
          color="#ffffff"
          attenuationDistance={3}
          attenuationColor="#4338ca"
          clearcoat={1}
          clearcoatRoughness={0}
          samplings={3}
        />
      </mesh>
    </Float>
  )
}

/**
 * Animated cube component
 */
function Cube({ position, index }) {
  const meshRef = useRef()

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5 + index) * 0.5
      meshRef.current.rotation.y = Math.cos(state.clock.elapsedTime * 0.3 + index) * 0.5
    }
  })

  return (
    <mesh ref={meshRef} position={position}>
      <boxGeometry args={[0.8, 0.8, 0.8]} />
      <meshStandardMaterial
        color={`hsl(${index * 45 + 180}, 80%, 60%)`}
        metalness={0.9}
        roughness={0.1}
        emissive={`hsl(${index * 45 + 180}, 80%, 60%)`}
        emissiveIntensity={0.5}
      />
    </mesh>
  )
}

/**
 * Bright, high-contrast background geometry for visible refraction
 */
function BackgroundGeometry() {
  const groupRef = useRef()

  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.02
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1
    }
  })

  return (
    <group ref={groupRef}>
      {/* Bright colorful orbs behind glass */}
      {Array.from({ length: 6 }).map((_, i) => {
        const angle = (i / 6) * Math.PI * 2
        const radius = 3.5
        return (
          <mesh
            key={i}
            position={[
              Math.cos(angle) * radius,
              Math.sin(angle) * radius * 0.7,
              -2
            ]}
          >
            <sphereGeometry args={[0.6, 32, 32]} />
            <meshBasicMaterial
              color={`hsl(${i * 60}, 100%, 60%)`}
              toneEmitted
            />
          </mesh>
        )
      })}

      {/* Glowing geometric rings */}
      {Array.from({ length: 4 }).map((_, i) => (
        <mesh
          key={`ring-${i}`}
          position={[0, 0, -3 - i * 0.5]}
          rotation={[Math.PI / 2 + 0.3, 0.5, (i / 4) * Math.PI]}
        >
          <torusGeometry args={[2.5 - i * 0.5, 0.04, 16, 100]} />
          <meshBasicMaterial
            color={`hsl(${i * 90 + 30}, 100%, 70%)`}
            toneEmitted
          />
        </mesh>
      ))}

      {/* Animated cubes with metallic shine */}
      {Array.from({ length: 8 }).map((_, i) => {
        const x = ((i % 4) - 1.5) * 2.5
        const y = Math.floor(i / 4) * 2 - 0.5
        return (
          <Cube key={`cube-${i}`} position={[x, y, -4]} index={i} />
        )
      })}

      {/* Grid of bright dots */}
      {Array.from({ length: 25 }).map((_, i) => {
        const x = (i % 5 - 2) * 1.2
        const y = Math.floor(i / 5) - 2
        return (
          <mesh key={`dot-${i}`} position={[x, y, -5]}>
            <sphereGeometry args={[0.15, 16, 16]} />
            <meshBasicMaterial
              color="#ffffff"
              toneEmitted
            />
          </mesh>
        )
      })}

      {/* Large bright planes for strong refraction reference */}
      <mesh position={[0, 2.5, -4]} rotation={[0, 0, 0]}>
        <planeGeometry args={[6, 0.2]} />
        <meshBasicMaterial color="#ff6b6b" toneEmitted />
      </mesh>
      <mesh position={[0, -2.5, -4]} rotation={[0, 0, 0]}>
        <planeGeometry args={[6, 0.2]} />
        <meshBasicMaterial color="#4ecdc4" toneEmitted />
      </mesh>
      <mesh position={[3, 0, -4]} rotation={[0, Math.PI / 2, 0]}>
        <planeGeometry args={[6, 0.2]} />
        <meshBasicMaterial color="#ffe66d" toneEmitted />
      </mesh>
      <mesh position={[-3, 0, -4]} rotation={[0, Math.PI / 2, 0]}>
        <planeGeometry args={[6, 0.2]} />
        <meshBasicMaterial color="#95e1d3" toneEmitted />
      </mesh>
    </group>
  )
}

/**
 * Custom GLSL shader for liquid glass with animated FBM noise
 */
const liquidGlassShader = {
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

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

      vec3 pos = position;
      float noise = fbm(uv * 3.0 + uTime * 0.2);
      pos += normal * noise * 0.15;

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

      float fresnel = pow(1.0 - abs(dot(viewDir, normal)), 4.0);

      vec2 distortion = vec2(
        fbm(vUv * 3.0 + uTime * 0.2),
        fbm(vUv * 3.0 - uTime * 0.2)
      ) * uDistortionScale;

      float rOffset = fbm(vUv * 5.0 + uTime * 0.1) * uChromaticAberration;
      float gOffset = fbm(vUv * 5.0 + uTime * 0.1 + 0.5) * uChromaticAberration;
      float bOffset = fbm(vUv * 5.0 + uTime * 0.1 + 1.0) * uChromaticAberration;

      vec3 refracted = uColor * (0.7 + fresnel * 0.3);
      refracted.r += rOffset * 0.4;
      refracted.g += gOffset * 0.3;
      refracted.b += bOffset * 0.4;
      refracted *= 1.0 + (uIor - 1.0) * 0.25;
      refracted += fresnel * vec3(rOffset, gOffset, bOffset) * 0.5;

      gl_FragColor = vec4(refracted, 0.98);
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
      meshRef.current.rotation.y += 0.008
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.1
    }
  })

  return (
    <Float speed={1} rotationIntensity={0.3} floatIntensity={0.2}>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.4, 50]} />
        <shaderMaterial
          ref={materialRef}
          fragmentShader={liquidGlassShader.fragmentShader}
          vertexShader={liquidGlassShader.vertexShader}
          uniforms={{
            uTime: { value: 0 },
            uIor: { value: ior * 1.1 },
            uChromaticAberration: { value: chromaticAberration * 1.2 },
            uDistortionScale: { value: distortionScale * 0.8 },
            uColor: { value: new THREE.Color('#c7d2fe') },
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
