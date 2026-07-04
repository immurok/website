// IK-1 3D Preview — Three.js
// - Loads design-v2.glb (converted from STEP)
// - Applies PBR materials for anodized aluminum / black plastic / PCB / sensor glass
// - Provides a 360° OrbitControls camera with zoom + pan
// - Switches between assembled and exploded views with eased animation
// - Reads ?debug=1 query to show a small overlay with stats

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const QUERY = new URLSearchParams(location.search);
const DEBUG = QUERY.get('debug') === '1';
const CAPTURE = QUERY.get('capture') === '1';
if (DEBUG) document.body.classList.add('debug-on');
if (CAPTURE) document.body.classList.add('capture-on');

// ---------------------------- scene setup ----------------------------
const viewport = document.getElementById('viewport');

const scene = new THREE.Scene();
// In capture mode use a chroma-key magenta so check.py can cleanly
// extract the product silhouette even when the aluminum top face
// renders near-pure-white.
scene.background = CAPTURE ? new THREE.Color(1.0, 0.0, 1.0) : null;

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: CAPTURE, // needed for clean readPixels during screenshot
  powerPreference: 'high-performance',
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
viewport.appendChild(renderer.domElement);

const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 1000);
camera.position.set(85, 70, 105); // will be re-aimed after model load

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.rotateSpeed = 0.9;
controls.zoomSpeed = 0.9;
controls.enablePan = false;           // device stays locked on screen centre
controls.screenSpacePanning = false;
controls.minDistance = 30;
controls.maxDistance = 300;

// ---------------------------- environment ----------------------------
// Procedural studio environment (RoomEnvironment) — gives nice reflections
// for metallic surfaces without shipping a heavy HDR file.
const pmrem = new THREE.PMREMGenerator(renderer);
pmrem.compileEquirectangularShader();
const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environment = envTex;

// Soft three-point lighting on top of env. Kept fairly subtle so the
// environment map (which gives the "studio softbox overhead" highlights on
// the metallic top edge) is the dominant lighting cue.
const keyLight = new THREE.DirectionalLight(0xffffff, 1.15);
keyLight.position.set(45, 120, 55);  // higher overhead for stronger top-edge highlight
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(2048, 2048);
keyLight.shadow.camera.near = 1;
keyLight.shadow.camera.far  = 400;
keyLight.shadow.camera.left = -80;
keyLight.shadow.camera.right = 80;
keyLight.shadow.camera.top = 80;
keyLight.shadow.camera.bottom = -80;
keyLight.shadow.bias = -0.0002;
keyLight.shadow.normalBias = 0.04;
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0xc4d2ff, 0.18);
fillLight.position.set(-90, 30, -40);
scene.add(fillLight);

const rimLight = new THREE.DirectionalLight(0xffd9aa, 0.15);
rimLight.position.set(0, -40, -90);
scene.add(rimLight);

scene.add(new THREE.AmbientLight(0xffffff, 0.06));

// No ground plane — the model floats freely. (A ShadowMaterial plane caused
// a visible black square between the PCB and the bottom shell once the
// assembly was exploded, since the plane stays put while parts move.)

// ---------------------------- materials ----------------------------
// Two color variants of the anodized aluminum housing
const aluminumMats = {
  silver: new THREE.MeshPhysicalMaterial({
    color: 0xe2e3e6,            // bright satin aluminum (close to anodized natural)
    metalness: 1.0,
    roughness: 0.34,
    envMapIntensity: 1.25,
    clearcoat: 0.05,
    clearcoatRoughness: 0.5,
  }),
  'space-gray': new THREE.MeshPhysicalMaterial({
    color: 0xacaeb1,            // brighter mid-gray so anodized highlights read close to reference photos
    metalness: 1.0,
    roughness: 0.38,
    envMapIntensity: 1.35,
    clearcoat: 0.04,
    clearcoatRoughness: 0.55,
  }),
};

const blackPlasticMat = new THREE.MeshPhysicalMaterial({
  color: 0x111114, metalness: 0.0, roughness: 0.62, envMapIntensity: 0.7,
  side: THREE.DoubleSide, // STEP mesh normals point into the cavity — render both sides so the inside-top face is opaque from above too
});

