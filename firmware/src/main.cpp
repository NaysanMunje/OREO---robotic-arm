/*
 * ESP32-S3 — 4 motor test + limit switch homing (M2, M3, M4)
 * Physical wiring (confirmed):
 * M1 wrist:    PUL=4   DIR=5   — no limit
 * M2 shoulder: PUL=9   DIR=10  — Limit=GPIO7
 * M3 elbow:    PUL=11  DIR=12  — Limit=GPIO15
 * M4 base:     PUL=13  DIR=14  — Limit=GPIO6
 * WiFi: joins home network · http://arm.local (mDNS)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include "wifi_secrets.h"

static const uint8_t NUM_MOTORS = 4;

static const unsigned int HOME_PULSE_US = 500;
static const unsigned int HOME_SEEK_DELAY_US = 1500;
static const unsigned int HOME_BACKOFF_DELAY_US = 1500;
static const uint32_t HOME_MAX_SEEK_STEPS = 120000;
static const uint32_t HOME_MIN_SEEK_STEPS = 40;
static const uint8_t LIMIT_DEBOUNCE_HITS = 3;
static const uint16_t LIMIT_DEBOUNCE_GAP_US = 150;
static const uint8_t LIMIT_HOME_HITS = 2;
static const uint16_t LIMIT_HOME_GAP_US = 60;
static const unsigned int HOME_LIMIT_POLL_US = 50;

static const unsigned int DELAY_MIN = 200;
static const unsigned int DELAY_MAX = 4000;
static const unsigned int PULSE_MIN = 100;
static const unsigned int PULSE_MAX = 2500;

// Steps per degree at each joint (motor index 0=M1 … 3=M4).
// M2/M3: measured 45° in 1000 steps @ 20:1 → 1000/45 ≈ 22.22 steps/°
// Implied 400 steps/motor-rev (microstepping). M4 @ 25:1 → 400×25/360 ≈ 27.78
// M1 wrist: no gearbox assumed (1:1) → 400/360 ≈ 1.11 steps/°
static const float STEPS_PER_DEGREE[NUM_MOTORS] = {
    1100.0f / 90.0f,   // M1 wrist (measured: 1100 steps / 90°)
    1000.0f / 45.0f,    // M2 shoulder (20:1, measured)
    1000.0f / 45.0f,    // M3 elbow (20:1, measured)
    400.0f * 25.0f / 360.0f,  // M4 base (25:1, calculated)
};

// Max travel (0° at limit → far end). Keep in sync with arm_twin/config.json.
static const float MAX_TRAVEL_DEG[NUM_MOTORS] = {
    0.0f,    // M1 — no limit
    180.0f,  // M2 shoulder
    223.0f,  // M3 elbow
    152.0f,  // M4 base
};

// 0 = no limit switch on this motor
static const uint8_t LIMIT_PIN[NUM_MOTORS] = {0, 7, 15, 6};

struct MotorConfig {
  uint8_t pulPin;
  uint8_t dirPin;
  unsigned int pulseUs;
  unsigned int stepDelayUs;
  bool invertDir;
};

MotorConfig motors[NUM_MOTORS] = {
    {4, 5, 1600, 2600, false},    // M1 wrist
    {9, 10, 1600, 2600, true},    // M2 shoulder
    {11, 12, 1600, 2600, false},  // M3 elbow
    {13, 14, 1600, 2600, false},  // M4 base
};

static const char *WIFI_SSID = WIFI_SSID_VALUE;
static const char *WIFI_PASS = WIFI_PASS_VALUE;
static const char *MDNS_HOST = MDNS_HOST_VALUE;

WebServer server(80);
volatile bool running[NUM_MOTORS] = {false, false, false, false};
volatile bool dirCw[NUM_MOTORS] = {true, true, true, true};

enum HomingState : uint8_t {
  HOME_IDLE = 0,
  HOME_SEEK_CCW,
  HOME_BACKOFF_CW,
  HOME_DONE,
  HOME_FAILED_MAX,
};

volatile HomingState homingState = HOME_IDLE;
volatile uint8_t homingMotor = 255;
volatile bool motorHomed[NUM_MOTORS] = {false, false, false, false};
volatile int32_t motorStepPos[NUM_MOTORS] = {0, 0, 0, 0};
uint32_t homingStepCount = 0;
uint32_t backoffRemaining = 0;
const char *homingFailMsg = nullptr;

static const uint8_t HOME_ALL_SEQ[] = {1, 2, 3};
static const uint8_t HOME_ALL_COUNT = 3;
uint8_t homeAllIdx = 0;
bool homeAllActive = false;

enum MoveState : uint8_t { MOVE_IDLE = 0, MOVE_RUNNING };
volatile MoveState moveState = MOVE_IDLE;
volatile int32_t moveRemaining[NUM_MOTORS] = {0, 0, 0, 0};
const char *moveFailMsg = nullptr;

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>4 Motor Test</title>
<style>
body{margin:0;min-height:100vh;font-family:system-ui,sans-serif;background:#111;color:#eee;padding:1rem;touch-action:manipulation}
h1{font-size:1.2rem;margin:0 0 .25rem}
.sub{color:#888;font-size:.85rem;margin:0 0 1rem}
.panel{max-width:360px;margin:0 auto 1rem;padding:1rem;background:#1a1a1a;border-radius:12px}
.panel h2{font-size:1rem;margin:0 0 .5rem;color:#ccc}
.pins{font-size:.75rem;color:#666;margin:0 0 .5rem}
.set{margin:.75rem 0;padding:.75rem 0 0;border-top:1px solid #333}
.set label{display:flex;justify-content:space-between;font-size:.75rem;color:#aaa;margin-bottom:.2rem}
.set input[type=range]{width:100%;margin:0 0 .6rem}
.set .chk{display:flex;align-items:center;gap:.5rem;font-size:.8rem;color:#bbb;margin-top:.25rem}
.limbox{display:flex;align-items:center;gap:.75rem;padding:.75rem;margin:0 0 .75rem;background:#0d0d0d;border-radius:10px;border:1px solid #333}
.led{width:2.25rem;height:2.25rem;border-radius:50%;flex-shrink:0;background:#333}
.led.open{background:#22c55e;box-shadow:0 0 12px #22c55e88}
.led.pressed{background:#ef4444;box-shadow:0 0 14px #ef4444aa;animation:pulse .5s ease infinite alternate}
@keyframes pulse{from{opacity:1}to{opacity:.65}}
.limtxt{font-size:.9rem;font-weight:700}
.limsub{font-size:.72rem;color:#888;margin-top:.15rem}
.btn{width:100%;padding:1rem;margin-bottom:.5rem;border:none;border-radius:10px;font-size:1rem;font-weight:700;color:#fff;touch-action:none}
.btn:active{filter:brightness(1.15)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.cw{background:#1a7f4e}.ccw{background:#b33a3a}
.cal{background:#1a4a7f}.hall{background:#5a2d82}
.top{max-width:360px;margin:0 auto 1rem;padding:1rem;background:#1a2a1a;border-radius:12px;border:1px solid #2a4a2a}
.top h2{font-size:1rem;margin:0 0 .5rem;color:#8f8}
.gst{font-size:.85rem;color:#9cf;margin-top:.5rem;min-height:1.2rem}
.st{color:#6cf;font-size:.8rem;min-height:1rem}
.movegrid{display:grid;gap:.5rem;margin:0 0 .75rem}
.movegrid label{font-size:.8rem;color:#aaa;display:flex;flex-direction:column;gap:.2rem}
.movegrid input{padding:.5rem;border-radius:8px;border:1px solid #444;background:#111;color:#eee;font-size:1rem}
</style></head><body>
<h1>4 motor test</h1>
<p class="sub">Step 2 · Move API · v5.9 · home WiFi</p>
<div class="top">
<h2>Homing test</h2>
<p style="font-size:.8rem;color:#888;margin:0 0 .75rem">Homes shoulder→elbow→base (M2→M3→M4). M1 wrist has no limit.</p>
<button class="btn hall" id="homeAll">Home all (shoulder→elbow→base)</button>
<div class="gst" id="gStatus">Status: not homed</div>
</div>
<div class="top" style="background:#1a1a2a;border-color:#2a2a4a">
<h2>Move test</h2>
<p style="font-size:.8rem;color:#888;margin:0 0 .5rem">Absolute target steps (M2–M4 must be homed). Leave blank to skip a joint.</p>
<div class="movegrid">
<label>M1 wrist <input type="number" id="t0" placeholder="steps"></label>
<label>M2 shoulder <input type="number" id="t1" placeholder="steps"></label>
<label>M3 elbow <input type="number" id="t2" placeholder="steps"></label>
<label>M4 base <input type="number" id="t3" placeholder="steps"></label>
</div>
<button class="btn hall" id="moveBtn">Move to targets</button>
<div class="gst" id="moveStatus">Move: idle</div>
</div>
<div id="panels"></div>
<script>
const motorDefs=[
  {m:0,n:1,pins:'PUL=4 · DIR=5 · wrist (no limit)'},
  {m:1,n:2,pins:'PUL=9 · DIR=10 · shoulder',limitGpio:7},
  {m:2,n:3,pins:'PUL=11 · DIR=12 · elbow',limitGpio:6},
  {m:3,n:4,pins:'PUL=13 · DIR=14 · base',limitGpio:15}
];
const panels=document.getElementById('panels');
let active=[null,null,null,null];
let runToken=[0,0,0,0];
let saveTimers={};
let homingActive=false;
let movingActive=false;

function settingsHtml(m){
  return `<div class="set">
    <label><span>Step delay</span><span id="dval${m}">2600 µs</span></label>
    <input type="range" id="delay${m}" min="200" max="4000" step="50" value="2600" data-m="${m}">
    <label><span>Pulse width</span><span id="pval${m}">1600 µs</span></label>
    <input type="range" id="pulse${m}" min="100" max="2500" step="50" value="1600" data-m="${m}">
    <label class="chk"><input type="checkbox" id="inv${m}" data-m="${m}"> Invert direction</label>
  </div>`;
}

function limitHtml(m,gpio){
  return `<div class="limbox"><div class="led open" id="led${m}"></div><div>
    <div class="limtxt" id="limLabel${m}">Limit: …</div>
    <div class="limsub" id="limRaw${m}">GPIO${gpio}</div></div></div>
    <button class="btn cal" id="cal${m}" data-m="${m}">Calibrate home (CCW to limit)</button>`;
}

motorDefs.forEach(def=>{
  const el=document.createElement('div');
  el.className='panel';
  const extra=def.limitGpio?limitHtml(def.m,def.limitGpio):'';
  el.innerHTML=`<h2>Motor ${def.n}</h2><p class="pins">${def.pins}</p>${settingsHtml(def.m)}${extra}
    <button class="btn cw" data-m="${def.m}" data-d="cw">Clockwise</button>
    <button class="btn ccw" data-m="${def.m}" data-d="ccw">Counter-clockwise</button>
    <div class="st" id="s${def.m}">Idle</div>`;
  panels.appendChild(el);
});

function start(m,d){
  const tok=++runToken[m];
  active[m]=d;
  fetch('/start?motor='+m+'&dir='+d,{method:'POST'}).then(()=>{
    if(active[m]!==d||runToken[m]!==tok){
      fetch('/stop?motor='+m,{method:'POST'});
    }
  }).catch(()=>{});
  document.getElementById('s'+m).textContent=d==='cw'?'Running CW':'Running CCW';
}
function stop(m){
  if(active[m]===null)return;
  runToken[m]++;
  active[m]=null;
  fetch('/stop?motor='+m,{method:'POST'}).catch(()=>{});
  document.getElementById('s'+m).textContent='Idle';
}
function stopAll(){
  [0,1,2,3].forEach(m=>{if(active[m]!==null)stop(m);});
  fetch('/stop_all',{method:'POST'}).catch(()=>{});
}

document.querySelectorAll('.btn[data-m][data-d]').forEach(btn=>{
  const m=+btn.dataset.m,d=btn.dataset.d;
  const down=e=>{e.preventDefault();if(active[m]||homingActive||movingActive)return;active[m]=d;start(m,d);};
  const up=e=>{e.preventDefault();if(active[m]===d)stop(m);};
  btn.addEventListener('pointerdown',down);
  btn.addEventListener('pointerup',up);
  btn.addEventListener('pointercancel',up);
  btn.addEventListener('pointerleave',up);
});
window.addEventListener('pointerup',stopAll);
window.addEventListener('pointercancel',stopAll);
window.addEventListener('blur',stopAll);

document.querySelectorAll('.btn.cal').forEach(btn=>{
  btn.addEventListener('click',async()=>{
    const m=+btn.dataset.m;
    if(active[m])stop(m);
    homingActive=true;
    document.getElementById('s'+m).textContent='Calibrating…';
    await fetch('/calibrate?motor='+m,{method:'POST'});
  });
});

async function pushSettings(m){
  const delay=document.getElementById('delay'+m).value;
  const pulse=document.getElementById('pulse'+m).value;
  const invert=document.getElementById('inv'+m).checked?1:0;
  document.getElementById('dval'+m).textContent=delay+' µs';
  document.getElementById('pval'+m).textContent=pulse+' µs';
  await fetch('/settings?motor='+m+'&delay='+delay+'&pulse='+pulse+'&invert='+invert,{method:'POST'});
}
document.querySelectorAll('input[data-m]').forEach(inp=>{
  const m=+inp.dataset.m;
  const go=()=>{clearTimeout(saveTimers[m]);saveTimers[m]=setTimeout(()=>pushSettings(m),400);};
  inp.addEventListener('change',go);
});

async function loadSettings(){
  const r=await fetch('/settings');const arr=await r.json();
  arr.forEach((s,i)=>{
    document.getElementById('delay'+i).value=s.delay;
    document.getElementById('pulse'+i).value=s.pulse;
    document.getElementById('inv'+i).checked=s.invert;
    document.getElementById('dval'+i).textContent=s.delay+' µs';
    document.getElementById('pval'+i).textContent=s.pulse+' µs';
  });
}
loadSettings();

document.getElementById('homeAll').addEventListener('click',async()=>{
  [0,1,2,3].forEach(m=>{if(active[m])stop(m);});
  homingActive=true;
  document.getElementById('gStatus').textContent='Status: homing…';
  await fetch('/home_all',{method:'POST'});
});

document.getElementById('moveBtn').addEventListener('click',async()=>{
  [0,1,2,3].forEach(m=>{if(active[m])stop(m);});
  let q='';
  for(let m=0;m<4;m++){
    const v=document.getElementById('t'+m).value.trim();
    if(v!=='')q+=(q?'&':'')+'m'+m+'='+encodeURIComponent(v);
  }
  if(!q){document.getElementById('moveStatus').textContent='Move: enter at least one target';return;}
  document.getElementById('moveStatus').textContent='Move: starting…';
  const r=await fetch('/move?'+q,{method:'POST'});
  const t=await r.text();
  if(!r.ok)document.getElementById('moveStatus').textContent='Move: FAILED — '+t;
});

function anyHeld(){return active[0]||active[1]||active[2]||active[3];}

async function pollGlobal(){
  if(anyHeld())return;
  try{
    const r=await fetch('/status');const d=await r.json();
    homingActive=d.homing;
    movingActive=d.moving;
    const ha=document.getElementById('homeAll');
    const mb=document.getElementById('moveBtn');
    if(ha)ha.disabled=d.homing||d.moving;
    if(mb)mb.disabled=d.homing||d.moving;
    let t='Status: ';
    if(d.homing)t+='homing M'+(d.homingMotor+1)+'…';
    else if(d.moving)t+='moving…';
    else if(d.allHomed)t+='all homed (M2–M4) · 0° at limit switch';
    else if(d.fail)t+='FAILED: '+d.fail;
  else{
      const parts=d.motors.map(m=>'M'+(m.id+1)+(m.homed?'✓':'—')+' '+m.steps+'st');
      t+=parts.join(' · ');
    }
    document.getElementById('gStatus').textContent=t;
    const ms=document.getElementById('moveStatus');
    if(ms){
      if(d.moving)ms.textContent='Move: running…';
      else if(d.moveFail)ms.textContent='Move: FAILED — '+d.moveFail;
      else if(!d.homing)ms.textContent='Move: idle · '+d.motors.map(m=>'M'+(m.id+1)+'='+m.steps).join(' ');
    }
    for(const m of d.motors){
      const def=motorDefs.find(x=>x.m===m.id);
      if(!def||!def.limitGpio)continue;
      const led=document.getElementById('led'+m.id);
      const limLabel=document.getElementById('limLabel'+m.id);
      const limRaw=document.getElementById('limRaw'+m.id);
      const st=document.getElementById('s'+m.id);
      const cal=document.getElementById('cal'+m.id);
      if(led)led.className='led '+(m.limitRaw?'pressed':'open');
      if(limLabel)limLabel.textContent=m.limitRaw?'LIMIT PRESSED':'Limit open (not pressed)';
      if(limRaw)limRaw.textContent='GPIO'+def.limitGpio+' raw:'+(m.limitRaw?'LOW':'HIGH')+(m.homed?' · homed':'');
      if(d.homing&&d.homingMotor===m.id){
        homingActive=true;
        if(cal)cal.disabled=true;
        if(st)st.textContent='Calibrating… '+(m.seekSteps||0)+' steps';
      }else{
        if(cal)cal.disabled=false;
        if(m.homed&&st&&st.textContent.startsWith('Calibrat'))st.textContent='Homed at 0°';
        if(d.fail==='max_steps'&&d.homingMotor===m.id&&st)st.textContent='Failed — never hit limit';
      }
    }
  }catch(e){}
}
setInterval(pollGlobal,250);pollGlobal();
</script></body></html>
)rawliteral";

bool hasLimit(uint8_t m) { return m < NUM_MOTORS && LIMIT_PIN[m] != 0; }

uint32_t halfMaxSteps(uint8_t m) {
  const float halfDeg = MAX_TRAVEL_DEG[m] * 0.5f;
  return (uint32_t)lroundf(halfDeg * STEPS_PER_DEGREE[m]);
}

unsigned int clampDelay(unsigned int v) {
  if (v < DELAY_MIN) return DELAY_MIN;
  if (v > DELAY_MAX) return DELAY_MAX;
  return v;
}

unsigned int clampPulse(unsigned int v) {
  if (v < PULSE_MIN) return PULSE_MIN;
  if (v > PULSE_MAX) return PULSE_MAX;
  return v;
}

bool limitRaw(uint8_t m) {
  if (!hasLimit(m)) return false;
  return digitalRead(LIMIT_PIN[m]) == LOW;
}

bool limitHomingHit(uint8_t m) {
  if (!hasLimit(m)) return false;
  for (uint8_t i = 0; i < LIMIT_HOME_HITS; i++) {
    if (digitalRead(LIMIT_PIN[m]) != LOW) return false;
    if (i + 1 < LIMIT_HOME_HITS) delayMicroseconds(LIMIT_HOME_GAP_US);
  }
  return true;
}

bool limitStablePressed(uint8_t m) {
  if (!hasLimit(m)) return false;
  for (uint8_t i = 0; i < LIMIT_DEBOUNCE_HITS; i++) {
    if (digitalRead(LIMIT_PIN[m]) != LOW) return false;
    delayMicroseconds(LIMIT_DEBOUNCE_GAP_US);
  }
  return true;
}

void setDirection(uint8_t m, bool cw) {
  bool level = cw;
  if (motors[m].invertDir) level = !level;
  digitalWrite(motors[m].dirPin, level ? HIGH : LOW);
}

void stepMotorTimed(uint8_t m, unsigned int pulseUs, unsigned int stepDelayUs) {
  digitalWrite(motors[m].pulPin, HIGH);
  delayMicroseconds(pulseUs);
  digitalWrite(motors[m].pulPin, LOW);
  delayMicroseconds(stepDelayUs);
}

// Homing step — polls limit during inter-step delay for faster switch detection.
bool homingSeekStep(uint8_t m) {
  digitalWrite(motors[m].pulPin, HIGH);
  delayMicroseconds(HOME_PULSE_US);
  digitalWrite(motors[m].pulPin, LOW);

  unsigned int elapsed = 0;
  while (elapsed < HOME_SEEK_DELAY_US) {
    if (homingStepCount >= HOME_MIN_SEEK_STEPS && limitHomingHit(m)) return false;
    const unsigned int chunk =
        (HOME_SEEK_DELAY_US - elapsed < HOME_LIMIT_POLL_US) ? (HOME_SEEK_DELAY_US - elapsed)
                                                            : HOME_LIMIT_POLL_US;
    delayMicroseconds(chunk);
    elapsed += chunk;
  }
  return true;
}

void stepMotor(uint8_t m) {
  stepMotorTimed(m, motors[m].pulseUs, motors[m].stepDelayUs);
}

void stopAllMotors() {
  for (uint8_t m = 0; m < NUM_MOTORS; m++) running[m] = false;
}

void webServerTask(void *pv) {
  (void)pv;
  for (;;) {
    server.handleClient();
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

bool allLimitMotorsHomed() {
  for (uint8_t i = 0; i < HOME_ALL_COUNT; i++) {
    if (!motorHomed[HOME_ALL_SEQ[i]]) return false;
  }
  return true;
}

void beginHomingMotor(uint8_t m);

void startBackoffFromLimit(uint8_t m) {
  motorStepPos[m] = 0;
  setDirection(m, true);
  delayMicroseconds(20);
  backoffRemaining = halfMaxSteps(m);
  homingState = HOME_BACKOFF_CW;
  const float halfDeg = MAX_TRAVEL_DEG[m] * 0.5f;
  Serial.printf("M%u limit hit — moving to %.1f deg (%lu steps CW)\n", m + 1, halfDeg,
                (unsigned long)backoffRemaining);
}

void finishHomingMotor(uint8_t m) {
  motorHomed[m] = true;
  Serial.printf("M%u homed — 0 at limit, now at %ld steps\n", m + 1, (long)motorStepPos[m]);
  if (homeAllActive && homeAllIdx + 1 < HOME_ALL_COUNT) {
    homeAllIdx++;
    beginHomingMotor(HOME_ALL_SEQ[homeAllIdx]);
  } else {
    homeAllActive = false;
    homingState = HOME_IDLE;
    homingMotor = 255;
    if (allLimitMotorsHomed()) Serial.println("Home all complete");
  }
}

void beginHomingMotor(uint8_t m) {
  homingMotor = m;
  homingStepCount = 0;
  motorHomed[m] = false;
  homingFailMsg = nullptr;

  if (limitHomingHit(m)) {
    startBackoffFromLimit(m);
    return;
  }

  setDirection(m, false);
  delayMicroseconds(20);
  homingState = HOME_SEEK_CCW;
  Serial.printf("M%u homing: CCW to GPIO %u\n", m + 1, LIMIT_PIN[m]);
}

void startHoming(uint8_t m) {
  if (!hasLimit(m) || homingState != HOME_IDLE || moveState != MOVE_IDLE) return;
  stopAllMotors();
  homeAllActive = false;
  beginHomingMotor(m);
}

void startHomeAll() {
  if (homingState != HOME_IDLE || moveState != MOVE_IDLE) return;
  stopAllMotors();
  homeAllActive = true;
  homeAllIdx = 0;
  homingFailMsg = nullptr;
  for (uint8_t i = 0; i < HOME_ALL_COUNT; i++) {
    motorHomed[HOME_ALL_SEQ[i]] = false;
    motorStepPos[HOME_ALL_SEQ[i]] = 0;
  }
  Serial.println("Home all: M2 → M3 → M4");
  beginHomingMotor(HOME_ALL_SEQ[0]);
}

void tickHoming() {
  if (homingState == HOME_IDLE || homingMotor >= NUM_MOTORS) return;
  const uint8_t m = homingMotor;

  if (homingState == HOME_SEEK_CCW) {
    if (homingStepCount >= HOME_MIN_SEEK_STEPS && limitHomingHit(m)) {
      startBackoffFromLimit(m);
      return;
    }
    if (homingStepCount >= HOME_MAX_SEEK_STEPS) {
      homingFailMsg = "max_steps";
      homingState = HOME_FAILED_MAX;
      return;
    }
    if (!homingSeekStep(m)) {
      startBackoffFromLimit(m);
      return;
    }
    homingStepCount++;
    return;
  }

  if (homingState == HOME_BACKOFF_CW) {
    if (backoffRemaining == 0) {
      finishHomingMotor(m);
      return;
    }
    stepMotorTimed(m, HOME_PULSE_US, HOME_BACKOFF_DELAY_US);
    backoffRemaining--;
    motorStepPos[m]++;
    return;
  }

  if (homingState == HOME_FAILED_MAX) {
    homeAllActive = false;
    homingState = HOME_IDLE;
    homingMotor = 255;
  }
}

bool parseMotorTarget(uint8_t m, int32_t &targetOut) {
  char keySteps[4];
  char keyDeg[8];
  snprintf(keySteps, sizeof(keySteps), "m%u", m);
  snprintf(keyDeg, sizeof(keyDeg), "m%u_deg", m);

  if (server.hasArg(keyDeg)) {
    float deg = server.arg(keyDeg).toFloat();
    targetOut = (int32_t)lroundf(deg * STEPS_PER_DEGREE[m]);
    return true;
  }
  if (server.hasArg(keySteps)) {
    targetOut = (int32_t)server.arg(keySteps).toInt();
    return true;
  }
  return false;
}

bool startMove() {
  if (homingState != HOME_IDLE) {
    moveFailMsg = "homing_active";
    return false;
  }
  if (moveState == MOVE_RUNNING) {
    moveFailMsg = "busy";
    return false;
  }

  stopAllMotors();
  moveFailMsg = nullptr;

  bool any = false;
  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    moveRemaining[m] = 0;
    int32_t target = 0;
    if (!parseMotorTarget(m, target)) continue;

    if (hasLimit(m) && !motorHomed[m]) {
      moveFailMsg = "not_homed";
      return false;
    }

    int32_t delta = target - motorStepPos[m];
    if (delta == 0) continue;

    moveRemaining[m] = delta;
    any = true;
    Serial.printf("M%u move: %ld -> %ld (%ld steps)\n", m + 1, (long)motorStepPos[m],
                  (long)target, (long)delta);
  }

  if (!any) return true;

  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    if (moveRemaining[m] != 0) {
      setDirection(m, moveRemaining[m] > 0);
      delayMicroseconds(20);
    }
  }
  moveState = MOVE_RUNNING;
  return true;
}

void tickMove() {
  if (moveState != MOVE_RUNNING) return;

  bool anyRemaining = false;
  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    if (moveRemaining[m] == 0) continue;
    anyRemaining = true;
    bool cw = moveRemaining[m] > 0;
    setDirection(m, cw);
    stepMotor(m);
    motorStepPos[m] += cw ? 1 : -1;
    if (cw)
      moveRemaining[m]--;
    else
      moveRemaining[m]++;
  }

  anyRemaining = false;
  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    if (moveRemaining[m] != 0) anyRemaining = true;
  }
  if (!anyRemaining) {
    moveState = MOVE_IDLE;
    Serial.println("Move complete");
  }
}

void setupLimitPins() {
  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    if (hasLimit(m)) pinMode(LIMIT_PIN[m], INPUT_PULLUP);
  }
}

void connectToHomeWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(WIFI_PS_NONE);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("Connecting to \"%s\"...\n", WIFI_SSID);
  uint8_t tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 60) {
    delay(500);
    Serial.print('.');
    tries++;
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi failed — check SSID/password");
    return;
  }
  Serial.print("IP: http://");
  Serial.println(WiFi.localIP());
  if (MDNS.begin(MDNS_HOST)) {
    Serial.printf("mDNS: http://%s.local\n", MDNS_HOST);
  } else {
    Serial.println("mDNS start failed — use IP address");
  }
}

void setup() {
  Serial.begin(115200);
  setupLimitPins();

  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    pinMode(motors[m].pulPin, OUTPUT);
    pinMode(motors[m].dirPin, OUTPUT);
    digitalWrite(motors[m].pulPin, LOW);
    digitalWrite(motors[m].dirPin, LOW);
  }

  connectToHomeWifi();

  Serial.println("\n=== Step 2 · Move API v5.9 (home WiFi) ===");
  Serial.printf("M2 limit GPIO7 · M3 limit GPIO15 · M4 limit GPIO6\n");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Web UI: http://");
    Serial.print(MDNS_HOST);
    Serial.print(".local  (");
    Serial.print(WiFi.localIP());
    Serial.println(')');
  }

  server.on("/", []() { server.send_P(200, "text/html", INDEX_HTML); });

  server.on("/settings", HTTP_GET, []() {
    String json = "[";
    for (uint8_t m = 0; m < NUM_MOTORS; m++) {
      if (m) json += ',';
      json += "{\"delay\":";
      json += motors[m].stepDelayUs;
      json += ",\"pulse\":";
      json += motors[m].pulseUs;
      json += ",\"invert\":";
      json += motors[m].invertDir ? "true" : "false";
      json += "}";
    }
    json += "]";
    server.send(200, "application/json", json);
  });

  server.on("/settings", HTTP_POST, []() {
    if (!server.hasArg("motor")) {
      server.send(400, "text/plain", "missing motor");
      return;
    }
    uint8_t m = (uint8_t)server.arg("motor").toInt();
    if (m >= NUM_MOTORS) {
      server.send(400, "text/plain", "bad motor");
      return;
    }
    if (server.hasArg("delay")) {
      motors[m].stepDelayUs = clampDelay((unsigned int)server.arg("delay").toInt());
    }
    if (server.hasArg("pulse")) {
      motors[m].pulseUs = clampPulse((unsigned int)server.arg("pulse").toInt());
    }
    if (server.hasArg("invert")) {
      motors[m].invertDir = server.arg("invert").toInt() != 0;
    }
    server.send(200, "text/plain", "OK");
  });

  server.on("/start", HTTP_POST, []() {
    if (homingState != HOME_IDLE) {
      server.send(409, "text/plain", "homing active");
      return;
    }
    if (moveState != MOVE_IDLE) {
      server.send(409, "text/plain", "move active");
      return;
    }
    if (!server.hasArg("motor")) {
      server.send(400, "text/plain", "missing motor");
      return;
    }
    uint8_t m = (uint8_t)server.arg("motor").toInt();
    if (m >= NUM_MOTORS) {
      server.send(400, "text/plain", "bad motor");
      return;
    }
    dirCw[m] = !server.hasArg("dir") || server.arg("dir") != "ccw";
    setDirection(m, dirCw[m]);
    delayMicroseconds(20);
    running[m] = true;
    server.send(200, "text/plain", "OK");
  });

  server.on("/stop", HTTP_POST, []() {
    if (!server.hasArg("motor")) {
      server.send(400, "text/plain", "missing motor");
      return;
    }
    uint8_t m = (uint8_t)server.arg("motor").toInt();
    if (m >= NUM_MOTORS) {
      server.send(400, "text/plain", "bad motor");
      return;
    }
    running[m] = false;
    server.send(200, "text/plain", "OK");
  });

  server.on("/stop_all", HTTP_POST, []() {
    stopAllMotors();
    server.send(200, "text/plain", "OK");
  });

  server.on("/home_all", HTTP_POST, []() {
    if (moveState != MOVE_IDLE) {
      server.send(409, "text/plain", "move active");
      return;
    }
    startHomeAll();
    server.send(200, "text/plain", "OK");
  });

  server.on("/move", HTTP_POST, []() {
    if (startMove()) {
      server.send(200, "text/plain", "OK");
    } else {
      const char *msg = moveFailMsg ? moveFailMsg : "failed";
      server.send(409, "text/plain", msg);
    }
  });

  server.on("/status", []() {
    bool homing = homingState == HOME_SEEK_CCW || homingState == HOME_BACKOFF_CW;
    bool moving = moveState == MOVE_RUNNING;
    String json = "{\"homing\":";
    json += homing ? "true" : "false";
    json += ",\"moving\":";
    json += moving ? "true" : "false";
    json += ",\"homingMotor\":";
    json += homing ? homingMotor : 255;
    json += ",\"allHomed\":";
    json += allLimitMotorsHomed() ? "true" : "false";
    json += ",\"fail\":";
    if (homingFailMsg) {
      json += "\"";
      json += homingFailMsg;
      json += "\"";
    } else {
      json += "null";
    }
    json += ",\"moveFail\":";
    if (moveFailMsg) {
      json += "\"";
      json += moveFailMsg;
      json += "\"";
    } else {
      json += "null";
    }
    json += ",\"wifi\":{";
    json += "\"connected\":";
    json += WiFi.status() == WL_CONNECTED ? "true" : "false";
    json += ",\"ip\":\"";
    json += WiFi.localIP().toString();
    json += "\",\"host\":\"";
    json += MDNS_HOST;
    json += ".local\",\"ssid\":\"";
    json += WIFI_SSID;
    json += "\"";
    json += "}";
    json += ",\"motors\":[";
    for (uint8_t m = 0; m < NUM_MOTORS; m++) {
      if (m) json += ',';
      json += "{\"id\":";
      json += m;
      json += ",\"homed\":";
      json += motorHomed[m] ? "true" : "false";
      json += ",\"steps\":";
      json += motorStepPos[m];
      json += ",\"hasLimit\":";
      json += hasLimit(m) ? "true" : "false";
      json += ",\"limitRaw\":";
      if (hasLimit(m))
        json += limitRaw(m) ? "true" : "false";
      else
        json += "null";
      json += ",\"seekSteps\":";
      json += (homing && homingMotor == m) ? homingStepCount : 0;
      json += ",\"running\":";
      json += running[m] ? "true" : "false";
      json += "}";
    }
    json += "]}";
    server.send(200, "application/json", json);
  });

  server.on("/calibrate", HTTP_POST, []() {
    if (moveState != MOVE_IDLE) {
      server.send(409, "text/plain", "move active");
      return;
    }
    if (!server.hasArg("motor")) {
      server.send(400, "text/plain", "missing motor");
      return;
    }
    uint8_t m = (uint8_t)server.arg("motor").toInt();
    if (!hasLimit(m)) {
      server.send(400, "text/plain", "no limit on motor");
      return;
    }
    startHoming(m);
    server.send(200, "text/plain", "OK");
  });

  server.on("/calibrate_m3", HTTP_POST, []() {
    startHoming(2);
    server.send(200, "text/plain", "OK");
  });

  server.on("/status_limit", []() {
    if (!server.hasArg("motor")) {
      server.send(400, "text/plain", "missing motor");
      return;
    }
    uint8_t m = (uint8_t)server.arg("motor").toInt();
    if (!hasLimit(m)) {
      server.send(400, "text/plain", "no limit");
      return;
    }
    bool homing = (homingMotor == m) &&
                  (homingState == HOME_SEEK_CCW || homingState == HOME_BACKOFF_CW);
    bool raw = limitRaw(m);
    const char *fail = (homingMotor == m) ? homingFailMsg : nullptr;

    String json = "{\"raw\":";
    json += raw ? "true" : "false";
    json += ",\"limit\":";
    json += raw ? "true" : "false";
    json += ",\"homing\":";
    json += homing ? "true" : "false";
    json += ",\"homed\":";
    json += motorHomed[m] ? "true" : "false";
    json += ",\"failed\":";
    if (fail) {
      json += "\"";
      json += fail;
      json += "\"";
    } else {
      json += "null";
    }
    json += ",\"seekSteps\":";
    json += (homingMotor == m) ? homingStepCount : 0;
    json += "}";
    server.send(200, "application/json", json);
  });

  server.on("/status_m3", []() {
    server.sendHeader("Location", "/status_limit?motor=2");
    server.send(302, "text/plain", "moved");
  });

  server.begin();
  xTaskCreatePinnedToCore(webServerTask, "web", 8192, NULL, 2, NULL, 0);
}

void loop() {
  tickHoming();

  if (homingState != HOME_IDLE) return;

  tickMove();
  if (moveState != MOVE_IDLE) return;

  for (uint8_t m = 0; m < NUM_MOTORS; m++) {
    if (running[m]) {
      stepMotor(m);
      motorStepPos[m] += dirCw[m] ? 1 : -1;
    }
  }
}
