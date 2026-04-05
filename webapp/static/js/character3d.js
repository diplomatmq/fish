import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";
import { GLTFLoader } from "https://unpkg.com/three@0.160.0/examples/jsm/loaders/GLTFLoader.js";

const MODEL_URL = "/static/models/fisherman.glb";

function buildAnchorTexture() {
  const size = 512;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#225f8f";
  ctx.fillRect(0, 0, size, size);

  ctx.strokeStyle = "#e8f6ff";
  ctx.lineWidth = 8;

  for (let y = 48; y < size; y += 96) {
    for (let x = 48; x < size; x += 96) {
      ctx.beginPath();
      ctx.arc(x, y - 12, 9, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(x, y - 3);
      ctx.lineTo(x, y + 26);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(x, y + 24, 18, 0, Math.PI, true);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(x - 18, y + 24);
      ctx.lineTo(x - 28, y + 10);
      ctx.moveTo(x + 18, y + 24);
      ctx.lineTo(x + 28, y + 10);
      ctx.stroke();
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(2, 2);
  return texture;
}

function buildFallbackCharacter() {
  const group = new THREE.Group();

  const skinMat = new THREE.MeshStandardMaterial({ color: 0xf1c8a3, roughness: 0.72, metalness: 0.04 });
  const shirtMat = new THREE.MeshStandardMaterial({ color: 0xf8f8f8, roughness: 0.86, metalness: 0.02 });
  const shortsMat = new THREE.MeshStandardMaterial({ map: buildAnchorTexture(), roughness: 0.9, metalness: 0.01 });
  const darkMat = new THREE.MeshStandardMaterial({ color: 0x2f3138, roughness: 0.8, metalness: 0.06 });

  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.29, 0.25, 0.78, 18), shirtMat);
  torso.position.y = 1.12;
  group.add(torso);

  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.12, 16), skinMat);
  neck.position.y = 1.55;
  group.add(neck);

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.25, 28, 28), skinMat);
  head.position.y = 1.8;
  group.add(head);

  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.032, 14, 14), skinMat);
  nose.scale.set(1.05, 1.1, 1.35);
  nose.position.set(0, 1.76, 0.23);
  group.add(nose);

  const leftEye = new THREE.Mesh(new THREE.SphereGeometry(0.018, 10, 10), darkMat);
  leftEye.position.set(-0.075, 1.82, 0.21);
  group.add(leftEye);

  const rightEye = new THREE.Mesh(new THREE.SphereGeometry(0.018, 10, 10), darkMat);
  rightEye.position.set(0.075, 1.82, 0.21);
  group.add(rightEye);

  const shorts = new THREE.Mesh(new THREE.CylinderGeometry(0.31, 0.32, 0.3, 18), shortsMat);
  shorts.position.y = 0.9;
  group.add(shorts);

  const leftLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.095, 0.64, 16), skinMat);
  leftLeg.position.set(-0.11, 0.55, 0);
  group.add(leftLeg);

  const rightLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.095, 0.64, 16), skinMat);
  rightLeg.position.set(0.11, 0.55, 0);
  group.add(rightLeg);

  const leftFoot = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.08, 0.3), darkMat);
  leftFoot.position.set(-0.11, 0.18, 0.08);
  group.add(leftFoot);

  const rightFoot = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.08, 0.3), darkMat);
  rightFoot.position.set(0.11, 0.18, 0.08);
  group.add(rightFoot);

  const leftArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.067, 0.56, 8, 16), skinMat);
  leftArm.position.set(-0.35, 1.15, 0.03);
  leftArm.rotation.z = 0.24;
  group.add(leftArm);

  const rightArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.067, 0.56, 8, 16), skinMat);
  rightArm.position.set(0.35, 1.15, 0.03);
  rightArm.rotation.z = -0.24;
  group.add(rightArm);

  const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 1.45, 12), new THREE.MeshStandardMaterial({ color: 0x8b5a2b }));
  rod.position.set(0.54, 1.18, 0.08);
  rod.rotation.z = -0.47;
  group.add(rod);

  const line = new THREE.Mesh(new THREE.CylinderGeometry(0.002, 0.002, 0.56, 6), new THREE.MeshStandardMaterial({ color: 0xd6f3ff }));
  line.position.set(0.88, 0.9, 0.08);
  group.add(line);

  group.position.y = -0.16;
  return group;
}

function loadGlbModel(path) {
  return new Promise((resolve, reject) => {
    const loader = new GLTFLoader();
    loader.load(
      path,
      (gltf) => resolve(gltf.scene),
      undefined,
      (error) => reject(error)
    );
  });
}

export function initCharacterScene(host) {
  if (!host) {
    return {
      resize() {},
      destroy() {},
    };
  }

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  host.innerHTML = "";
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x0d4362, 3, 8);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(0, 1.5, 3.6);

  const hemi = new THREE.HemisphereLight(0xb8edff, 0x0f2f44, 1.1);
  scene.add(hemi);

  const key = new THREE.DirectionalLight(0xffffff, 1.15);
  key.position.set(1.7, 2.6, 2.3);
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x7cd6ff, 0.7);
  rim.position.set(-2.3, 1.8, -2.1);
  scene.add(rim);

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(1.35, 50),
    new THREE.MeshStandardMaterial({
      color: 0x145778,
      roughness: 0.86,
      metalness: 0.03,
      transparent: true,
      opacity: 0.84,
    })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.2;
  scene.add(floor);

  const actorRoot = new THREE.Group();
  scene.add(actorRoot);

  let actor = null;
  let disposed = false;
  let rafId = 0;

  const fallbackActor = buildFallbackCharacter();
  actorRoot.add(fallbackActor);
  actor = fallbackActor;

  loadGlbModel(MODEL_URL)
    .then((model) => {
      if (disposed) {
        return;
      }
      actorRoot.remove(fallbackActor);
      model.scale.set(1.3, 1.3, 1.3);
      model.position.y = -0.2;
      actorRoot.add(model);
      actor = model;
    })
    .catch(() => {
      // Keep fallback if high quality model is not provided yet.
    });

  function resize() {
    const width = Math.max(1, host.clientWidth || 1);
    const height = Math.max(1, host.clientHeight || 1);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function frame(time) {
    if (disposed) {
      return;
    }

    const t = time * 0.001;
    if (actor) {
      actor.rotation.y = Math.sin(t * 0.6) * 0.2;
      actor.position.y = (actor === fallbackActor ? -0.16 : -0.2) + Math.sin(t * 1.4) * 0.03;
    }

    floor.material.opacity = 0.8 + Math.sin(t * 1.5) * 0.06;
    renderer.render(scene, camera);
    rafId = requestAnimationFrame(frame);
  }

  resize();
  rafId = requestAnimationFrame(frame);

  return {
    resize,
    destroy() {
      disposed = true;
      cancelAnimationFrame(rafId);
      renderer.dispose();
      host.innerHTML = "";
    },
  };
}