// Procedural bottom-label texture: FCC / Bluetooth / CE / model / SN
// markings, plus a small green LED dot — drawn into a canvas and
// applied to the bottom disc so bottom-up renders look populated
// rather than featureless black.
function makeBottomLabelTexture() {
  const cv = document.createElement('canvas');
  cv.width = cv.height = 1024;
  const ctx = cv.getContext('2d');
  // black background
  ctx.fillStyle = '#0d0e10';
  ctx.fillRect(0, 0, 1024, 1024);

  const cx = 512, cy = 512;

  // Concentric inset disc (slightly darker)
  ctx.fillStyle = '#080808';
  ctx.beginPath();
  ctx.arc(cx, cy, 430, 0, Math.PI * 2);
  ctx.fill();

  // White / light-gray text rotated around centre — mimics the photo where
  // the model / serial-number ring runs along the disc edge.
  ctx.fillStyle = '#d3d3d4';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const texts = [
    'Model: immurok IK-1',
    'SN: K26010001',
    'Input: 5V⎓ 500mA',
    'FCC ID: XXX-XXXX',
    'CMIIT ID: 2026DPXXXX',
    'Made in China',
  ];
  for (let i = 0; i < texts.length; i++) {
    ctx.save();
    const a = (i / texts.length) * Math.PI * 2;
    ctx.translate(cx, cy);
    ctx.rotate(a);
    ctx.translate(0, -380);
    ctx.rotate(Math.PI / 2);
    ctx.fillText(texts[i], 0, 0);
    ctx.restore();
  }

  // FCC mark
  ctx.fillStyle = '#dddddd';
  ctx.font = '900 110px serif';
  ctx.fillText('FC', cx - 12, cy - 30);

  // CE
  ctx.font = '900 90px serif';
  ctx.fillText('CE', cx - 110, cy);

  // Bluetooth glyph (stylised B)
  ctx.font = '900 80px sans-serif';
  ctx.fillText('B', cx - 130, cy + 80);

  // Reset button hole
  ctx.fillStyle = '#1f1f1f';
  ctx.beginPath();
  ctx.arc(cx + 160, cy + 90, 22, 0, Math.PI * 2);
  ctx.fill();

  // Green status LED dot
  ctx.fillStyle = '#46c44a';
  ctx.beginPath();
  ctx.arc(cx + 120, cy - 35, 14, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = 'rgba(220,255,210,0.7)';
  ctx.beginPath();
  ctx.arc(cx + 116, cy - 39, 5, 0, Math.PI * 2);
  ctx.fill();

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}
const bottomLabelTex = makeBottomLabelTexture();
const bottomLabelMat = new THREE.MeshPhysicalMaterial({
  map: bottomLabelTex,
  metalness: 0.0,
  roughness: 0.62,
  envMapIntensity: 0.7,
});
const sensorGlassMat = new THREE.MeshPhysicalMaterial({
  color: 0x1a1c20, metalness: 0.0, roughness: 0.08,
  transmission: 0.0, ior: 1.5, envMapIntensity: 1.3,
  clearcoat: 1.0, clearcoatRoughness: 0.04,
});
const sensorRingMat = new THREE.MeshPhysicalMaterial({
  color: 0xe2e3e5, metalness: 1.0, roughness: 0.28, envMapIntensity: 1.2,
});
// PCB look matched to PCB参考图: solder mask is a deep saturated blue with
// a subtle satin sheen, exposed copper pads / castellations are warm gold,
// and the green-paint silkscreen-free PCB substrate edge is matte tan/beige.
const pcbMat = new THREE.MeshPhysicalMaterial({
  color: 0x143b8a, metalness: 0.1, roughness: 0.5, envMapIntensity: 0.85,
  clearcoat: 0.25, clearcoatRoughness: 0.4,            // solder mask is slightly glossy
});
const pcbGoldEdgeMat = new THREE.MeshPhysicalMaterial({
  color: 0xd4ad55, metalness: 0.85, roughness: 0.35, envMapIntensity: 1.0,
});
// Bare-substrate edge (the tan stripe along the PCB outline in the refs)
const pcbSubstrateMat = new THREE.MeshPhysicalMaterial({
  color: 0xb19551, metalness: 0.0, roughness: 0.7, envMapIntensity: 0.5,
});
// Big mounting screws: black-anodised / black oxide finish (the ones that
// hold the housing together — visible at the 4 corners of the bottom shell).
const screwMat = new THREE.MeshPhysicalMaterial({
  color: 0x1a1b1d, metalness: 1.0, roughness: 0.42, envMapIntensity: 0.9,
});
// The USB-C port is mostly the CAVITY we see through — give it a darker
// look so it reads as a recess rather than a bright stub.
const connectorMetalMat = new THREE.MeshPhysicalMaterial({
  color: 0x32343a, metalness: 0.85, roughness: 0.45, envMapIntensity: 0.7,
});
const ledLensMat = new THREE.MeshPhysicalMaterial({
  color: 0xffffff, metalness: 0.0, roughness: 0.25,
  emissive: 0xffffff, emissiveIntensity: 0.85, // tiny indicator pill — glows bright in product photos
  envMapIntensity: 0.7,
});
const componentMat = new THREE.MeshPhysicalMaterial({
  color: 0x1c1c20, metalness: 0.3, roughness: 0.55, envMapIntensity: 0.6,
});

// PCB component palette — colours sampled from the EasyEDA MTL file
// (PCB参考图/3D_PCB6-4_2026-05-23.mtl). Refdes-based assignment uses the
// component-name prefix in the STEP file (e.g. "R11~R0201~…", "USB1~…",
// "U6~VQFN-28…", "LED2~LED-SMD_FM-…", "Board", "TopCopper", "TopFpcStiffener").

// PCB substrate — darker EasyEDA blue (user feedback: previous 0x0383d1 too bright)
const pcbBoardMat = new THREE.MeshPhysicalMaterial({
  color: 0x0a4895, metalness: 0.05, roughness: 0.45, envMapIntensity: 0.85,
  clearcoat: 0.25, clearcoatRoughness: 0.4,
});
// Exposed copper / castellation pads (mtl27: 0.97, 0.88, 0.60) — pale gold
const pcbPadGoldMat = new THREE.MeshPhysicalMaterial({
  color: 0xf7e09a, metalness: 0.85, roughness: 0.35, envMapIntensity: 1.0,
});
// Bright gold connector pins (used INSIDE white plastic connectors —
// e.g. U1 / CN1 — the pins facing into the socket are bare brass/gold).
const connectorPinGoldMat = new THREE.MeshPhysicalMaterial({
  color: 0xe6b34a, metalness: 0.9, roughness: 0.32, envMapIntensity: 1.05,
});
// Gray tinted glass LED light pipe — fully transparent with refraction.
const lightPipeMat = new THREE.MeshPhysicalMaterial({
  color: 0xb4b6ba,                 // gray tint
  metalness: 0.0,
  roughness: 0.02,                 // polished glass
  transmission: 1.0,               // full refractive transparency
  ior: 1.52,                       // window-glass / acrylic
  thickness: 0.6,
  attenuationColor: 0xc8cad0,
  attenuationDistance: 5,
  clearcoat: 1.0, clearcoatRoughness: 0.02,
  envMapIntensity: 1.2,
  transparent: true,
  side: THREE.DoubleSide,
});
// Insulated power wire — red (+) and black (−)
const wirePosMat = new THREE.MeshPhysicalMaterial({
  color: 0xb52121, metalness: 0.0, roughness: 0.55, envMapIntensity: 0.5,
});
const wireNegMat = new THREE.MeshPhysicalMaterial({
  color: 0x0c0c0e, metalness: 0.0, roughness: 0.55, envMapIntensity: 0.5,
});
// FPC stiffener — tan FR-4 substrate (mtl37: 0.62, 0.62, 0.36)
const fpcStiffenerMat = new THREE.MeshPhysicalMaterial({
  color: 0x9e9c5b, metalness: 0.0, roughness: 0.6, envMapIntensity: 0.55,
});

// PCB silkscreen / pad textures applied to the Board substrate's top and
// bottom faces. Loaded once and re-used for the 2-material Board split.
const _texLoader = new THREE.TextureLoader();
function loadPcbFaceTex(url) {
  const t = _texLoader.load(url);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy  = 8;
  t.wrapS = THREE.ClampToEdgeWrapping;
  t.wrapT = THREE.ClampToEdgeWrapping;
  t.flipY = true;
  return t;
}
const pcbTopTex    = loadPcbFaceTex('./up.png');
const pcbBottomTex = loadPcbFaceTex('./down.png');
const pcbTopMat = new THREE.MeshStandardMaterial({
  map: pcbTopTex, metalness: 0.0, roughness: 0.55, envMapIntensity: 0.7,
});
const pcbBottomMat = new THREE.MeshStandardMaterial({
  map: pcbBottomTex, metalness: 0.0, roughness: 0.55, envMapIntensity: 0.7,
});

// Black IC body (matte epoxy)
const chipBlackMat = new THREE.MeshPhysicalMaterial({
  color: 0x141414, metalness: 0.05, roughness: 0.55, envMapIntensity: 0.5,
});
// Bright silver lead frames / pins / pads / contacts.
// Pins are tiny so reflections often don't fall on them; keep metalness
// high but raise the base colour and env intensity so they read as silver
// regardless of viewing angle.
const chipLeadMat = new THREE.MeshPhysicalMaterial({
  color: 0xeaebee, metalness: 0.85, roughness: 0.28, envMapIntensity: 1.4,
});
// USB-C shell / crystal can — bright chrome (mtl15: 0.9)
const connectorChromeMat = new THREE.MeshPhysicalMaterial({
  color: 0xcfd0d3, metalness: 1.0, roughness: 0.28, envMapIntensity: 1.15,
});
// White plastic — SW2 slide switch body (mtl3: 1, 1, 1)
const plasticWhiteMat = new THREE.MeshPhysicalMaterial({
  color: 0xf0f0ee, metalness: 0.0, roughness: 0.5, envMapIntensity: 0.6,
});
// Ceramic SMD capacitor — tan body (mtl31/mtl34 family, peach/cream)
const ceramicCapTanMat = new THREE.MeshPhysicalMaterial({
  color: 0xc9a87a, metalness: 0.05, roughness: 0.55, envMapIntensity: 0.55,
});
// SMD resistor — black/dark grey body
const smdResistorBodyMat = new THREE.MeshPhysicalMaterial({
  color: 0x1a1a1c, metalness: 0.05, roughness: 0.55, envMapIntensity: 0.5,
});
// LED dome — bright white, mildly emissive
const ledDomeMat = new THREE.MeshPhysicalMaterial({
  color: 0xfff4cc, metalness: 0.0, roughness: 0.25,
  emissive: 0xfff4cc, emissiveIntensity: 0.25, envMapIntensity: 0.9,
});
// Diode body — small black/glass
const diodeBodyMat = new THREE.MeshPhysicalMaterial({
  color: 0x16161a, metalness: 0.1, roughness: 0.4, envMapIntensity: 0.7,
});
// Inductor body
const inductorBodyMat = new THREE.MeshPhysicalMaterial({
  color: 0x232325, metalness: 0.2, roughness: 0.55, envMapIntensity: 0.55,
});
// Antenna pad — pale yellow PCB-trace look (mtl37 tone)
const antennaPadMat = new THREE.MeshPhysicalMaterial({
  color: 0xc9b25a, metalness: 0.5, roughness: 0.45, envMapIntensity: 0.7,
});
// Silver-gray pouch-cell ("软包") battery — aluminised mylar foil look.
const batteryPouchMat = new THREE.MeshPhysicalMaterial({
  color: 0xa8a9ad, metalness: 0.7, roughness: 0.38, envMapIntensity: 1.0,
  clearcoat: 0.2, clearcoatRoughness: 0.45,
});

// Top-level part name → category (used for material assignment & explode layer)
// Sizes / observations from build/assembly-tree.json:
//   PRT0001_12  44×44×11.5   → outer aluminum body (top shell + ring in one)
//   PRT0002_10  40.9×40.9×6.0 → black plastic bottom cavity / battery cover
//   PRT0003_6   3.5×6.8×7.1   → side push button (reset)
//   PRT0004_3   32.9×32.9×1.0 → top label / sticker disc
//   PRT0005_8   4.8×9.2×5.0   → USB-C female metal shell
//   PRT0006_7   5.8×5.7×3.1   → side LED light pipe / micro-switch
//   2_3_ASM     17.4×17.5×5.2 → fingerprint sensor module (with glass)
//   ASM0001_…   4.0×8.5×0.1   → adhesive label
//   FPC_ASM     9.0×17.4×4.4  → FPC ribbon connector
//   M2X3X4      4×4×3.5       → M2 screw
//   PRT0001     5×5×0.5       → flat washer
//   1_5         4×4×2.5       → small standoff
//   280         4×4×8.0       → tall standoff / battery post
//   DC          12×20×6.0     → battery / DC pack
//   3D_PCB5_NOCU_V2_ASM 38.9×39.5×6.9 → PCB sub-assembly (223 child meshes)
// Three-tier vertical explode (in mm, +Y is up):
//   TOP    (+22): aluminum housing assembly — shell + sensor + top label
//   MIDDLE (  0): PCB and electronics that ride with the board
//   BOTTOM (-22): black plastic cavity + bottom disc + screws + standoffs
const LAYER_TOP    =  22;
const LAYER_PCB    =   2;   // PCB lifted just a hair to separate from the plastic shell
const LAYER_BOTTOM = -12;   // tighter gap between PCB and bottom shell
const LAYER_HARDWARE = -32; // screws & washers pulled further down than the shell

const PART_RULES = [
  // TOP — aluminum housing assembly
  { match: n => n === 'PRT0001_12',          cat: 'shell-alu',     layer: LAYER_TOP    }, // main 44×44×11.5 anodized-aluminum body
  { match: n => n === '2_3_ASM',             cat: 'sensor',        layer: LAYER_TOP    }, // fingerprint sensor module (rides with shell)
  // ASM0001_ASM_1_ASM is a 0.1 mm-thick disc that floats inside the alu
  // shell — hide it (it was an adhesive-pad placeholder, not a visible part).
  { match: n => n === 'ASM0001_ASM_1_ASM',   cat: 'hidden-label',  layer: LAYER_TOP    },

  // MIDDLE — PCB and the components mounted on / poking through it
  { match: n => n === '3D_PCB5_NOCU_V2_ASM', cat: 'pcb',           layer: LAYER_PCB    },
  // FPC_ASM (black ribbon cable) hidden per design intent — sensor connects
  // directly to the PCB through-hole now.
  { match: n => n === 'FPC_ASM',             cat: 'hidden-fpc',    layer: LAYER_PCB    },
  // PRT0005_8 and PRT0006_7 are the 2 black-plastic buttons (front/back of
  // the device, at ±Y). In explode they sit at the geometric midpoint
  // between PCB and the bottom plastic shell.
  { match: n => n === 'PRT0005_8',           cat: 'mid-button',    layer: (LAYER_PCB + LAYER_BOTTOM) / 2 },
  { match: n => n === 'PRT0006_7',           cat: 'mid-button',    layer: (LAYER_PCB + LAYER_BOTTOM) / 2 },
  { match: n => n === 'PRT0003_6',           cat: 'light-pipe',    layer: LAYER_PCB    }, // L-shaped white translucent LED light guide (3.5×6.8×7.1)
  { match: n => n === 'DC',                  cat: 'battery',       layer: LAYER_PCB    }, // battery / DC pack

  // BOTTOM — black plastic shell + label disc
  { match: n => n === 'PRT0002_10',          cat: 'cavity-plastic',layer: LAYER_BOTTOM }, // 40.9×40.9×6 black-plastic bottom cavity
  { match: n => n === 'PRT0004_3',           cat: 'bottom-disc',   layer: LAYER_BOTTOM }, // 32×32×1 FCC-label disc

  // HARDWARE
  // M2X3X4 internal mounting screws — hidden
  { match: n => n === 'M2X3X4',              cat: 'hidden-screw',  layer: LAYER_HARDWARE },
  // PRT0001 (washers) + 1_5 (standoffs) are internal fasteners — hidden.
  { match: n => n === 'PRT0001',             cat: 'hidden-washer', layer: LAYER_HARDWARE },
  { match: n => n === '1_5',                 cat: 'hidden-standoff', layer: LAYER_HARDWARE },
  // 4 corner "280" posts = the big black-metal corner screws visible on
  // the bottom of the housing. In explode they drop BELOW the bottom shell.
  { match: n => n === '280',                 cat: 'corner-screw',  layer: LAYER_BOTTOM - 14 },
];

function ruleFor(name) {
  // Drop a trailing _N suffix added by GLTFLoader to disambiguate duplicate
  // sibling names (e.g. four "280" standoffs become 280, 280_1, 280_2, 280_3).
  const base = name.replace(/_\d+$/, '');
  for (const r of PART_RULES) if (r.match(name) || r.match(base)) return r;
  return null;
}

// Decide material from category + per-mesh attributes
function materialFor(cat, mesh, parentColor) {
  switch (cat) {
    case 'shell-alu':           // aluminum body
      return aluminumMats[currentVariant];
    case 'cavity-plastic':      // black plastic bottom cavity
      return blackPlasticMat;
    case 'bottom-disc':
      return blackPlasticMat;     // black plastic disc (real product has FCC/SN decals not modelled)
    case 'sensor':        return sensorGlassMat;
    case 'label':         return blackPlasticMat;
    case 'light-pipe':    return lightPipeMat;        // PRT0003_6 — gray-white translucent LED guide
    case 'corner-screw':  return screwMat;             // black metal finish for the 4 visible corner screws
    case 'mid-button':    return blackPlasticMat;      // PRT0005_8 + PRT0006_7 — black-plastic buttons at PCB↔bottom midpoint
    case 'hidden-screw':
    case 'hidden-washer':
    case 'hidden-standoff':
    case 'hidden-fpc':
    case 'hidden-label':  return null;                // signal to skip (mesh.visible=false)
    case 'battery':       return batteryPouchMat;
    case 'pcb':           return pcbForSubMesh(mesh, parentColor);
  }
  return null;
}

// Material chooser for PCB sub-meshes.
//
// STEP file is colourless (all 223 PCB sub-meshes share the default 0.85
// grey) so we classify by *geometry*. The dimensions in mm match the BOM
// observed in PCB参考图: USB-C female (vol ≈ 250), FFC + slide switch
// (white plastic, vol 100-160), tactile button (~5mm cube), MCU QFN
// (~4mm flat square), and many micro-SMD passives / pads.
function pcbForSubMesh(mesh, parentColor) {
  const g = mesh.geometry;
  if (!g.boundingBox) g.computeBoundingBox();
  const bb = g.boundingBox;
  const sx = bb.max.x - bb.min.x;
  const sy = bb.max.y - bb.min.y;
  const sz = bb.max.z - bb.min.z;
  const dims = [sx, sy, sz].sort((a, b) => a - b);  // ascending
  const thin = dims[0], mid = dims[1], lng = dims[2];
  const vol  = sx * sy * sz;

  // 1. Exposed copper pads / lead frames — extremely thin patches
  if (thin < 0.12 && lng < 2.5)   return chipLeadMat;       // tiny silver pads / leads
  if (thin < 0.12)                 return pcbGoldEdgeMat;    // larger gold pads

  // 2. PCB substrate — thin, very wide
  if (thin <= 1.5 && lng >= 25)   return pcbMat;            // the board itself

  // 3. USB-C female shell — biggest non-board single component
  if (vol > 180 && lng > 9)       return connectorChromeMat; // silver chrome

  // 4. White-plastic connector bodies (FFC connector, slide switch) —
  //    moderately large, longer than wide, not too thick.
  if (vol >= 25 && lng >= 5 && thin <= 3.5 && lng / mid > 1.2)
    return plasticWhiteMat;

  // 5. Tactile button — roughly cube-shaped, ~3-5 mm per side
  if (lng >= 3 && lng <= 5.5 && thin >= 1.5 && mid / thin < 2.2)
    return chipBlackMat;          // button base (silver actuator caught by #1)

  // 6. MCU / QFN package — flat square, 3-5 mm side, < 1.5 mm thick
  if (lng >= 3 && lng <= 6 && thin < 1.5 && Math.abs(mid - lng) / lng < 0.25)
    return chipBlackMat;

  // 7. Crystal can — small silver cylinder/rectangle
  if (lng >= 2 && lng <= 4 && mid >= 1.5 && thin >= 0.8 && lng / mid < 2.0 && vol > 5)
    return connectorChromeMat;

  // 8. SMD passives — tiny rectangles
  if (lng <= 2.0)                  return smdResistorBodyMat;

  // 9. Anything else (medium 2-3 mm components) → dark plastic
  if (lng <= 3.5)                  return componentMat;

  // Fallback: PCB blue
  return pcbMat;
}

// ---------------------------- loading ----------------------------
let model;             // pivot Group holding the assembly, kept centred at world origin
let topParts = [];     // top-level child groups (the categorised parts)
let LOCAL_WORLD_UP = new THREE.Vector3(0, 1, 0); // world-up expressed in asm-local space; filled in once the model loads
// World-space horizontal direction the camera should look FROM for each
// canonical preset. Filled in after the model loads, based on the actual
// position of the USB-C port (front) and LED (side).
const FRONT_DIR = new THREE.Vector3(0, 0, 1);
const SIDE_DIR  = new THREE.Vector3(1, 0, 0);
let currentVariant = 'silver';
let explodeT = 0;      // 0 = assembled, 1 = fully exploded
let targetT = 0;
const PCB_GROUP_COLOR_BY_GLB_MAT = new WeakMap();

const loadingEl = document.getElementById('loading');
const debugEl = document.getElementById('debug');
function dbg(...lines) {
  if (!DEBUG) return;
  debugEl.innerText = lines.join('\n');
}

// Draco-compressed GLBs need a decoder. Three.js ships one (~ 750 KB total,
// loaded async on first GLB) — we serve a copy from ./draco/.
const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('./draco/');

const loader = new GLTFLoader();
loader.setDRACOLoader(dracoLoader);

// design-v2.glb is the hybrid GLB built by tools/hybrid-glb.mjs: fine
// tessellation everywhere EXCEPT PRT0002_10 (bottom cavity), which keeps
// the older coarse mesh — fine tessellation didn't help that part visually.
// Both design-v2.glb and design-pcb.glb are Draco-compressed (see tools/compress-glbs.sh).
loader.load(
  './design-v2.glb',
  (gltf) => onModel(gltf.scene),
  (xhr) => {
    if (xhr.lengthComputable) {
      const pct = Math.round(xhr.loaded / xhr.total * 100);
      loadingEl.querySelector('.label').textContent = `Loading model … ${pct}%`;
    }
  },
  (err) => {
    console.error(err);
    loadingEl.querySelector('.label').textContent = 'Failed to load model — see console';
  }
);

function onModel(root) {
  // model is set to the pivot Group once we create it below

  // First: cache the original material colors before we replace them,
  // so PCB classification can still inspect "what color was this in the GLB".
  root.traverse(o => {
    if (o.isMesh && o.material) {
      PCB_GROUP_COLOR_BY_GLB_MAT.set(o, o.material.color.clone());
    }
  });

  // Walk: descend through single-child wrapper nodes until we find the node
  // whose children are the real top-level parts (e.g. '000-ZHIWEN_20260330_ASM'
  // sits below an unnamed wrapper after the gltf-transform round-trip).
  let asm = root;
  while (asm.children.length === 1 && asm.children[0].children.length > 0) {
    asm = asm.children[0];
  }
  console.log('[ik1] assembly root:', asm.name || '(unnamed)', 'children:', asm.children.length);

  for (const child of [...asm.children]) {
    const rule = ruleFor(child.name);
    child.userData.rule = rule;
    child.userData.cat  = rule?.cat || 'misc';
    child.userData.layer = rule?.layer ?? 0;
    topParts.push(child);

    // Hidden categories: remove the whole part from rendering & layout.
    const isHidden = String(child.userData.cat).startsWith('hidden-');
    if (isHidden) {
      child.visible = false;
    }

    // The pouch cell STEP body comes out at 6 mm tall — visually too tall
    // for the housing once you account for the wrap; flatten on the
    // asm-local Z axis (= world-up after the pivot rotation).
    if (child.userData.cat === 'battery') {
      child.scale.z = 0.66;        // ≈ 4 mm visible height
    }

    let meshCount = 0;
    child.traverse(o => {
      if (!o.isMesh) return;
      meshCount++;
      o.castShadow = true;
      o.receiveShadow = true;
      const parentColor = PCB_GROUP_COLOR_BY_GLB_MAT.get(o);
      if (isHidden) return;
      let mat = materialFor(child.userData.cat, o, parentColor) || o.material;
      // Sensor sub-assembly 2_3_ASM has two ~8.4×5×3 mm FFC connector
      // sub-meshes (mesh_7 + mesh_9) — paint those white plastic instead
      // of the sensor glass material.
      if (child.userData.cat === 'sensor') {
        const g = o.geometry;
        if (!g.boundingBox) g.computeBoundingBox();
        const bb = g.boundingBox;
        const vol = (bb.max.x-bb.min.x) * (bb.max.y-bb.min.y) * (bb.max.z-bb.min.z);
        if (vol > 50 && vol < 200) mat = plasticWhiteMat;
      }
      o.material = mat;

      // For the bottom disc, the STEP file carries no UVs — generate a
      // planar projection from below so the label texture wraps the disc.
      if (child.userData.cat === 'bottom-disc') {
        const g = o.geometry;
        const pos = g.attributes.position;
        const box = new THREE.Box3().setFromBufferAttribute(pos);
        const sz = box.getSize(new THREE.Vector3());
        const uv = new Float32Array(pos.count * 2);
        for (let i = 0; i < pos.count; i++) {
          const x = pos.getX(i), z = pos.getZ(i);
          uv[i * 2]     = (x - box.min.x) / Math.max(sz.x, 1e-6);
          uv[i * 2 + 1] = 1 - (z - box.min.z) / Math.max(sz.z, 1e-6);
        }
        g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
      }
    });
    console.log(`[ik1] part "${child.name}" cat=${child.userData.cat} meshes=${meshCount}`);
  }

  // Reparent the assembly under a controlled pivot Group attached
  // directly to the scene. This eliminates any inherited transforms from
  // the gltf wrapper nodes and lets us rotate/centre the whole model in
  // world space without doing parent-space gymnastics.
  const pivot = new THREE.Group();
  pivot.name = 'ik1-pivot';
  scene.add(pivot);
  if (asm.parent) asm.parent.remove(asm);
  pivot.add(asm);
  model = pivot;

  // 1. Pick the thickness axis (smallest dimension) and rotate the pivot
  //    so that axis becomes world-Y (up).
  const rawBox  = new THREE.Box3().setFromObject(asm);
  const rawSize = rawBox.getSize(new THREE.Vector3());
  const thickIdx = [rawSize.x, rawSize.y, rawSize.z].indexOf(
                     Math.min(rawSize.x, rawSize.y, rawSize.z));
  if (thickIdx === 2)      pivot.rotation.x = -Math.PI / 2;   // Z-up → Y-up
  else if (thickIdx === 0) pivot.rotation.z =  Math.PI / 2;   // X-up → Y-up
  pivot.updateMatrixWorld(true);

  // 2. Sensor-side check. PRT0004_3 (1mm-thick black-plastic disc) is the
  //    *bottom* of the device — flip 180° around X if it currently sits
  //    above the assembly centre.
  const bottomDisc = topParts.find(p => p.userData.cat === 'bottom-disc');
  if (bottomDisc) {
    const dc = new THREE.Box3().setFromObject(bottomDisc).getCenter(new THREE.Vector3());
    const ac = new THREE.Box3().setFromObject(pivot).getCenter(new THREE.Vector3());
    if (dc.y > ac.y) {
      pivot.rotation.x += Math.PI;
      pivot.updateMatrixWorld(true);
    }
  }

  // 3. Centre the pivot so the model's *world* bbox is at the origin
  //    (X/Z) and snap the bottom to world Y = 0 (so the optional ground
  //    shadow looks right). Because pivot is a direct child of `scene`,
  //    its `position` is exactly world space — no parent-frame surprises.
  const finalBox = new THREE.Box3().setFromObject(pivot);
  const fc       = finalBox.getCenter(new THREE.Vector3());
  pivot.position.x -= fc.x;
  pivot.position.z -= fc.z;
  pivot.position.y -= finalBox.min.y;       // sits on y=0
  pivot.updateMatrixWorld(true);

  // Save base local positions for explode.
  // Because asm is rotated by the pivot, world-up no longer maps to asm-local
  // +Y. Pre-compute the unit vector that points world-up *in asm-local space*
  // and use it as the explode direction so parts always move vertically on
  // screen, regardless of the orientation flips we applied above.
  const _q = new THREE.Quaternion();
  asm.getWorldQuaternion(_q).invert();
  LOCAL_WORLD_UP.set(0, 1, 0).applyQuaternion(_q).normalize();
  console.log(`[ik1] LOCAL_WORLD_UP (asm-local) = (${LOCAL_WORLD_UP.x.toFixed(2)}, ${LOCAL_WORLD_UP.y.toFixed(2)}, ${LOCAL_WORLD_UP.z.toFixed(2)})`);
  for (const p of topParts) {
    p.userData.basePos = p.position.clone();
  }

  // (Procedural battery-floor cover removed — original CAD parts are
  //  the source of truth; we'll re-classify whichever STEP part should
  //  actually be the bottom cover rather than synthesising one.)

  // sensor (2_3_ASM) — at t=0 stays at original CAD position; at t=1
  // lands at the geometric midpoint between the aluminum shell and the
  // PCB along world-up. Same trick as mid-buttons below.
  {
    scene.updateMatrixWorld(true);
    const upOf = (obj) => asm.worldToLocal(
      new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3())
    ).dot(LOCAL_WORLD_UP);
    const sensorPart = topParts.find(p => p.userData.cat === 'sensor');
    const aluPart    = topParts.find(p => p.userData.cat === 'shell-alu');
    const pcbForS    = topParts.find(p => p.userData.cat === 'pcb');
    if (sensorPart && aluPart && pcbForS) {
      const midOriginal     = (upOf(aluPart) + upOf(pcbForS)) * 0.5;
      const midAtFullExplode = midOriginal + (LAYER_TOP + LAYER_PCB) * 0.5;
      sensorPart.userData.layer = midAtFullExplode - upOf(sensorPart);
    }
  }

  // mid-button parts (PRT0005_8, PRT0006_7) — keep their basePos at the
  // original CAD position so explode t=0 looks like the real assembled
  // device. Then compute a PER-PART `layer` offset so that at t=1 each
  // button lands exactly at the geometric midpoint between PCB and the
  // bottom plastic shell along the world-up axis.
  //
  // Each top-level part's `.position` is (0,0,0) — the geometry sits at
  // its world location via vertex coordinates, not via node offsets.
  // So we measure each part's *world* bbox centre, project on LOCAL_WORLD_UP
  // for its altitude, and derive layer = midUp - own.
  scene.updateMatrixWorld(true);
  const pcbPart    = topParts.find(p => p.userData.cat === 'pcb');
  const bottomPart = topParts.find(p => p.userData.cat === 'cavity-plastic');
  if (pcbPart && bottomPart) {
    const upOf = (obj) => {
      const c = new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3());
      return asm.worldToLocal(c).dot(LOCAL_WORLD_UP);
    };
    // midUp_original from PCB and Bottom at their CAD positions; at t=1
    // they shift by LAYER_PCB and LAYER_BOTTOM respectively along world-up,
    // so midUp(t=1) = midUp_original + (LAYER_PCB + LAYER_BOTTOM)/2.
    const midUpOriginal = (upOf(pcbPart) + upOf(bottomPart)) * 0.5;
    const midUpAtFullExplode = midUpOriginal + (LAYER_PCB + LAYER_BOTTOM) * 0.5;
    for (const p of topParts) {
      if (p.userData.cat !== 'mid-button') continue;
      p.userData.layer = midUpAtFullExplode - upOf(p);
    }
  }

  // Determine which world direction the USB-C port faces — its world-space
  // X/Z offset from the assembly center tells us. We'll align "front"
  // toward USB-C and "side" toward the LED indicator if we find one.
  const asmBox = new THREE.Box3().setFromObject(pivot);
  const asmCenter = asmBox.getCenter(new THREE.Vector3());
  // PRT0005_8 sits at the front edge of the device (near the USB-C aperture)
  // so we still use its position as the FRONT_DIR proxy even though its
  // material category is now 'mid-button'.
  const usbPart = topParts.find(p => p.name === 'PRT0005_8');
  const ledPart = topParts.find(p => p.userData.cat === 'led-pipe');
  if (usbPart) {
    const c = new THREE.Box3().setFromObject(usbPart).getCenter(new THREE.Vector3()).sub(asmCenter);
    // Project to horizontal plane (XZ) and normalise
    const dir = new THREE.Vector2(c.x, c.z);
    if (dir.lengthSq() > 1e-3) {
      dir.normalize();
      FRONT_DIR.set(dir.x, 0, dir.y);
    }
  }
  if (ledPart) {
    const c = new THREE.Box3().setFromObject(ledPart).getCenter(new THREE.Vector3()).sub(asmCenter);
    const dir = new THREE.Vector2(c.x, c.z);
    if (dir.lengthSq() > 1e-3) {
      dir.normalize();
      SIDE_DIR.set(dir.x, 0, dir.y);
    }
  } else {
    SIDE_DIR.set(-FRONT_DIR.z, 0, FRONT_DIR.x);   // perpendicular fallback
  }
  // LED and USB-C may turn out to be on OPPOSITE sides (this model has them
  // 180° apart). If so, force SIDE_DIR to a true perpendicular axis so
  // 'side' previews show the blank face (matching ref 1.176/1.177).
  const dotFS = FRONT_DIR.dot(SIDE_DIR);
  if (Math.abs(dotFS) > 0.8) {
    SIDE_DIR.set(-FRONT_DIR.z, 0, FRONT_DIR.x).normalize();
  }
  console.log(`[ik1] FRONT_DIR (toward USB-C) = (${FRONT_DIR.x.toFixed(2)}, ${FRONT_DIR.y.toFixed(2)}, ${FRONT_DIR.z.toFixed(2)})`);
  console.log(`[ik1] SIDE_DIR  (perpendicular)= (${SIDE_DIR.x.toFixed(2)}, ${SIDE_DIR.y.toFixed(2)}, ${SIDE_DIR.z.toFixed(2)})`);

  // Camera framing
  const center = asmCenter;
  const radius = asmBox.getSize(new THREE.Vector3()).length() * 0.5;
  controls.target.copy(center);
  cameraFrame(center, radius, 'iso');

  dbg(
    `parts: ${topParts.length}`,
    `bbox: ${rawSize.x.toFixed(1)} x ${rawSize.y.toFixed(1)} x ${rawSize.z.toFixed(1)} mm`,
    `thickness axis (raw): ${'xyz'[thickIdx]}`,
    `pivot world centre: (${pivot.position.x.toFixed(1)},${pivot.position.y.toFixed(1)},${pivot.position.z.toFixed(1)})`,
    `camera target: (${controls.target.x.toFixed(1)},${controls.target.y.toFixed(1)},${controls.target.z.toFixed(1)})`,
    `categories: ${[...new Set(topParts.map(p => p.userData.cat))].join(', ')}`
  );

  window.__ik1 = { scene, camera, renderer, controls, model: pivot, asm, topParts, THREE };

  // Swap the colourless STEP PCB embedded in design-v2 for the standalone
  // high-precision PCB STEP (design-pcb.glb). Wait for that to finish
  // before flagging readyForCapture so screenshots see the final look.
  loadPrecisionPcb(asm).then(() => {
    loadingEl.classList.add('hidden');
    setTimeout(() => loadingEl.remove(), 400);
    window.__readyForCapture = true;
  }).catch(err => {
    console.warn('[ik1] PCB swap failed, keeping STEP PCB:', err);
    loadingEl.classList.add('hidden');
    setTimeout(() => loadingEl.remove(), 400);
    window.__readyForCapture = true;
  });
}

