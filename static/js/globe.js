/* =============================================================================
   Travello — hero globe
   A wireframe Earth with a pin on every live destination and two flight arcs
   tracing between them. Built on Three.js; silently skipped if WebGL or the
   library is unavailable, or if the visitor prefers reduced motion.
   ========================================================================== */
(function () {
  "use strict";

  const canvas = document.getElementById("globe-canvas");
  if (!canvas || typeof window.THREE === "undefined") return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const THREE = window.THREE;

  const COLOURS = {
    grid: 0x7c4dff,
    core: 0x0e0a1f,
    pin: 0xff4d8d,
    pinFeatured: 0xffb020,
    arc: 0x35e0c2,
    star: 0xa99fc9,
  };

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch (error) {
    return; // No WebGL — the hero still reads fine without the globe.
  }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 1000);
  camera.position.set(0, 0.3, 6.4);

  const world = new THREE.Group();
  world.rotation.z = -0.35; // axial tilt
  scene.add(world);

  const RADIUS = 2.35;

  // Solid inner sphere so pins on the far side are hidden by the planet.
  world.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(RADIUS * 0.985, 48, 48),
      new THREE.MeshBasicMaterial({ color: COLOURS.core })
    )
  );

  // Latitude/longitude wireframe.
  world.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(RADIUS, 36, 24),
      new THREE.MeshBasicMaterial({
        color: COLOURS.grid,
        wireframe: true,
        transparent: true,
        opacity: 0.16,
      })
    )
  );

  // Soft halo.
  world.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(RADIUS * 1.06, 48, 48),
      new THREE.MeshBasicMaterial({
        color: COLOURS.grid,
        transparent: true,
        opacity: 0.05,
        side: THREE.BackSide,
      })
    )
  );

  // Starfield.
  const starCount = 520;
  const starPositions = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i += 1) {
    const radius = 14 + Math.random() * 22;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    starPositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    starPositions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    starPositions[i * 3 + 2] = radius * Math.cos(phi);
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  const stars = new THREE.Points(
    starGeometry,
    new THREE.PointsMaterial({ color: COLOURS.star, size: 0.07, transparent: true, opacity: 0.55 })
  );
  scene.add(stars);

  /** Convert latitude/longitude into a point on the sphere. */
  function toVector(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    return new THREE.Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta)
    );
  }

  const pinGeometry = new THREE.SphereGeometry(0.045, 12, 12);
  const pinGroup = new THREE.Group();
  world.add(pinGroup);

  function addPin(lat, lon, featured) {
    const material = new THREE.MeshBasicMaterial({
      color: featured ? COLOURS.pinFeatured : COLOURS.pin,
    });
    const pin = new THREE.Mesh(pinGeometry, material);
    pin.position.copy(toVector(lat, lon, RADIUS * 1.01));
    pinGroup.add(pin);

    // Halo ring that pulses outward.
    const halo = new THREE.Mesh(
      new THREE.RingGeometry(0.07, 0.095, 20),
      new THREE.MeshBasicMaterial({
        color: material.color,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
      })
    );
    halo.position.copy(pin.position);
    halo.lookAt(new THREE.Vector3(0, 0, 0));
    halo.userData.phase = Math.random() * Math.PI * 2;
    pinGroup.add(halo);
    return pin;
  }

  function addArc(from, to) {
    const start = toVector(from[0], from[1], RADIUS * 1.01);
    const end = toVector(to[0], to[1], RADIUS * 1.01);
    const mid = start.clone().add(end).multiplyScalar(0.5).normalize()
      .multiplyScalar(RADIUS * 1.45);
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(curve.getPoints(60)),
      new THREE.LineBasicMaterial({ color: COLOURS.arc, transparent: true, opacity: 0.45 })
    );
    world.add(line);

    const traveller = new THREE.Mesh(
      new THREE.SphereGeometry(0.038, 10, 10),
      new THREE.MeshBasicMaterial({ color: COLOURS.arc })
    );
    world.add(traveller);
    return { curve, traveller, offset: Math.random() };
  }

  const fallbackPins = [
    [15.29, 74.12, true],   // Goa
    [27.17, 78.04, false],  // Agra
    [34.08, 74.79, true],   // Srinagar
    [9.93, 76.26, false],   // Kochi
    [-8.34, 115.09, true],  // Bali
    [35.01, 135.76, false], // Kyoto
    [64.96, -19.02, true],  // Iceland
    [41.89, 12.49, false],  // Rome
  ];

  const arcs = [];

  function buildPins(points) {
    points.forEach((point) => addPin(point[0], point[1], point[2]));
    if (points.length >= 2) {
      arcs.push(addArc(points[0], points[Math.min(4, points.length - 1)]));
      arcs.push(addArc(points[1], points[points.length - 1]));
    }
  }

  // Pull real destination coordinates from the API; fall back to a fixed set.
  fetch("/api/globe-pins/", { headers: { Accept: "application/json" } })
    .then((response) => (response.ok ? response.json() : Promise.reject()))
    .then((data) => {
      const points = (data.results || data)
        .filter((item) => item.latitude != null && item.longitude != null)
        .map((item) => [item.latitude, item.longitude, item.is_featured]);
      buildPins(points.length ? points : fallbackPins);
    })
    .catch(() => buildPins(fallbackPins));

  // Mouse parallax.
  const pointer = { x: 0, y: 0 };
  if (!reduceMotion) {
    window.addEventListener("pointermove", (event) => {
      pointer.x = (event.clientX / window.innerWidth - 0.5) * 0.4;
      pointer.y = (event.clientY / window.innerHeight - 0.5) * 0.25;
    });
  }

  function resize() {
    const parent = canvas.parentElement;
    const width = parent.clientWidth;
    const height = parent.clientHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    // Pull the camera back on narrow screens so the globe stays fully visible.
    camera.position.z = width < 640 ? 7.8 : 6.4;
    camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);
  resize();

  const clock = new THREE.Clock();
  function render() {
    const elapsed = clock.getElapsedTime();

    if (!reduceMotion) {
      world.rotation.y += 0.0016;
      stars.rotation.y -= 0.0004;
      world.rotation.x += (pointer.y - world.rotation.x * 0.5) * 0.01;
      camera.position.x += (pointer.x * 1.6 - camera.position.x) * 0.03;
      camera.lookAt(0, 0, 0);

      pinGroup.children.forEach((child) => {
        if (child.userData.phase === undefined) return;
        const pulse = (Math.sin(elapsed * 1.8 + child.userData.phase) + 1) / 2;
        child.scale.setScalar(1 + pulse * 0.9);
        child.material.opacity = 0.55 - pulse * 0.45;
      });

      arcs.forEach((arc) => {
        const t = (elapsed * 0.13 + arc.offset) % 1;
        arc.traveller.position.copy(arc.curve.getPoint(t));
      });
    }

    renderer.render(scene, camera);
    requestAnimationFrame(render);
  }
  render();
})();
