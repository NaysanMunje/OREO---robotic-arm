/** Shared MediaPipe hand + face landmark helpers. */

export const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17],
];

export function packHandResult(result) {
  if (!result?.landmarks?.length) {
    return { detected: false, hand_count: 0, hands: [] };
  }
  const hands = result.landmarks.map((hand) =>
    hand.map((p) => ({ x: p.x, y: p.y, z: p.z })),
  );
  const tip = hands[0]?.[8];
  return {
    detected: true,
    hand_count: hands.length,
    hands,
    index_tip: tip ? { x: tip.x, y: tip.y } : null,
  };
}

/** Face oval outline (MediaPipe face mesh indices). */
export const FACE_OVAL = [
  10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
  400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
  54, 103, 67, 109,
];

export const FACE_LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246];
export const FACE_RIGHT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398];

function drawPolyline(ctx, landmarks, indices, width, height, close = false) {
  if (!landmarks?.length || !indices?.length) return;
  ctx.beginPath();
  const p0 = landmarks[indices[0]];
  if (!p0) return;
  ctx.moveTo(p0.x * width, p0.y * height);
  for (let i = 1; i < indices.length; i++) {
    const p = landmarks[indices[i]];
    if (!p) continue;
    ctx.lineTo(p.x * width, p.y * height);
  }
  if (close) ctx.closePath();
  ctx.stroke();
}

export function packFaceResult(result) {
  if (!result?.faceLandmarks?.length) {
    return { detected: false, face_count: 0, faces: [] };
  }
  const faces = result.faceLandmarks.map((face) =>
    face.map((p) => ({ x: p.x, y: p.y, z: p.z })),
  );
  const nose = faces[0]?.[1];
  return {
    detected: true,
    face_count: faces.length,
    faces,
    nose_tip: nose ? { x: nose.x, y: nose.y } : null,
  };
}