// ---------------------------- PCB swap (high-precision STEP + named-refdes colouring) ----------------------------
//
// design-pcb.glb is the standalone PCB STEP (converted via tools/convert-pcb.mjs)
// with full mesh precision (275 components, 232k vertices, full lead-frame
// detail). It is *colourless* (STEP carries no per-mesh colours) but each
// top-level child is named with its refdes-and-package (e.g. "R11~R0201~…",
// "USB1~USB-C-SMD…", "U6~VQFN-28…", "Board", "TopCopper", "BottomCopper",
// "TopFpcStiffener"), which lets us pick the right material per component
// type and then sub-classify each child mesh by relative size: largest mesh
// = body, smaller meshes = leads/pads.

function pcbMaterialsForComponent(name) {
  // Returns { body, lead } pair. `body` colours the largest mesh of a
  // multi-mesh component; `lead` colours every smaller mesh.
  // Match on both the refdes prefix AND the description so U1 (a 6-pin
  // CONN connector that happens to start with U) is correctly identified
  // as a connector rather than as an IC.
  const n = name.toUpperCase();

  // Board / copper / stiffener take the same colour for every mesh.
  if (n.startsWith('BOARD'))          return { body: pcbBoardMat,    lead: pcbBoardMat };
  if (n.includes('COPPER'))           return { body: pcbPadGoldMat,  lead: pcbPadGoldMat };
  if (n.includes('FPCSTIFFENER'))     return { body: fpcStiffenerMat,lead: fpcStiffenerMat };

  // Connector by description (white plastic housing + bright-gold pins).
  // Covers U1~CONN-SMD_6P… (ribbon socket) and CN1~CONN-TH_5304… (2-pin
  // power socket), regardless of refdes prefix.
  if (n.includes('CONN'))             return { body: plasticWhiteMat,    lead: connectorPinGoldMat };

  // USB-C female (silver chrome shell, silver inside contacts)
  if (n.includes('USB'))              return { body: connectorChromeMat, lead: chipLeadMat };

  // Antennas / crystals
  if (n.includes('ANT-SMD') || n.startsWith('U4')) return { body: antennaPadMat, lead: antennaPadMat };
  if (n.includes('CRYSTAL') || n.startsWith('X'))  return { body: connectorChromeMat, lead: chipLeadMat };

  // Active / passive components — body colour + silver leads
  if (n.startsWith('R'))   return { body: smdResistorBodyMat, lead: chipLeadMat };
  if (n.startsWith('C'))   return { body: ceramicCapTanMat,   lead: chipLeadMat };
  if (n.startsWith('L'))   return { body: inductorBodyMat,    lead: chipLeadMat };
  if (n.startsWith('D'))   return { body: diodeBodyMat,       lead: chipLeadMat };
  if (n.startsWith('Q'))   return { body: chipBlackMat,       lead: chipLeadMat };
  if (n.startsWith('LED')) return { body: ledDomeMat,         lead: chipLeadMat };
  // U3 specifically uses a white-package LDO / regulator — override before
  // the generic U* IC rule below.
  if (n.startsWith('U3'))  return { body: plasticWhiteMat,    lead: chipLeadMat };
  // Switches: slide-switches (MSK family — SW-TH_MSK*) are white-plastic
  // bodies; SMD tactile buttons (SW1, SW3) are black-epoxy bodies with
  // silver leads.
  if (n.startsWith('SW') && n.includes('MSK')) return { body: plasticWhiteMat, lead: chipLeadMat };
  if (n.startsWith('SW'))  return { body: chipBlackMat,        lead: chipLeadMat };
  if (n.startsWith('U'))   return { body: chipBlackMat,       lead: chipLeadMat }; // ICs

  return { body: chipBlackMat, lead: chipLeadMat };
}

