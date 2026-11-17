import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Float, MeshTransmissionMaterial } from '@react-three/drei'

/**
 * Main Liquid Glass Sphere with true refraction
 */
function LiquidGlassSphere({
  ior = 1.5,
  chromaticAberration = 0.08,
  distortionScale = 1.0,
  thickness = 2,
}) {
  const meshRef = useRef()

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.15
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1
    }
  })

  return (
    <Float speed={1} rotationIntensity={0.3} floatIntensity={0.2}>
      <mesh ref={meshRef} position={[0, 0, 0]}>
        <sphereGeometry args={[1.6, 128, 128]} />
        <MeshTransmissionMaterial
          backside
          backsideThickness={1}
          thickness={thickness}
          roughness={0}
          transmission={1}
          ior={ior}
          chromaticAberration={chromaticAberration}
          distortion={distortionScale}
          anisotropy={20}
          distortionScale={distortionScale}
          color="#ffffff"
          attenuationDistance={5}
          attenuationColor="#ffffff"
          clearcoat={1}
          clearcoatRoughness={0}
        />
      </mesh>
    </Float>
  )
}

/**
 * Bright grid of colorful cubes behind the glass
 */
function BackgroundCubes() {
  const groupRef = useRef()

  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.02
    }
  })

  const colors = [
    '#ff0066', '#ff6600', '#ffcc00', '#00cc66',
    '#0066ff', '#6600ff', '#ff00cc', '#00cccc'
  ]

  return (
    <group ref={groupRef}>
      {Array.from({ length: 16 }).map((_, i) => {
        const row = Math.floor(i / 4)
        const col = i % 4
        const x = (col - 1.5) * 2.2
        const y = (row - 1.5) * 2.2
        return (
          <mesh
            key={i}
            position={[x, y, -4]}
            rotation={[
              Math.sin((Date.now() / 1000) + i) * 0.3,
              Math.cos((Date.now() / 1000) + i) * 0.3,
              (i * Math.PI) / 4
            ]}
          >
            <boxGeometry args={[1, 1, 1]} />
            <meshBasicMaterial color={colors[i % colors.length]} />
          </mesh>
        )
      })}
    </group>
  )
}

/**
 * Glowing rings behind glass
 */
function BackgroundRings() {
  return (
    <group>
      {Array.from({ length: 3 }).map((_, i) => (
        <mesh
          key={i}
          position={[0, 0, -5 - i * 0.5]}
          rotation={[Math.PI / 2, 0, (i / 3) * Math.PI]}
        >
          <torusGeometry args={[3.5 - i * 0.8, 0.06, 16, 100]} />
          <meshBasicMaterial
            color={['#ff0066', '#00ccff', '#ccff00'][i]}
            toneEmitted
          />
        </mesh>
      ))}
    </group>
  )
}

/**
 * Bright colored orbs for strong refraction reference
 */
function BackgroundOrbs() {
  const orbsRef = useRef()

  useFrame((state, delta) => {
    if (orbsRef.current) {
      orbsRef.current.rotation.z -= delta * 0.03
    }
  })

  return (
    <group ref={orbsRef}>
      {Array.from({ length: 8 }).map((_, i) => {
        const angle = (i / 8) * Math.PI * 2
        const radius = 4
        return (
          <mesh
            key={i}
            position={[
              Math.cos(angle) * radius,
              Math.sin(angle) * radius * 0.8,
              -3
            ]}
          >
            <sphereGeometry args={[0.5, 32, 32]} />
            <meshBasicMaterial
              color={[
                '#ff0066', '#ff6600', '#ffcc00',
                '#00cc66', '#0066ff', '#6600ff',
                '#ff00cc', '#cc0066'
              ][i]}
              toneEmitted
            />
          </mesh>
        )
      })}
    </group>
  )
}

/**
 * Custom GLSL shader for secondary glass element
 */
const customGlassShader = {
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
      pos += normal * noise * 0.1;

      vViewPosition = cameraPosition - pos;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform float uChromaticAberration;
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

      float fresnel = pow(1.0 - abs(dot(viewDir, normal)), 3.0);

      float rOff = fbm(vUv * 5.0 + uTime * 0.1) * uChromaticAberration;
      float gOff = fbm(vUv * 5.0 + uTime * 0.1 + 0.33) * uChromaticAberration;
      float bOff = fbm(vUv * 5.0 + uTime * 0.1 + 0.66) * uChromaticAberration;

      vec3 color = uColor * (0.7 + fresnel * 0.3);
      color.r += rOff * 0.5;
      color.g += gOff * 0.4;
      color.b += bOff * 0.5;

      gl_FragColor = vec4(color, 0.95);
    }
  `,
}

function CustomGlassIcosahedron({ chromaticAberration }) {
  const materialRef = useRef()
  const meshRef = useRef()

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime
    }
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.01
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.15
    }
  })

  return (
    <Float speed={1.5} rotationIntensity={0.5} floatIntensity={0.3}>
      <mesh ref={meshRef} position={[2.5, -2, -1]}>
        <icosahedronGeometry args={[0.8, 32]} />
        <shaderMaterial
          ref={materialRef}
          vertexShader={customGlassShader.vertexShader}
          fragmentShader={customGlassShader.fragmentShader}
          uniforms={{
            uTime: { value: 0 },
            uChromaticAberration: { value: chromaticAberration },
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

export { LiquidGlassSphere, BackgroundCubes, BackgroundRings, BackgroundOrbs, CustomGlassIcosahedron }
