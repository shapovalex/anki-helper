# Pronunciation: Mic Level Indicator & Recording Replay

**Date:** 2026-05-08  
**Scope:** Frontend only (`static/pronunciation.html`) — no backend changes.

---

## Problem

The pronunciation test gives no feedback that the browser is actually capturing audio. Users cannot tell if the microphone is working until they see assessment results. There is also no way to listen back to the recording to understand what Azure received.

---

## Features

### 1. Microphone Level Indicator

A real-time volume bar shown during recording that proves the browser is hearing input.

**Implementation:**

- In `startRecording()`, after obtaining the mic `stream`, create an `AudioContext`, connect a `MediaStreamSourceNode` → `AnalyserNode`.
- Start a `requestAnimationFrame` loop that calls `analyser.getByteFrequencyData()`, averages the values to a 0–100 volume level, and sets the `width` of `.mic-bar-fill` proportionally.
- In `stopRecording()`, cancel the animation frame, close the `AudioContext`, and reset the bar to 0.

**UI:** A thin bar (`4px` tall, full-width) placed directly below the record button. No label. Moves only when real audio input is detected.

### 2. Recording Replay

A button in the results section that plays back the last recording.

**Implementation:**

- Store the recorded `Blob` in a module-level variable `lastRecordingBlob` after `stopRecording()` builds it.
- Clear `lastRecordingBlob` at the start of each new recording.
- In the results section, add a "▶ Play back recording" button alongside the existing "🎤 Record Again" button.
- On click: create an object URL from `lastRecordingBlob`, set it as `src` on a hidden `<audio>` element, call `.play()`, and revoke the URL on `onended`.
- The button is hidden when `lastRecordingBlob` is null (i.e., before any recording or after a new one starts).

---

## Affected Files

- `static/pronunciation.html` — all changes are here

---

## Out of Scope

- Waveform / canvas visualisation
- Replay before submission
- Any backend changes