function applyPcbMaterial(componentRoot, boardY = null) {
  const { body, lead } = pcbMaterialsForComponent(componentRoot.name || '');

  // Collect all meshes in this component subtree, ranked by volume.
  const meshes = [];
  componentRoot.traverse(o => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    const g = o.geometry;
    if (!g.boundingBox) g.computeBoundingBox();
    const bb = g.boundingBox;
    const vol = (bb.max.x - bb.min.x) * (bb.max.y - bb.min.y) * (bb.max.z - bb.min.z);
    meshes.push({ obj: o, vol });
  });
  if (meshes.length === 0) return;
  meshes.sort((a, b) => b.vol - a.vol);

  // (Body+lead Z-slab split removed below — `leadAtLow` and `isTopSide`
  // are no longer needed.)

  const isConnector = body === plasticWhiteMat && lead === connectorPinGoldMat;
  if (isConnector) {
    // FFC / power connectors are mostly a monolithic white-plastic mesh.
    // Color any mesh with appreciable volume as housing; only the truly
    // tiny extras (<5 % of largest) get the gold pin material.
    const threshold = meshes[0].vol * 0.05;
    for (const m of meshes) m.obj.material = (m.vol >= threshold) ? body : lead;
  } else {
    // Largest mesh → body; every smaller mesh → lead.
    meshes[0].obj.material = body;
    for (let i = 1; i < meshes.length; i++) meshes[i].obj.material = lead;
  }

  // body+lead Z-slab split removed — produced visible silver "half-chip"
  // artifacts when chips were viewed from non-ideal angles (e.g. from
  // below the PCB looking up). Chips now render as solid body colour;
  // separate pin meshes that already exist in the STEP are still picked
  // up by the lead-silver branch above.
}

