# Pronunciation: Mic Level Indicator & Recording Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real-time microphone volume bar during recording and a "Play back recording" button in the results section of the pronunciation practice page.

**Architecture:** All changes are client-side in `static/pronunciation.html`. The mic bar uses `AudioContext` + `AnalyserNode` to read live audio levels from the existing mic stream, driving a CSS width via `requestAnimationFrame`. The replay feature stores the last recorded `Blob` in a module-level variable and plays it back via a temporary object URL.

**Tech Stack:** Vanilla JS, Web Audio API (`AudioContext`, `AnalyserNode`), `MediaRecorder` (already in use), HTML/CSS

---

### Task 1: Add mic bar HTML and CSS

**Files:**
- Modify: `static/pronunciation.html` (CSS block and HTML structure)

There are no automated frontend tests for this project. Each task includes a manual verification step instead.

- [ ] **Step 1: Add CSS for the mic bar**

In the `<style>` block (after `.record-status` rule, around line 79), add:

```css
.mic-bar {
    height: 4px;
    background: var(--surface-2, #2a2a2a);
    border-radius: 2px;
    margin: 0.3rem 0 0.2rem;
    overflow: hidden;
}
.mic-bar-fill {
    height: 100%;
    width: 0%;
    background: var(--primary, #5b8dee);
    border-radius: 2px;
    transition: width 0.05s linear;
}
```

- [ ] **Step 2: Add mic bar HTML below the record button**

Replace this block (around line 138–139):

```html
<button id="record-btn" class="btn-primary btn-full">🎤 Hold to Record</button>
<p class="record-status" id="record-status"></p>
```

With:

```html
<button id="record-btn" class="btn-primary btn-full">🎤 Hold to Record</button>
<div class="mic-bar"><div class="mic-bar-fill" id="mic-bar-fill"></div></div>
<p class="record-status" id="record-status"></p>
```

- [ ] **Step 3: Manually verify the bar renders**

Start the dev server:
```bash
uv run uvicorn app.main:app --reload
```
Open `http://localhost:8000/pronunciation` in the browser. The mic bar should be visible as a thin dark strip below the record button (0% width = invisible fill, which is correct at this stage).

- [ ] **Step 4: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: add mic level bar HTML and CSS"
```

---

### Task 2: Wire up Web Audio to animate the mic bar during recording

**Files:**
- Modify: `static/pronunciation.html` (JS `startRecording` and `stopRecording` functions)

- [ ] **Step 1: Add module-level variables for Web Audio state**

In the JS block, find the existing variable declarations (around line 218):

```js
let mediaRecorder   = null;
let audioChunks     = [];
```

Add two more variables after them:

```js
let audioContext    = null;
let micLevelRafId   = null;
```

- [ ] **Step 2: Add the mic level animation loop helper**

Add this function after the `scoreClass` function (around line 229):

```js
function startMicLevelLoop(stream) {
    audioContext = new AudioContext();
    const source   = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const fill = document.getElementById('mic-bar-fill');

    function tick() {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((s, v) => s + v, 0) / data.length;
        fill.style.width = Math.min(100, (avg / 128) * 100) + '%';
        micLevelRafId = requestAnimationFrame(tick);
    }
    micLevelRafId = requestAnimationFrame(tick);
}

function stopMicLevelLoop() {
    if (micLevelRafId) { cancelAnimationFrame(micLevelRafId); micLevelRafId = null; }
    if (audioContext)  { audioContext.close(); audioContext = null; }
    const fill = document.getElementById('mic-bar-fill');
    if (fill) fill.style.width = '0%';
}
```

- [ ] **Step 3: Call `startMicLevelLoop` in `startRecording` after obtaining the stream**

Find `startRecording` (around line 363). After the line:

```js
stream = await navigator.mediaDevices.getUserMedia({ audio: true });
```

Add:

```js
startMicLevelLoop(stream);
```

- [ ] **Step 4: Call `stopMicLevelLoop` in `stopRecording`**

Find `stopRecording` (around line 381). After the line:

```js
mediaRecorder.stream.getTracks().forEach(t => t.stop());
```

Add:

```js
stopMicLevelLoop();
```

- [ ] **Step 5: Manually verify the mic bar animates**

With the dev server running, go to `http://localhost:8000/pronunciation`, select a deck, click Start Practicing, then hold the record button and speak. The blue bar should grow and shrink in response to your voice. Releasing the button should reset it to 0. If the bar doesn't move, open DevTools → Console and check for errors (`AudioContext` creation failures, etc.).

- [ ] **Step 6: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: animate mic level bar using Web Audio analyser"
```

---

### Task 3: Store the last recording and add a replay button

**Files:**
- Modify: `static/pronunciation.html` (JS variable, `startRecording`/`stopRecording`, HTML results section)

- [ ] **Step 1: Add `lastRecordingBlob` module-level variable**

In the variable declarations block (around line 218), add:

```js
let lastRecordingBlob = null;
```

- [ ] **Step 2: Clear `lastRecordingBlob` at the start of each new recording**

In `startRecording`, right after the early-return guard:

```js
if (mediaRecorder && mediaRecorder.state === 'recording') return;
```

Add:

```js
lastRecordingBlob = null;
```

- [ ] **Step 3: Store the blob after building it in `stopRecording`**

In `stopRecording`, find:

```js
const blob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
```

Replace with:

```js
const blob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
lastRecordingBlob = blob;
```

- [ ] **Step 4: Add the replay button and hidden audio element to the results section HTML**

Find the existing "Record Again" button in the results section (around line 163):

```html
<button class="btn-secondary btn-full" style="margin-bottom:1rem;" onclick="resetForRecording()">🎤 Record Again</button>
```

Replace with:

```html
<div style="display:flex; gap:0.5rem; margin-bottom:1rem;">
    <button class="btn-secondary" style="flex:1;" onclick="resetForRecording()">🎤 Record Again</button>
    <button class="btn-secondary" id="replay-btn" style="flex:1; display:none;" onclick="playBackRecording()">▶ Play back recording</button>
</div>
<audio id="replay-audio" style="display:none;"></audio>
```

- [ ] **Step 5: Add `playBackRecording` function**

Add this function after `resetForRecording` (around line 534):

```js
function playBackRecording() {
    if (!lastRecordingBlob) return;
    const url = URL.createObjectURL(lastRecordingBlob);
    const audio = document.getElementById('replay-audio');
    audio.src = url;
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play();
}
```

- [ ] **Step 6: Show the replay button when results are displayed**

In `showResults` (around line 426), at the very end of the function (after the recommendations reset block), add:

```js
const replayBtn = document.getElementById('replay-btn');
if (replayBtn) replayBtn.style.display = lastRecordingBlob ? '' : 'none';
```

- [ ] **Step 7: Hide the replay button in `resetForRecording`**

In `resetForRecording` (around line 534), add at the end:

```js
const replayBtn = document.getElementById('replay-btn');
if (replayBtn) replayBtn.style.display = 'none';
```

- [ ] **Step 8: Manually verify replay**

With the dev server running, go to the pronunciation practice page, record something, release the button, and wait for results. A "▶ Play back recording" button should appear next to "🎤 Record Again". Click it — you should hear what you recorded. Click "🎤 Record Again" — the replay button should disappear until the next assessment completes.

- [ ] **Step 9: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: add play-back-recording button in results section"
```