export function drawFacesOnCanvas(ctx, faceState, width, height, clearFirst = true) {
  if (!ctx) return;
  if (clearFirst) ctx.clearRect(0, 0, width, height);
  if (!faceState?.detected || !faceState.faces?.length) return;

  for (const landmarks of faceState.faces) {
    ctx.strokeStyle = 'rgba(125, 211, 252, 0.92)';
    ctx.lineWidth = 2.5;
    drawPolyline(ctx, landmarks, FACE_OVAL, width, height, true);
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.85)';
    ctx.lineWidth = 1.5;
    drawPolyline(ctx, landmarks, FACE_LEFT_EYE, width, height, true);
    drawPolyline(ctx, landmarks, FACE_RIGHT_EYE, width, height, true);

    const nose = landmarks[1];
    if (nose) {
      ctx.strokeStyle = 'rgba(251, 191, 36, 1)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(nose.x * width, nose.y * height, 8, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

/**
 * Thumb-driven control: the thumb stands in for the arm.
 * Hand landmark indices along the thumb:
 *   1 = CMC (base), 2 = MCP knuckle, 3 = IP knuckle, 4 = tip.
 * The MCP knuckle drives the shoulder, the IP knuckle drives the elbow.
 */
const THUMB = { cmc: 1, mcp: 2, ip: 3, tip: 4 };

function angleAtDeg(a, b, c) {
  if (!a || !b || !c) return null;
  const v1x = a.x - b.x;
  const v1y = a.y - b.y;
  const v2x = c.x - b.x;
  const v2y = c.y - b.y;
  const m = Math.hypot(v1x, v1y) * Math.hypot(v2x, v2y);
  if (!m) return null;
  const cos = Math.max(-1, Math.min(1, (v1x * v2x + v1y * v2y) / m));
  return (Math.acos(cos) * 180) / Math.PI;
}

/** Angle of segment a→b above the horizontal plane: -90=down, 0=level, +90=up. */
function elevationAboveHorizontal(a, b) {
  if (!a || !b) return null;
  const dx = b.x - a.x;
  const dy = b.y - a.y; // image y grows downward
  if (dx === 0 && dy === 0) return null;
  return (Math.atan2(-dy, Math.abs(dx)) * 180) / Math.PI;
}

export function packThumbResult(result) {
  const lm = result?.landmarks?.[0];
  if (!lm || lm.length < 5) {
    return { detected: false, side: null, shoulder_angle: null, elbow_angle: null, points: null };
  }
  const pick = (i) => (lm[i] ? { x: lm[i].x, y: lm[i].y } : null);
  const cmc = pick(THUMB.cmc);
  const mcp = pick(THUMB.mcp);
  const ip = pick(THUMB.ip);
  const tip = pick(THUMB.tip);
  // Shoulder = MCP knuckle: elevation of the proximal segment above horizontal.
  const shoulderAngle = elevationAboveHorizontal(mcp, ip);
  // Elbow = IP knuckle: interior bend between the two thumb segments.
  const elbowAngle = angleAtDeg(mcp, ip, tip);
  const side = result?.handednesses?.[0]?.[0]?.categoryName ?? result?.handedness?.[0]?.[0]?.categoryName ?? null;
  return {
    detected: shoulderAngle != null && elbowAngle != null,
    side,
    shoulder_angle: shoulderAngle != null ? Math.round(shoulderAngle * 10) / 10 : null,
    elbow_angle: elbowAngle != null ? Math.round(elbowAngle * 10) / 10 : null,
    // Reuse the generic skeleton fields so existing drawing/relay stays unchanged.
    points: { hip: cmc, shoulder: mcp, elbow: ip, wrist: tip },
  };
}

export function drawPoseOnCanvas(ctx, poseState, width, height, clearFirst = true) {
  if (!ctx) return;
  if (clearFirst) ctx.clearRect(0, 0, width, height);
  if (!poseState?.detected || !poseState.points) return;
  const { shoulder, elbow, wrist, hip } = poseState.points;
  const P = (p) => (p ? { x: p.x * width, y: p.y * height } : null);
  const seg = (a, b) => {
    const pa = P(a);
    const pb = P(b);
    if (!pa || !pb) return;
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.stroke();
  };
  ctx.strokeStyle = 'rgba(168, 85, 247, 0.55)';
  ctx.lineWidth = 3;
  seg(hip, shoulder);
  ctx.strokeStyle = 'rgba(192, 132, 252, 0.95)';
  ctx.lineWidth = 5;
  seg(shoulder, elbow);
  seg(elbow, wrist);
  for (const p of [shoulder, elbow, wrist]) {
    const q = P(p);
    if (!q) continue;
    ctx.fillStyle = 'rgba(233, 213, 255, 0.98)';
    ctx.beginPath();
    ctx.arc(q.x, q.y, 6, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = 'rgba(233, 213, 255, 1)';
  ctx.font = '600 14px system-ui, sans-serif';
  const eP = P(elbow);
  const sP = P(shoulder);
  if (eP && poseState.elbow_angle != null) {
    ctx.fillText(`elbow ${Math.round(poseState.elbow_angle)}\u00B0`, eP.x + 10, eP.y);
  }
  if (sP && poseState.shoulder_angle != null) {
    ctx.fillText(`shoulder ${Math.round(poseState.shoulder_angle)}\u00B0`, sP.x + 10, sP.y - 6);
  }
}

export function drawTracksOnCanvas(ctx, handState, faceState, width, height, poseState) {
  if (!ctx) return;
  ctx.clearRect(0, 0, width, height);
  drawHandsOnCanvas(ctx, handState, width, height, false);
  drawFacesOnCanvas(ctx, faceState, width, height, false);
  drawPoseOnCanvas(ctx, poseState, width, height, false);
}

export function drawHandsOnCanvas(ctx, handState, width, height, clearFirst = true) {
  if (!ctx) return;
  if (clearFirst) ctx.clearRect(0, 0, width, height);
  if (!handState?.detected || !handState.hands?.length) return;
  for (const landmarks of handState.hands) {
    ctx.strokeStyle = 'rgba(74, 222, 128, 0.92)';
    ctx.lineWidth = 3;
    for (const [a, b] of HAND_CONNECTIONS) {
      const p1 = landmarks[a];
      const p2 = landmarks[b];
      if (!p1 || !p2) continue;
      ctx.beginPath();
      ctx.moveTo(p1.x * width, p1.y * height);
      ctx.lineTo(p2.x * width, p2.y * height);
      ctx.stroke();
    }
    for (const p of landmarks) {
      ctx.fillStyle = 'rgba(134, 239, 172, 0.95)';
      ctx.beginPath();
      ctx.arc(p.x * width, p.y * height, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    const tip = landmarks[8];
    if (tip) {
      ctx.strokeStyle = 'rgba(251, 191, 36, 1)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(tip.x * width, tip.y * height, 12, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

export async function createHandLandmarker() {
  const { HandLandmarker, FilesetResolver } = await import(
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm'
  );
  const wasmPath = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm';
  const vision = await FilesetResolver.forVisionTasks(wasmPath);
  let landmarker;
  try {
    landmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numHands: 2,
    });
  } catch (_) {
    landmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
        delegate: 'CPU',
      },
      runningMode: 'VIDEO',
      numHands: 2,
    });
  }
  return landmarker;
}

export async function createFaceLandmarker() {
  const { FaceLandmarker, FilesetResolver } = await import(
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm'
  );
  const wasmPath = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm';
  const vision = await FilesetResolver.forVisionTasks(wasmPath);
  const model =
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';
  const opts = {
    baseOptions: { modelAssetPath: model },
    runningMode: 'VIDEO',
    numFaces: 1,
  };
  try {
    return await FaceLandmarker.createFromOptions(vision, {
      ...opts,
      baseOptions: { ...opts.baseOptions, delegate: 'GPU' },
    });
  } catch (_) {
    return FaceLandmarker.createFromOptions(vision, {
      ...opts,
      baseOptions: { ...opts.baseOptions, delegate: 'CPU' },
    });
  }
}