// Split a body+leads merged mesh. Each PCB component mesh has its OWN
// local coordinate system (not necessarily axis-aligned with the world),
// so we project every vertex on the world-up direction (re-expressed in
// mesh-local space via the inverse of mesh.matrixWorld's rotation) and
// slice perpendicular to that.
function splitBodyAndLeads(mesh, bodyMat, leadMat, leadAtLow = true) {
  const g = mesh.geometry;
  if (!g.attributes.position) return;
  const pos = g.attributes.position;

  let idx = g.index;
  let triCount;
  let getIdx;
  if (idx) {
    triCount = idx.count / 3;
    getIdx = (t, v) => idx.getX(t * 3 + v);
  } else {
    triCount = pos.count / 3;
    getIdx = (t, v) => t * 3 + v;
  }

  // World-up in mesh-local coords.
  const meshQuat = mesh.getWorldQuaternion(new THREE.Quaternion());
  const localUp  = new THREE.Vector3(0, 1, 0).applyQuaternion(meshQuat.invert()).normalize();

  // Project every vertex on localUp to find the altitude range.
  let minU = Infinity, maxU = -Infinity;
  const proj = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i++) {
    const u = pos.getX(i) * localUp.x + pos.getY(i) * localUp.y + pos.getZ(i) * localUp.z;
    proj[i] = u;
    if (u < minU) minU = u;
    if (u > maxU) maxU = u;
  }

  // 20 % slab on the PCB-facing end.
  const span = maxU - minU;
  const leadThresh = leadAtLow ? minU + span * 0.20 : maxU - span * 0.20;

  const bodyTris = [];
  const leadTris = [];
  for (let t = 0; t < triCount; t++) {
    const a = getIdx(t, 0), b = getIdx(t, 1), c = getIdx(t, 2);
    const cu = (proj[a] + proj[b] + proj[c]) / 3;
    const isLead = leadAtLow ? (cu < leadThresh) : (cu > leadThresh);
    if (isLead) leadTris.push(a, b, c);
    else        bodyTris.push(a, b, c);
  }

  if (leadTris.length === 0 || bodyTris.length === 0) return;

  const merged = new Uint32Array(bodyTris.length + leadTris.length);
  merged.set(bodyTris, 0);
  merged.set(leadTris, bodyTris.length);

  g.setIndex(new THREE.BufferAttribute(merged, 1));
  g.clearGroups();
  g.addGroup(0,               bodyTris.length, 0);
  g.addGroup(bodyTris.length, leadTris.length, 1);

  mesh.material = [bodyMat, leadMat];
}

