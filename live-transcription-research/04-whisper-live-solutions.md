# Whisper-Based Live Transcription Solutions Research

**Date:** January 11, 2026
**Purpose:** Research for Claude Code CLI live transcription integration
**Note:** This research is compiled from knowledge cutoff data (May 2025). Web search was unavailable during compilation.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Whisper Implementations](#core-whisper-implementations)
3. [Live/Real-Time Solutions](#livereal-time-solutions)
4. [Voice Activity Detection Integration](#voice-activity-detection-integration)
5. [CLI-Focused Tools](#cli-focused-tools)
6. [Feasibility Assessment](#feasibility-assessment)
7. [Recommendations for Claude Code CLI](#recommendations-for-claude-code-cli)

---

## Executive Summary

Whisper, OpenAI's speech recognition model, was designed for batch processing (30-second windows) rather than real-time streaming. However, the community has developed several approaches to enable live transcription:

1. **whisper.cpp** - C++ port with native streaming support
2. **faster-whisper** - CTranslate2-based Python implementation (4x faster)
3. **WhisperLive** - WebSocket-based real-time server
4. **whisper-streaming** - Sliding window approach for streaming
5. **Various VAD + Whisper combos** - Silero VAD, WebRTC VAD integration

---

## Core Whisper Implementations

### 1. OpenAI Whisper (Original)

**Repository:** https://github.com/openai/whisper

**Characteristics:**
- Written in Python with PyTorch
- Processes audio in 30-second windows
- Not designed for real-time use
- High accuracy, GPU-accelerated
- Models: tiny, base, small, medium, large, turbo

**Latency:** ~2-30 seconds depending on model and hardware

**Code Example (Batch Processing):**
```python
import whisper

model = whisper.load_model("turbo")
result = model.transcribe("audio.mp3")
print(result["text"])
```

**Limitation for Live Use:** Processes entire audio files; no native streaming support.

---

### 2. faster-whisper

**Repository:** https://github.com/SYSTRAN/faster-whisper

**Key Features:**
- Uses CTranslate2 for inference (4x faster than original)
- Lower memory usage
- INT8 quantization support
- Batched inference support
- Word-level timestamps

**Installation:**
```bash
pip install faster-whisper
```

**Code Example:**
```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v2", device="cuda", compute_type="float16")
segments, info = model.transcribe("audio.mp3", beam_size=5)

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

**Streaming Potential:** The segment-based output allows for pseudo-streaming when combined with audio chunking.

---

### 3. whisper.cpp

**Repository:** https://github.com/ggerganov/whisper.cpp

**Key Features:**
- Pure C/C++ implementation
- No Python/PyTorch dependency
- CPU-optimized (SIMD, Apple Silicon optimized)
- Native real-time streaming support (`stream` example)
- Memory-mapped models
- WASM support for browser

**Native Streaming Tool:**
```bash
# Build
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make

# Download model
./models/download-ggml-model.sh base.en

# Real-time microphone transcription
./stream -m models/ggml-base.en.bin -t 8 --step 500 --length 5000
```

**Stream Parameters:**
- `--step`: Audio step size in milliseconds (default: 3000)
- `--length`: Audio length in milliseconds (default: 10000)
- `-t`: Number of threads
- `--vad-thold`: VAD threshold for speech detection

**Latency:** 500ms - 3 seconds depending on configuration

**Feasibility: HIGH** - Native streaming support, excellent for CLI integration.

---

## Live/Real-Time Solutions

### 4. WhisperLive (Collabora)

**Repository:** https://github.com/collabora/WhisperLive

**Architecture:**
- Client-server model via WebSocket
- Supports faster-whisper backend
- GPU acceleration support
- Word-level timestamps
- Multi-client support

**Installation:**
```bash
pip install whisper-live
```

**Server:**
```python
from whisper_live.server import TranscriptionServer

server = TranscriptionServer()
server.run("0.0.0.0", 9090)
```

**Client:**
```python
from whisper_live.client import TranscriptionClient

client = TranscriptionClient(
    "localhost", 9090,
    lang="en",
    translate=False,
    model="small"
)
client.start()
```

**Features:**
- Handles audio streaming
- Automatic VAD integration
- Continuous transcription
- Low-latency mode available

**Feasibility: HIGH** - Excellent for integration, handles streaming complexity.

---

### 5. whisper-streaming

**Repository:** https://github.com/ufal/whisper_streaming

**Approach:** Local Agreement Policy for online/streaming ASR

**Key Concept:**
- Processes audio in overlapping windows
- Uses "local agreement" to output stable text
- Delays output until confident about transcription

**Installation:**
```bash
pip install whisper-streaming
```

**Usage:**
```python
from whisper_streaming import WhisperStreaming

# Configure streaming whisper
streamer = WhisperStreaming(
    model="base",
    language="en",
    chunk_size=1.0  # 1 second chunks
)

# Process audio chunks
for chunk in audio_stream:
    result = streamer.process(chunk)
    if result:
        print(result)
```

**Latency:** ~1-3 seconds (depends on local agreement policy)

---

### 6. RealtimeSTT

**Repository:** https://github.com/KoljaB/RealtimeSTT

**Features:**
- Turnkey real-time speech-to-text
- Voice activity detection built-in
- Wake word detection support
- Callback-based architecture
- Multi-backend support (Whisper, faster-whisper)

**Installation:**
```bash
pip install RealtimeSTT
```

**Code Example:**
```python
from RealtimeSTT import AudioToTextRecorder

def process_text(text):
    print(f"Transcribed: {text}")

recorder = AudioToTextRecorder(
    model="base",
    language="en",
    on_transcription_complete=process_text
)

recorder.start()
# Records until stopped
recorder.stop()
```

**CLI Usage:**
```bash
python -m RealtimeSTT
```

**Feasibility: HIGH** - Simple API, good for CLI integration.

---

### 7. speech_recognition + Whisper

**Repository:** https://github.com/Uberi/speech_recognition

**Approach:** Uses the `speech_recognition` library with Whisper backend.

**Code Example:**
```python
import speech_recognition as sr

recognizer = sr.Recognizer()
mic = sr.Microphone()

with mic as source:
    recognizer.adjust_for_ambient_noise(source)
    print("Listening...")
    audio = recognizer.listen(source)

# Use Whisper for transcription
text = recognizer.recognize_whisper(audio, model="base")
print(f"You said: {text}")
```

**Limitation:** Not true streaming; waits for speech to complete.

---

## Voice Activity Detection Integration

### Silero VAD + Whisper

**Repository:** https://github.com/snakers4/silero-vad

**Why VAD Matters:**
- Reduces unnecessary Whisper processing
- Detects speech start/end
- Enables efficient chunking
- Reduces latency and CPU usage

**Integration Example:**
```python
import torch
import torchaudio

# Load Silero VAD
model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad'
)

(get_speech_timestamps, save_audio, read_audio,
 VADIterator, collect_chunks) = utils

# Use VADIterator for streaming
vad_iterator = VADIterator(model)

# Process audio stream
for audio_chunk in audio_stream:
    speech_dict = vad_iterator(audio_chunk, return_seconds=True)
    if speech_dict:
        # Speech detected, process with Whisper
        pass
```

### WebRTC VAD

**Package:** `webrtcvad`

**Lighter alternative:**
```python
import webrtcvad

vad = webrtcvad.Vad(3)  # Aggressiveness 0-3

# Check if frame contains speech
is_speech = vad.is_speech(frame, sample_rate=16000)
```

---

## CLI-Focused Tools

### whisper-cli (whisper.cpp)

**Built-in CLI for streaming:**
```bash
# Install whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp && make

# Stream from microphone
./stream -m models/ggml-base.en.bin --step 1000 --length 5000

# Stream with VAD
./stream -m models/ggml-base.en.bin --vad-thold 0.6 --freq-thold 100
```

### Whisper CLI Wrapper Ideas

**Python CLI with Click:**
```python
import click
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import queue

@click.command()
@click.option('--model', default='base', help='Whisper model size')
@click.option('--language', default='en', help='Language code')
def live_transcribe(model, language):
    """Live transcription CLI tool."""
    whisper = WhisperModel(model, device="cpu")
    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time, status):
        audio_queue.put(indata.copy())

    with sd.InputStream(callback=audio_callback,
                        channels=1,
                        samplerate=16000):
        print("Listening... (Ctrl+C to stop)")
        buffer = np.array([], dtype=np.float32)

        while True:
            chunk = audio_queue.get()
            buffer = np.append(buffer, chunk.flatten())

            # Process every 3 seconds of audio
            if len(buffer) >= 16000 * 3:
                segments, _ = whisper.transcribe(buffer)
                for segment in segments:
                    print(segment.text, end='', flush=True)
                buffer = np.array([], dtype=np.float32)

if __name__ == '__main__':
    live_transcribe()
```

---

## Feasibility Assessment

| Solution | Latency | Ease of Integration | CLI Support | Resource Usage | Overall Score |
|----------|---------|---------------------|-------------|----------------|---------------|
| whisper.cpp stream | 0.5-2s | Medium | Excellent | Low (CPU) | 9/10 |
| faster-whisper + VAD | 1-3s | High | Good | Medium (GPU) | 8/10 |
| WhisperLive | 1-2s | High | Medium | Medium | 8/10 |
| RealtimeSTT | 1-3s | Very High | Good | Medium | 8/10 |
| whisper-streaming | 1-3s | Medium | Medium | Medium | 7/10 |
| Original Whisper | 2-30s | Medium | Low | High | 5/10 |

### Latency Breakdown

**Factors affecting latency:**
1. **Audio buffering:** 500ms - 3s (configurable)
2. **Model inference:** 100ms - 2s (depends on model size)
3. **VAD processing:** 10-50ms
4. **Text confirmation:** 100-500ms (for streaming agreement)

**Optimal configuration for CLI:**
- Model: `tiny.en` or `base.en` (fastest)
- Audio buffer: 1-2 seconds
- VAD: Silero (best accuracy) or WebRTC (fastest)
- Implementation: whisper.cpp or faster-whisper

---

## Recommendations for Claude Code CLI

### Primary Recommendation: whisper.cpp

**Reasons:**
1. Native streaming support (`./stream`)
2. No Python runtime required
3. Low latency (sub-second possible)
4. CPU-optimized (works without GPU)
5. Single binary distribution possible
6. Cross-platform (Windows, macOS, Linux)

**Integration Approach:**
```bash
# Claude Code could spawn whisper.cpp as subprocess
./whisper-stream -m model.bin --step 500 --length 2000 | claude-code-cli
```

### Secondary Recommendation: faster-whisper + RealtimeSTT

**Reasons:**
1. Python-native (easier integration if Claude Code is Python-based)
2. Good balance of speed and accuracy
3. Built-in VAD handling
4. Callback-based (non-blocking)

**Integration Example:**
```python
from RealtimeSTT import AudioToTextRecorder

def on_text(text):
    # Send to Claude Code for processing
    claude_code.process_input(text)

recorder = AudioToTextRecorder(model="base.en")
recorder.text_detected_callback = on_text
recorder.start()
```

### Architecture Suggestion for Claude Code CLI

```
+----------------+     +-------------+     +------------------+
|   Microphone   | --> |  VAD Engine | --> |  Whisper Engine  |
+----------------+     +-------------+     +------------------+
                                                    |
                                                    v
                                          +-----------------+
                                          | Text Processing |
                                          +-----------------+
                                                    |
                                                    v
                                          +-----------------+
                                          | Claude Code CLI |
                                          +-----------------+
```

**Key Design Decisions:**
1. **VAD-first:** Only send audio to Whisper when speech detected
2. **Buffered processing:** Accumulate 1-2 seconds before inference
3. **Incremental output:** Display partial results as they come
4. **Confirmation delay:** Wait 500ms after speech ends for final text
5. **Wake word (optional):** "Hey Claude" to start listening

---

## Additional Resources

### GitHub Repositories
- https://github.com/openai/whisper - Original Whisper
- https://github.com/ggerganov/whisper.cpp - C++ port with streaming
- https://github.com/SYSTRAN/faster-whisper - Fast Python implementation
- https://github.com/collabora/WhisperLive - Real-time server
- https://github.com/ufal/whisper_streaming - Streaming wrapper
- https://github.com/KoljaB/RealtimeSTT - Turnkey real-time STT
- https://github.com/snakers4/silero-vad - Voice activity detection

### Related Projects
- https://github.com/jianfch/stable-ts - Improved timestamps
- https://github.com/linto-ai/whisper-timestamped - Word timestamps
- https://github.com/Vaibhavs10/insanely-fast-whisper - Optimized inference

---

## Conclusion

For Claude Code CLI integration, the recommended approach is:

1. **For maximum performance:** Use whisper.cpp with the `stream` example as a subprocess
2. **For Python integration:** Use faster-whisper with RealtimeSTT wrapper
3. **For simplicity:** WhisperLive client-server architecture

All solutions can achieve sub-3-second latency with proper configuration. The choice depends on:
- Target platform constraints
- GPU availability
- Integration complexity tolerance
- Latency requirements

---

*Note: This research was compiled from training data with knowledge cutoff of May 2025. Some projects may have been updated or new solutions may have emerged. Verify links and features before implementation.*
