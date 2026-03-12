import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.162.0/build/three.module.js';

const socket = io();

const nameInput = document.getElementById('nameInput');
const roomInput = document.getElementById('roomInput');
const createBtn = document.getElementById('createBtn');
const joinBtn = document.getElementById('joinBtn');
const startBtn = document.getElementById('startBtn');
const shootSelfBtn = document.getElementById('shootSelfBtn');
const shootEnemyBtn = document.getElementById('shootEnemyBtn');
const stateBox = document.getElementById('stateBox');
const roomInfo = document.getElementById('roomInfo');
const gameControls = document.getElementById('gameControls');
const canvas = document.getElementById('scene');

let me = null;
let room = null;
let state = null;

function showState(message = '') {
  if (!state) {
    stateBox.textContent = message;
    return;
  }

  const players = state.players
    .map((p) => `${p} | HP: ${state.hp[p] ?? '-'} ${state.turn === p ? '⬅ turn' : ''}`)
    .join('\n');

  stateBox.textContent = [
    message,
    '',
    `Room: ${room}`,
    `Players:\n${players}`,
    `Shells remaining: ${state.shells_total} (live ${state.live_count} / blank ${state.blank_count})`,
    state.winner ? `Winner: ${state.winner}` : '',
  ]
    .filter(Boolean)
    .join('\n');

  const canPlay = state.turn === me && !state.winner && state.players.length === 2;
  shootSelfBtn.disabled = !canPlay;
  shootEnemyBtn.disabled = !canPlay;
}

createBtn.onclick = () => {
  socket.emit('create_room', { name: nameInput.value.trim() });
};

joinBtn.onclick = () => {
  socket.emit('join_room', { name: nameInput.value.trim(), room: roomInput.value.trim() });
};

startBtn.onclick = () => socket.emit('start_game');
shootSelfBtn.onclick = () => socket.emit('shoot', { target: 'self' });
shootEnemyBtn.onclick = () => socket.emit('shoot', { target: 'opponent' });

socket.on('room_joined', (payload) => {
  me = payload.you;
  room = payload.room;
  state = payload.state;
  roomInfo.textContent = `Connected to room: ${room}`;
  roomInfo.classList.remove('hidden');
  gameControls.classList.remove('hidden');
  showState('Lobby ready. Wait for second player then click Start Match.');
});

socket.on('state_update', (payload) => {
  state = payload.state;
  showState(payload.message || '');
});

socket.on('error_message', (payload) => {
  showState(`Error: ${payload.message}`);
});

// 3D scene setup
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x090b13);

const camera = new THREE.PerspectiveCamera(60, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
camera.position.set(0, 3, 8);

const hemi = new THREE.HemisphereLight(0xbfd4ff, 0x101010, 1.2);
scene.add(hemi);

const spot = new THREE.SpotLight(0xffffff, 1.3);
spot.position.set(4, 8, 3);
scene.add(spot);

const table = new THREE.Mesh(
  new THREE.CylinderGeometry(3.5, 3.8, 0.6, 32),
  new THREE.MeshStandardMaterial({ color: 0x23262f, metalness: 0.4, roughness: 0.7 }),
);
table.position.y = -1;
scene.add(table);

const gun = new THREE.Group();
const barrel = new THREE.Mesh(
  new THREE.CylinderGeometry(0.28, 0.28, 3.4, 24),
  new THREE.MeshStandardMaterial({ color: 0x8a95a5, metalness: 0.9, roughness: 0.2 }),
);
barrel.rotation.z = Math.PI / 2;
gun.add(barrel);

const grip = new THREE.Mesh(
  new THREE.BoxGeometry(0.5, 1.3, 0.8),
  new THREE.MeshStandardMaterial({ color: 0x3a2a1f, metalness: 0.15, roughness: 0.85 }),
);
grip.position.set(-1.2, -0.9, 0);
gun.add(grip);

gun.position.y = 0.1;
scene.add(gun);

const shellRing = [];
for (let i = 0; i < 8; i += 1) {
  const shell = new THREE.Mesh(
    new THREE.CylinderGeometry(0.12, 0.12, 0.5, 16),
    new THREE.MeshStandardMaterial({ color: 0xe3b341, metalness: 0.8, roughness: 0.3 }),
  );
  const angle = (i / 8) * Math.PI * 2;
  shell.position.set(Math.cos(angle) * 2, -0.5, Math.sin(angle) * 2);
  shell.rotation.x = Math.PI / 2;
  scene.add(shell);
  shellRing.push(shell);
}

function animate(time) {
  const t = time * 0.001;
  gun.rotation.y = Math.sin(t * 0.7) * 0.5;
  gun.position.y = 0.1 + Math.sin(t * 1.2) * 0.07;

  const remaining = state?.shells_total ?? 0;
  shellRing.forEach((shell, idx) => {
    shell.visible = idx < remaining;
    shell.rotation.y = t + idx * 0.4;
  });

  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

window.addEventListener('resize', () => {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
});

requestAnimationFrame(animate);
showState('Enter your name and create or join a room.');