// Generate planar UVs + split the Board mesh's faces into TOP/BOTTOM/EDGE
// groups so we can map up.png and down.png to the two large flat faces and
// keep PCB blue on the edges. Board's local Z is the thickness axis (0..1.2);
// in-plane axes are local X and Y.
function applyBoardTextures(boardMesh) {
  const geo = boardMesh.geometry;
  if (!geo.index || !geo.attributes.position) return;
  if (!geo.boundingBox) geo.computeBoundingBox();
  const bb  = geo.boundingBox;
  const pos = geo.attributes.position;

  const xMin = bb.min.x, xMax = bb.max.x, xSpan = xMax - xMin || 1;
  const yMin = bb.min.y, yMax = bb.max.y, ySpan = yMax - yMin || 1;
  const zMid = (bb.min.z + bb.max.z) * 0.5;

  // Per-vertex UV. Top face takes up.png directly; bottom face takes
  // down.png with the U axis flipped — down.png was exported as if you
  // had flipped the board horizontally to look at its underside, so
  // mirror-flipping U brings the silkscreen back to right-reading when
  // viewed from beneath.
  const uvArr = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const v = (y - yMin) / ySpan;
    if (z >= zMid) { uvArr[i*2] = (x - xMin) / xSpan;   uvArr[i*2 + 1] = v; }
    else           { uvArr[i*2] = (xMax - x) / xSpan;   uvArr[i*2 + 1] = v; }
  }
  geo.setAttribute('uv', new THREE.BufferAttribute(uvArr, 2));

  // A triangle is a TOP face if all 3 vertices sit on the top Z plane
  // (within 0.05 mm of bb.max.z), BOTTOM if all 3 sit on the bottom Z
  // plane. Everything else (side walls, chamfers, transitions) goes to
  // the EDGE group with the solid substrate material. This is strict
  // about belonging to a planar face but tolerant of small mesh-z noise.
  const TOL = 0.05;
  const idx = geo.index;
  const tri = idx.count / 3;
  const topTris = [], botTris = [], edgeTris = [];
  for (let t = 0; t < tri; t++) {
    const a = idx.getX(t*3), b = idx.getX(t*3+1), c = idx.getX(t*3+2);
    const az = pos.getZ(a), bz = pos.getZ(b), cz = pos.getZ(c);
    const topAll = az >= bb.max.z - TOL && bz >= bb.max.z - TOL && cz >= bb.max.z - TOL;
    const botAll = az <= bb.min.z + TOL && bz <= bb.min.z + TOL && cz <= bb.min.z + TOL;
    if (topAll)      topTris.push(a, b, c);
    else if (botAll) botTris.push(a, b, c);
    else             edgeTris.push(a, b, c);
  }

  const merged = new Uint32Array(topTris.length + botTris.length + edgeTris.length);
  merged.set(topTris, 0);
  merged.set(botTris, topTris.length);
  merged.set(edgeTris, topTris.length + botTris.length);
  geo.setIndex(new THREE.BufferAttribute(merged, 1));
  geo.clearGroups();
  geo.addGroup(0,                                       topTris.length, 0);
  geo.addGroup(topTris.length,                          botTris.length, 1);
  geo.addGroup(topTris.length + botTris.length,         edgeTris.length, 2);

  boardMesh.material = [pcbTopMat, pcbBottomMat, pcbBoardMat];
  console.log(`[ik1] Board textures: ${topTris.length/3} top tris, ${botTris.length/3} bottom, ${edgeTris.length/3} edge`);
}

async function loadPrecisionPcb(asm) {
  const pcbPart = topParts.find(p => p.userData.cat === 'pcb');
  if (!pcbPart) throw new Error('no pcb part in assembly');

  const loader = new GLTFLoader();
  loader.setDRACOLoader(dracoLoader);
  const gltf = await new Promise((res, rej) =>
    loader.load('./design-pcb.glb', res, undefined, rej)
  );
  const pcb = gltf.scene;

  let pcbRoot = pcb;
  while (pcbRoot.children.length === 1 && pcbRoot.children[0].children.length > 0) {
    pcbRoot = pcbRoot.children[0];
  }
  console.log(`[ik1] PCB precision GLB: ${pcbRoot.children.length} named components`);

  // Find the Board substrate's Y centre — used to detect which side of
  // the PCB each component sits on so the body / lead-frame split can
  // pick the correct end of the bbox as the "lead side" (closest to PCB).
  let boardY = null;
  for (const comp of pcbRoot.children) {
    if ((comp.name || '').startsWith('Board')) {
      const bb = new THREE.Box3().setFromObject(comp);
      boardY = bb.getCenter(new THREE.Vector3()).y;
      break;
    }
  }

  // Apply material per refdes; for the Board substrate, swap in the
  // up.png / down.png silkscreen textures via per-face groups.
  for (const comp of pcbRoot.children) {
    applyPcbMaterial(comp, boardY);
    if ((comp.name || '').startsWith('Board')) {
      comp.traverse(o => { if (o.isMesh) applyBoardTextures(o); });
    }
  }

  pcbPart.add(pcb);
  // The standalone PCB STEP sits 1.46 mm too high relative to the
  // housing — drop it so its USB-C connector lines up with the aluminum
  // shell's USB-C slot. asm-local Z is "down toward the bottom" (positive
  // Z is "up" in the original STEP; the alu shell sits at higher Z, the
  // bottom plastic at lower Z), so move PCB in -Z to descend it.
  pcb.position.set(0, 0, -1.46);
  pcb.rotation.set(0, 0, 0);

  // Hide the original 223-mesh colourless PCB.
  pcbPart.children.forEach(child => {
    if (child === pcb) return;
    child.traverse(o => { if (o.isMesh) o.visible = false; });
  });

  window.__ik1.pcbPrecision = pcb;

  // (Battery wires removed per user request.)
}


// ---------------------------- camera helpers ----------------------------
// Padding multiplier sets the device's apparent size in the iframe — smaller
// number = closer camera = bigger model. Apparent width ≈ 100 / multiplier %.
//   desktop 1.667 → ~60% of iframe width (1.5× the old 2.5 ≈ 40% framing)
//   mobile  1.25  → ~80% of iframe width
// We key off the *parent page* width (same-origin, so readable) so the
// breakpoint matches the site's 600px mobile cutoff instead of the iframe's
// own (much smaller) width.
function frameMultiplier() {
  let w = window.innerWidth;
  try {
    if (window.parent && window.parent !== window) w = window.parent.innerWidth;
  } catch (e) { /* cross-origin — fall back to own width */ }
  return w <= 600 ? 1.25 : 1.667;
}

function cameraFrame(center, radius, preset = 'iso') {
  const dist = radius / Math.sin(THREE.MathUtils.degToRad(camera.fov * 0.5)) * frameMultiplier();
  let off;
  const F = FRONT_DIR, S = SIDE_DIR;
  switch (preset) {
    case 'front':      off = F.clone().multiplyScalar(dist); break;
    case 'back':       off = F.clone().multiplyScalar(-dist); break;
    case 'top':        off = new THREE.Vector3(0, 1, 0.0001).multiplyScalar(dist); break;
    case 'bottom':     off = new THREE.Vector3(0, -1, 0.0001).multiplyScalar(dist); break;
    case 'side':       off = S.clone().multiplyScalar(dist); break;
    case 'iso':        off = new THREE.Vector3(0.7, 0.65, 0.85).normalize().multiplyScalar(dist); break;
    case 'iso-front':  off = new THREE.Vector3(0.7, 0.65,-0.85).normalize().multiplyScalar(dist); break;
    case 'iso-bottom':       off = new THREE.Vector3(0.7, -0.65, 0.85).normalize().multiplyScalar(dist); break;
    case 'iso-bottom-front': off = new THREE.Vector3(0.7, -0.65, -0.85).normalize().multiplyScalar(dist); break;
    default:           off = new THREE.Vector3(0.7, 0.65, 0.85).normalize().multiplyScalar(dist);
  }
  camera.position.copy(center).add(off);
  // For straight-up / straight-down views the default up=(0,1,0) is parallel
  // to the view direction (degenerate). Use a horizontal up vector instead
  // so the image is not undefined.
  if (preset === 'top' || preset === 'bottom') {
    camera.up.set(0, 0, -1);
  } else {
    camera.up.set(0, 1, 0);
  }
  camera.lookAt(center);
  controls.target.copy(center);
  controls.update();
}

// expose to test harness
window.__setCamera = (preset) => {
  if (!model) return;
  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() * 0.5;
  cameraFrame(center, radius, preset);
};

// ---------------------------- explode animation ----------------------------
function applyExplode(t) {
  // t in [0,1] — 0 assembled, 1 exploded.
  // Move along the world-up direction expressed in asm-local space, so
  // explode is always vertical on-screen no matter how the model was
  // oriented to bring its sensor face up.
  for (const p of topParts) {
    if (!p.userData.basePos) continue;
    const layer = p.userData.layer || 0;
    p.position.copy(p.userData.basePos).addScaledVector(LOCAL_WORLD_UP, layer * t);
  }
}
window.__setExplode = (t) => {
  targetT = THREE.MathUtils.clamp(t, 0, 1);
  // Keep the slider visual in sync if the UI is wired up.
  const s = document.getElementById('explode-slider');
  const v = document.getElementById('explode-val');
  if (s) { s.value = targetT * 100; s.style.setProperty('--pct', `${targetT * 100}%`); }
  if (v) v.textContent = `${Math.round(targetT * 100)}%`;
};

// ---------------------------- UI wiring ----------------------------
const explodeSlider = document.getElementById('explode-slider');
const explodeVal    = document.getElementById('explode-val');
const btnReset      = document.getElementById('btn-reset');
const viewsBar      = document.getElementById('views');

let currentPreset = 'iso';

function setExplodeFromSlider(v) {
  // Snap-to-zero at the very bottom of the rail so it's easy to fully reassemble
  if (v <= 2) v = 0;
  targetT = v / 100;
  explodeSlider.value = v;
  explodeSlider.style.setProperty('--pct', `${v}%`);
  explodeVal.textContent = `${Math.round(v)}%`;
}
explodeSlider.addEventListener('input', (e) => setExplodeFromSlider(parseFloat(e.target.value)));
setExplodeFromSlider(0);

btnReset.addEventListener('click', () => {
  setExplodeFromSlider(0);
  setActiveView(currentPreset);
  window.__setCamera(currentPreset);
});

function setActiveView(preset) {
  currentPreset = preset;
  for (const b of viewsBar.querySelectorAll('button')) {
    b.classList.toggle('active', b.dataset.preset === preset);
  }
}
viewsBar.addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-preset]');
  if (!btn) return;
  const preset = btn.dataset.preset;
  setActiveView(preset);
  window.__setCamera(preset);
});

for (const sw of document.querySelectorAll('.variants .swatch')) {
  sw.addEventListener('click', () => {
    document.querySelectorAll('.variants .swatch').forEach(s => s.classList.remove('active'));
    sw.classList.add('active');
    currentVariant = sw.dataset.variant;
    // Hot-swap by reassigning the shared aluminum material reference everywhere it's used
    for (const p of topParts) {
      const cat = p.userData.cat;
      if (cat === 'shell-alu') {
        p.traverse(o => { if (o.isMesh) o.material = aluminumMats[currentVariant]; });
      }
    }
  });
}
window.__setVariant = (v) => {
  const sw = document.querySelector(`.variants .swatch[data-variant="${v}"]`);
  if (sw) sw.click();
};

// ---------------------------- render loop ----------------------------
function resize() {
  const w = viewport.clientWidth || window.innerWidth;
  const h = viewport.clientHeight || window.innerHeight;
  // updateStyle=true so the canvas CSS size matches the viewport at any DPR.
  // (With `false` and DPR=2, the canvas's intrinsic CSS pixel size becomes
  // 2× the viewport and the centred render slides into the lower-right
  // quadrant of the visible viewport.)
  renderer.setSize(w, h, true);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

const clock = new THREE.Clock();
let needsRender = true;
let visible = true;
let rafId = null;

controls.addEventListener('change', () => { needsRender = true; });
window.addEventListener('resize', () => { needsRender = true; });

// Parent page notifies us when the iframe enters/leaves viewport so we can
// stop the render loop entirely (saves CPU/GPU and prevents scroll jank).
window.addEventListener('message', (e) => {
  if (!e.data || e.data.type !== 'ik1-visibility') return;
  const wasVisible = visible;
  visible = !!e.data.visible;
  if (visible && !wasVisible && !rafId) {
    needsRender = true;
    rafId = requestAnimationFrame(tick);
  }
});

function tick() {
  if (!visible) { rafId = null; return; }
  rafId = requestAnimationFrame(tick);
  const dt = clock.getDelta();
  // ease explode toward target
  if (Math.abs(explodeT - targetT) > 1e-3) {
    const k = 1 - Math.pow(0.001, dt); // dampened
    explodeT = THREE.MathUtils.lerp(explodeT, targetT, k);
    if (model) applyExplode(explodeT);
    needsRender = true;
  }
  const moved = controls.update();
  if (needsRender || moved) {
    renderer.render(scene, camera);
    needsRender = false;
  }
}
rafId = requestAnimationFrame(tick);
