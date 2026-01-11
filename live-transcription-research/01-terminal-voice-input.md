# Live Transcription Research: Terminal Voice Input for Claude Code CLI

## Executive Summary

This document explores implementing direct voice input into terminal applications, specifically for integration with Claude Code CLI. The goal is to enable users to speak commands and queries that are transcribed in real-time and sent to the CLI's stdin.

---

## 1. How Terminals Handle Audio Input

### 1.1 Terminal Fundamentals

Terminals are fundamentally **text-based I/O interfaces**. They do not natively handle audio input. A terminal receives:
- **stdin** (standard input): Text stream, typically from keyboard
- **stdout/stderr** (standard output/error): Text stream for output

### 1.2 Audio Input Architecture

```
+-------------------+      +---------------------+      +------------------+
|   Microphone      | ---> |  Audio Capture      | ---> |  Speech-to-Text  |
|   (Hardware)      |      |  Library/API        |      |  Engine          |
+-------------------+      +---------------------+      +------------------+
                                                                |
                                                                v
+-------------------+      +---------------------+      +------------------+
|   Claude Code     | <--- |  stdin pipe/        | <--- |  Text Output     |
|   CLI             |      |  subprocess         |      |  Buffer          |
+-------------------+      +---------------------+      +------------------+
```

### 1.3 Key Insight

Audio must be:
1. **Captured** from the microphone via OS audio APIs
2. **Processed** by a speech-to-text engine
3. **Piped** as text to the target application's stdin

---

## 2. Audio Capture Libraries for Windows

### 2.1 PyAudio

**Description**: Cross-platform audio I/O library based on PortAudio.

**Installation**:
```bash
pip install pyaudio
# Windows may require: pip install pipwin && pipwin install pyaudio
```

**Basic Usage**:
```python
import pyaudio
import numpy as np

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper requires 16kHz

p = pyaudio.PyAudio()
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

# Capture audio
data = stream.read(CHUNK)
audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
```

**Pros**:
- Mature, well-documented
- Cross-platform
- Low-level control

**Cons**:
- Can be tricky to install on Windows (requires PortAudio)
- No built-in async support

### 2.2 sounddevice

**Description**: Python bindings for PortAudio with NumPy integration.

**Installation**:
```bash
pip install sounddevice
```

**Basic Usage**:
```python
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
DURATION = 5  # seconds

# Record audio
audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE,
               channels=1, dtype='float32')
sd.wait()  # Wait until recording is finished

# Stream callback for real-time
def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    # Process indata here
    audio_queue.put(indata.copy())

with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                    callback=audio_callback):
    # Do transcription while recording
    pass
```

**Pros**:
- Cleaner API than PyAudio
- Native NumPy integration
- Callback-based streaming
- Easier installation on Windows

**Cons**:
- Still requires PortAudio (bundled on Windows)

### 2.3 Windows-Specific: pywin32 / Windows Audio Session API (WASAPI)

For Windows-native audio capture without PortAudio dependency:

```python
# Using sounddevice with WASAPI backend (Windows 10+)
import sounddevice as sd

# List WASAPI devices
devices = sd.query_devices()
print(devices)

# Use specific WASAPI device
sd.default.device = 'WASAPI'  # or specific device index
```

### 2.4 Recommended: sounddevice

For Windows development, **sounddevice** is recommended due to:
- Simpler installation
- Better Windows compatibility
- Native NumPy arrays (required by Whisper)
- Callback-based streaming for real-time applications

---

## 3. Speech-to-Text Engines

### 3.1 OpenAI Whisper (Local)

**This Repository**: The whisperCC repository contains OpenAI's Whisper model.

**Architecture**:
```
Audio (16kHz, float32) --> Mel Spectrogram --> Transformer Encoder/Decoder --> Text
```

**Key Parameters from Code Analysis**:
```python
# From whisper/audio.py
SAMPLE_RATE = 16000      # Required sample rate
CHUNK_LENGTH = 30        # 30-second chunks
N_SAMPLES = 480000       # 30 seconds * 16000 Hz
N_MELS = 80 or 128       # Mel spectrogram bins
```

**Model Options**:
| Model | Parameters | VRAM | Speed | Best For |
|-------|------------|------|-------|----------|
| tiny | 39M | ~1GB | ~10x | Low latency, limited accuracy |
| base | 74M | ~1GB | ~7x | Balance for testing |
| small | 244M | ~2GB | ~4x | Good accuracy |
| turbo | 809M | ~6GB | ~8x | **Best for real-time** (optimized large-v3) |

**Streaming Limitation**:
The standard Whisper transcribe() function processes complete audio segments:
```python
# From whisper/transcribe.py - processes 30-second windows
mel = log_mel_spectrogram(audio, model.dims.n_mels, padding=N_SAMPLES)
```

For real-time, we need a custom streaming approach.

### 3.2 Faster-Whisper

**Description**: CTranslate2-optimized Whisper implementation, 4x faster.

**Installation**:
```bash
pip install faster-whisper
```

**Usage**:
```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cuda", compute_type="float16")

# Transcribe with word timestamps
segments, info = model.transcribe("audio.wav", word_timestamps=True)
for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

**Pros**:
- 4x faster than original Whisper
- Lower memory usage
- Better suited for real-time

**Cons**:
- Separate installation
- Still chunk-based (not truly streaming)

### 3.3 Whisper.cpp

**Description**: C/C++ port of Whisper, highly optimized.

**Windows Installation**:
```bash
# Using pre-built binaries or compile with CMake
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
cmake -B build
cmake --build build --config Release
```

**Real-time Stream Example** (from whisper.cpp):
```bash
# stream example - real-time transcription
./stream -m models/ggml-base.en.bin -t 4 --step 500 --length 5000
```

**Pros**:
- Extremely fast (CPU optimized)
- Built-in streaming mode
- Low memory footprint

**Cons**:
- C++ integration needed from Python
- Separate model format (GGML)

### 3.4 Vosk

**Description**: Offline speech recognition toolkit supporting multiple languages.

**Installation**:
```bash
pip install vosk
# Download model: https://alphacephei.com/vosk/models
```

**Real-time Usage**:
```python
import vosk
import sounddevice as sd
import queue
import json

model = vosk.Model("vosk-model-en-us-0.22")
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    rec = vosk.KaldiRecognizer(model, 16000)
    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            print(result["text"])
        else:
            partial = json.loads(rec.PartialResult())
            print(f"Partial: {partial['partial']}", end='\r')
```

**Pros**:
- True real-time streaming
- Low latency (~200ms)
- Lightweight models (50MB-1GB)
- Works offline
- Partial results (interim transcription)

**Cons**:
- Lower accuracy than Whisper
- Requires model download

### 3.5 DeepSpeech (Mozilla)

**Note**: Project is no longer actively maintained. Consider alternatives.

### 3.6 Azure Speech Services / Google Cloud Speech-to-Text

**Cloud Options** - require internet and API keys:
```python
# Azure example
import azure.cognitiveservices.speech as speechsdk

speech_config = speechsdk.SpeechConfig(subscription="KEY", region="REGION")
recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

# Real-time with interim results
recognizer.recognizing.connect(lambda evt: print(f"RECOGNIZING: {evt.result.text}"))
recognizer.recognized.connect(lambda evt: print(f"RECOGNIZED: {evt.result.text}"))
recognizer.start_continuous_recognition()
```

**Pros**:
- Highest accuracy
- True streaming with interim results
- No local GPU needed

**Cons**:
- Requires internet
- API costs
- Privacy concerns

---

## 4. Comparison Matrix

| Feature | Whisper | Faster-Whisper | Whisper.cpp | Vosk | Cloud APIs |
|---------|---------|----------------|-------------|------|------------|
| **Latency** | High (1-5s) | Medium (0.5-2s) | Low (0.2-1s) | Very Low (<0.2s) | Low (<0.3s) |
| **Accuracy** | Excellent | Excellent | Excellent | Good | Excellent |
| **Streaming** | No (chunked) | No (chunked) | Yes | Yes | Yes |
| **Interim Results** | No | No | Limited | Yes | Yes |
| **Offline** | Yes | Yes | Yes | Yes | No |
| **GPU Required** | Recommended | Recommended | No | No | No |
| **Install Complexity** | Medium | Medium | High | Low | Low |
| **Windows Support** | Good | Good | Moderate | Excellent | Excellent |

---

## 5. Integration with Claude Code CLI

### 5.1 Architecture Options

#### Option A: Subprocess Pipe (Simplest)
```
+-------------+     +-------------------+     +----------------+
| Voice       | --> | Transcription     | --> | Claude Code    |
| Capture     |     | Engine            |     | (subprocess)   |
+-------------+     +-------------------+     +----------------+
                                                    |
                            stdin pipe -------------+
```

```python
import subprocess
import sys

# Start Claude Code as subprocess
process = subprocess.Popen(
    ['claude'],  # or full path to claude-code executable
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1  # Line buffered
)

# Send transcribed text
def send_to_claude(text):
    process.stdin.write(text + '\n')
    process.stdin.flush()

# Read response
def read_response():
    return process.stdout.readline()
```

#### Option B: PTY (Pseudo-Terminal) - More Compatible
```python
import pty
import os
import select

# Create pseudo-terminal
master_fd, slave_fd = pty.openpty()

# Start process with PTY
pid = os.fork()
if pid == 0:
    # Child process
    os.setsid()
    os.dup2(slave_fd, 0)  # stdin
    os.dup2(slave_fd, 1)  # stdout
    os.dup2(slave_fd, 2)  # stderr
    os.execvp('claude', ['claude'])
else:
    # Parent process - interact with master_fd
    os.write(master_fd, b"Hello from voice input\n")
```

**Note**: PTY approach is Unix-specific. For Windows, use `winpty` or `conpty`.

#### Option C: Named Pipe (Windows-Friendly)
```python
# Windows Named Pipe approach
import win32pipe
import win32file

pipe_name = r'\\.\pipe\claude_voice_input'

# Create named pipe
pipe = win32pipe.CreateNamedPipe(
    pipe_name,
    win32pipe.PIPE_ACCESS_DUPLEX,
    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
    1, 65536, 65536, 0, None
)
```

### 5.2 Complete Implementation Example

```python
#!/usr/bin/env python3
"""
Voice Input for Claude Code CLI
Real-time speech-to-text integration using Vosk (for low latency)
"""

import subprocess
import queue
import sys
import threading
import json

import sounddevice as sd
import vosk

# Configuration
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
MODEL_PATH = "vosk-model-en-us-0.22"  # Download from vosk website

class VoiceToClaudeCode:
    def __init__(self, model_path: str):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.running = False

        # Start Claude Code process
        self.claude_process = subprocess.Popen(
            ['claude'],  # Adjust path as needed
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

    def audio_callback(self, indata, frames, time, status):
        """Called by sounddevice for each audio block"""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        self.audio_queue.put(bytes(indata))

    def transcription_worker(self):
        """Process audio and produce transcription"""
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.5)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self.text_queue.put(("final", text))
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get("partial", "").strip()
                    if partial_text:
                        self.text_queue.put(("partial", partial_text))
            except queue.Empty:
                continue

    def display_worker(self):
        """Display transcription and send to Claude when ready"""
        current_partial = ""
        while self.running:
            try:
                msg_type, text = self.text_queue.get(timeout=0.5)
                if msg_type == "partial":
                    # Show partial transcription
                    print(f"\r[Speaking...] {text}", end="", flush=True)
                    current_partial = text
                elif msg_type == "final":
                    # Clear partial and show final
                    print(f"\r[You]: {text}          ")
                    # Send to Claude Code
                    self.send_to_claude(text)
            except queue.Empty:
                continue

    def send_to_claude(self, text: str):
        """Send transcribed text to Claude Code stdin"""
        try:
            self.claude_process.stdin.write(text + "\n")
            self.claude_process.stdin.flush()
            print("[Sent to Claude Code]")
        except BrokenPipeError:
            print("[Error: Claude Code process terminated]", file=sys.stderr)
            self.running = False

    def output_reader(self):
        """Read and display Claude Code output"""
        while self.running:
            try:
                line = self.claude_process.stdout.readline()
                if line:
                    print(f"[Claude]: {line.rstrip()}")
                elif self.claude_process.poll() is not None:
                    break
            except:
                break

    def run(self):
        """Main loop"""
        self.running = True

        # Start worker threads
        transcription_thread = threading.Thread(target=self.transcription_worker)
        display_thread = threading.Thread(target=self.display_worker)
        output_thread = threading.Thread(target=self.output_reader)

        transcription_thread.start()
        display_thread.start()
        output_thread.start()

        print("Voice input active. Speak to interact with Claude Code.")
        print("Press Ctrl+C to exit.\n")

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype='int16',
                channels=1,
                callback=self.audio_callback
            ):
                while self.running:
                    sd.sleep(100)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False
            transcription_thread.join()
            display_thread.join()
            self.claude_process.terminate()

if __name__ == "__main__":
    app = VoiceToClaudeCode(MODEL_PATH)
    app.run()
```

### 5.3 Whisper-Based Real-Time Implementation

For higher accuracy using Whisper with chunked processing:

```python
#!/usr/bin/env python3
"""
Voice Input using Whisper (higher accuracy, higher latency)
"""

import subprocess
import queue
import threading
import numpy as np
import sounddevice as sd

# Option 1: Using this repository's Whisper
import whisper

# Option 2: Using faster-whisper
# from faster_whisper import WhisperModel

class WhisperVoiceInput:
    def __init__(self, model_name: str = "base"):
        # Load Whisper model
        self.model = whisper.load_model(model_name)

        # Audio settings
        self.sample_rate = 16000
        self.chunk_duration = 3  # seconds - shorter = lower latency
        self.chunk_samples = self.sample_rate * self.chunk_duration

        # Buffers
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()

        # Processing
        self.audio_queue = queue.Queue()
        self.running = False

    def audio_callback(self, indata, frames, time, status):
        """Accumulate audio data"""
        audio_data = indata[:, 0].astype(np.float32)
        self.audio_queue.put(audio_data)

    def buffer_worker(self):
        """Accumulate audio and trigger transcription"""
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                with self.buffer_lock:
                    self.audio_buffer = np.concatenate([self.audio_buffer, chunk])

                    # When we have enough audio, transcribe
                    if len(self.audio_buffer) >= self.chunk_samples:
                        audio_to_process = self.audio_buffer[:self.chunk_samples]
                        self.audio_buffer = self.audio_buffer[self.chunk_samples // 2:]  # Overlap

                        # Transcribe in separate thread to not block
                        threading.Thread(
                            target=self.transcribe_chunk,
                            args=(audio_to_process,)
                        ).start()
            except queue.Empty:
                continue

    def transcribe_chunk(self, audio: np.ndarray):
        """Transcribe audio chunk using Whisper"""
        # Pad or trim to 30 seconds (Whisper requirement)
        audio = whisper.pad_or_trim(audio)

        # Create mel spectrogram
        mel = whisper.log_mel_spectrogram(audio, n_mels=self.model.dims.n_mels)
        mel = mel.to(self.model.device)

        # Decode
        options = whisper.DecodingOptions(language="en", fp16=False)
        result = whisper.decode(self.model, mel, options)

        text = result.text.strip()
        if text and text not in ["", "[BLANK_AUDIO]", "(silence)"]:
            print(f"\n[Transcribed]: {text}")
            # Send to Claude Code here

    def run(self):
        """Start voice capture"""
        self.running = True

        buffer_thread = threading.Thread(target=self.buffer_worker)
        buffer_thread.start()

        print(f"Whisper voice input active (using {self.chunk_duration}s chunks)")
        print("Press Ctrl+C to stop.\n")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self.audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            ):
                while self.running:
                    sd.sleep(100)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            buffer_thread.join()

if __name__ == "__main__":
    app = WhisperVoiceInput("base")
    app.run()
```

---

## 6. Windows-Specific Considerations

### 6.1 Audio Device Selection

```python
import sounddevice as sd

# List all audio devices
print(sd.query_devices())

# Set specific input device
sd.default.device = (input_device_id, output_device_id)

# Or by name
for i, dev in enumerate(sd.query_devices()):
    if 'Microphone' in dev['name'] and dev['max_input_channels'] > 0:
        sd.default.device[0] = i
        break
```

### 6.2 Common Windows Issues

1. **PyAudio Installation**:
   ```bash
   # If pip install pyaudio fails:
   pip install pipwin
   pipwin install pyaudio
   # Or download .whl from https://www.lfd.uci.edu/~gohlke/pythonlibs/
   ```

2. **Missing VC++ Redistributable**:
   - Install Visual C++ Redistributable for Visual Studio 2015-2022

3. **Microphone Permissions**:
   - Windows 10/11: Settings > Privacy > Microphone > Allow apps to access microphone

4. **WASAPI Exclusive Mode**:
   ```python
   # Some apps lock the audio device
   # Use shared mode:
   import sounddevice as sd
   sd.default.extra_settings = sd.WasapiSettings(exclusive=False)
   ```

### 6.3 Process Communication on Windows

Windows doesn't have Unix PTY. Alternatives:

```python
# Option 1: Simple subprocess (works for most cases)
import subprocess
proc = subprocess.Popen(['claude'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

# Option 2: Using pywinpty for full PTY emulation
from winpty import PtyProcess
proc = PtyProcess.spawn('claude')
proc.write('Hello\r\n')
output = proc.read()

# Option 3: ConPTY (Windows 10 1809+)
# Requires ctypes/cffi bindings to Windows API
```

---

## 7. Latency Analysis

### 7.1 Latency Components

```
Total Latency = Audio Capture + Processing + Transcription + Piping

Audio Capture:     ~50-100ms (buffer size dependent)
                   - Smaller buffers = lower latency, higher CPU
                   - Recommended: 100-200ms blocks

Processing:        ~10-50ms
                   - Mel spectrogram computation
                   - Format conversion

Transcription:     50ms - 5000ms (engine dependent)
                   - Vosk: 50-200ms
                   - Whisper tiny (GPU): 200-500ms
                   - Whisper turbo (GPU): 500-1500ms
                   - Whisper large (GPU): 2000-5000ms

Piping:            ~1-5ms (negligible)
```

### 7.2 Latency Targets

| Use Case | Acceptable Latency | Recommended Engine |
|----------|-------------------|-------------------|
| Real-time conversation | <500ms | Vosk, Whisper.cpp |
| Dictation | <1000ms | Faster-Whisper (tiny/base) |
| Command input | <2000ms | Whisper (base/small) |
| High-accuracy transcription | <5000ms | Whisper (turbo/large) |

### 7.3 Optimization Strategies

1. **Voice Activity Detection (VAD)**:
   - Only transcribe when speech is detected
   - Reduces unnecessary processing
   ```python
   import webrtcvad
   vad = webrtcvad.Vad(3)  # Aggressiveness 0-3
   is_speech = vad.is_speech(audio_bytes, sample_rate)
   ```

2. **Chunked Processing with Overlap**:
   - Process 3-5 second chunks
   - 50% overlap prevents word splitting
   - Balance between latency and context

3. **GPU Acceleration**:
   - CUDA for Whisper: 10x speedup
   - Ensure CUDA toolkit matches PyTorch version

4. **Model Selection**:
   - Start with `tiny` or `base` for testing
   - Use `turbo` for production (best accuracy/speed ratio)

---

## 8. Audio Quality Requirements

### 8.1 Whisper Requirements

From `whisper/audio.py`:
```python
SAMPLE_RATE = 16000  # 16kHz required
# Audio format: float32, mono, normalized to [-1, 1]
```

### 8.2 Recommended Settings

```python
AUDIO_CONFIG = {
    'sample_rate': 16000,      # Required by Whisper
    'channels': 1,              # Mono
    'dtype': 'float32',         # Or int16 then convert
    'blocksize': 1600,          # 100ms at 16kHz
}
```

### 8.3 Audio Quality Tips

1. **Noise Reduction**:
   ```python
   # Using noisereduce library
   import noisereduce as nr
   reduced_noise = nr.reduce_noise(y=audio, sr=16000)
   ```

2. **Normalization**:
   ```python
   # Normalize to prevent clipping
   audio = audio / np.max(np.abs(audio))
   ```

3. **Silence Trimming**:
   ```python
   # Remove leading/trailing silence
   from scipy.io import wavfile
   # Or use librosa.effects.trim()
   ```

---

## 9. Installation Guide

### 9.1 Minimal Setup (Vosk - Lowest Latency)

```bash
# 1. Install dependencies
pip install sounddevice vosk

# 2. Download Vosk model (choose size)
# Small (~50MB): vosk-model-small-en-us-0.15
# Medium (~500MB): vosk-model-en-us-0.22
# Download from: https://alphacephei.com/vosk/models

# 3. Run the voice input script
python voice_to_claude.py
```

### 9.2 Full Setup (Whisper - Highest Accuracy)

```bash
# 1. Install this Whisper repository
cd C:/Users/joshu/Documents/GitHub/whisperCC
pip install -e .

# 2. Install audio capture
pip install sounddevice numpy

# 3. Install CUDA (optional, for GPU acceleration)
# Download from: https://developer.nvidia.com/cuda-downloads
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 4. Run Whisper-based voice input
python voice_to_claude_whisper.py
```

### 9.3 Dependencies Summary

```
# requirements-voice-input.txt
sounddevice>=0.4.0        # Audio capture
numpy>=1.20.0             # Array processing
vosk>=0.3.45              # Low-latency STT (optional)
# openai-whisper           # High-accuracy STT (from this repo)
webrtcvad>=2.0.10         # Voice activity detection (optional)
```

---

## 10. Pros and Cons Summary

### 10.1 Approach: Vosk + Subprocess Pipe

**Pros**:
- Very low latency (~200ms)
- Simple implementation
- Works offline
- Partial (interim) results
- Lightweight

**Cons**:
- Lower accuracy than Whisper
- English models best; other languages vary
- Requires model download

### 10.2 Approach: Whisper + Subprocess Pipe

**Pros**:
- Excellent accuracy
- Multilingual support
- Integrated with existing whisperCC codebase
- Well-maintained

**Cons**:
- Higher latency (1-5 seconds)
- No true streaming (chunk-based)
- GPU recommended for acceptable speed
- No interim results

### 10.3 Approach: Cloud APIs

**Pros**:
- Best accuracy
- True streaming with interim results
- No local compute needed
- Constantly improving

**Cons**:
- Requires internet
- API costs
- Privacy concerns
- Dependency on external service

---

## 11. Feasibility Assessment

### 11.1 Technical Feasibility: HIGH

Implementing voice input for Claude Code CLI is technically feasible with current tools:

1. **Audio capture** is well-supported on Windows via sounddevice
2. **Speech-to-text** has multiple viable options (Vosk for speed, Whisper for accuracy)
3. **Process integration** works via subprocess stdin/stdout piping

### 11.2 Practical Challenges

| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| Latency | Medium | Use Vosk or Whisper tiny/base |
| Accuracy | Low | Whisper provides excellent accuracy |
| Installation | Medium | Pre-packaged installer or Docker |
| Windows compatibility | Low | sounddevice handles this well |
| Background noise | Medium | VAD + noise reduction |

### 11.3 Recommended Implementation Path

**Phase 1: Prototype (1-2 days)**
- Use Vosk for quick results
- Simple subprocess piping
- Test basic voice-to-Claude flow

**Phase 2: Enhancement (3-5 days)**
- Add Whisper support for higher accuracy
- Implement VAD for efficiency
- Add configuration options

**Phase 3: Polish (1-2 weeks)**
- Create installer/setup script
- Add GUI for device selection
- Implement push-to-talk option
- Error handling and recovery

### 11.4 Success Metrics

- **Latency**: < 2 seconds from speech end to Claude receiving text
- **Accuracy**: > 95% word accuracy for clear speech
- **Reliability**: Works consistently across sessions
- **Usability**: Minimal setup required by end user

---

## 12. Alternative Approaches

### 12.1 System-Level Voice Input

Instead of custom implementation, leverage OS voice typing:

**Windows Voice Typing (Win+H)**:
- Built into Windows 10/11
- Types directly into any text field
- No coding required
- But: less control, may interfere with Claude Code UI

### 12.2 Accessibility Tools

Screen readers and dictation software:
- Dragon NaturallySpeaking
- Windows Speech Recognition
- Can work with any terminal

### 12.3 Browser Extension Approach

If Claude Code has a web interface:
- Web Speech API in browser
- Native browser microphone access
- No installation on user's system

---

## 13. Conclusion

Direct voice input to Claude Code CLI is achievable through a combination of audio capture libraries (sounddevice) and speech-to-text engines (Vosk for low latency, Whisper for high accuracy). The recommended approach uses subprocess piping to send transcribed text to Claude Code's stdin.

**Key Recommendations**:
1. Start with Vosk for prototyping due to its low latency and ease of setup
2. Add Whisper support as an optional high-accuracy mode
3. Implement Voice Activity Detection to reduce unnecessary processing
4. Provide clear installation instructions for Windows users
5. Consider a "push-to-talk" mode as an alternative to continuous listening

**Next Steps**:
1. Create a working prototype with Vosk
2. Test integration with Claude Code CLI
3. Evaluate latency and accuracy in real-world usage
4. Iterate based on user feedback

---

## Appendix A: Quick Start Script

Save this as `voice_input_quick_start.py`:

```python
#!/usr/bin/env python3
"""
Quick Start: Voice Input for Terminal Commands
Run: python voice_input_quick_start.py
"""

import subprocess
import queue
import threading
import json
import sys

try:
    import sounddevice as sd
except ImportError:
    print("Installing sounddevice...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sounddevice"])
    import sounddevice as sd

try:
    import vosk
except ImportError:
    print("Installing vosk...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "vosk"])
    import vosk

# Download model if not present
import os
MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"

if not os.path.exists(MODEL_NAME):
    print(f"Downloading {MODEL_NAME}...")
    import urllib.request
    import zipfile
    urllib.request.urlretrieve(MODEL_URL, f"{MODEL_NAME}.zip")
    with zipfile.ZipFile(f"{MODEL_NAME}.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
    os.remove(f"{MODEL_NAME}.zip")

# Main voice capture
SAMPLE_RATE = 16000
audio_queue = queue.Queue()

def callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

model = vosk.Model(MODEL_NAME)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

print("\n" + "="*50)
print("Voice Input Active - Speak now!")
print("Press Ctrl+C to exit")
print("="*50 + "\n")

with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                       dtype='int16', channels=1, callback=callback):
    try:
        while True:
            data = audio_queue.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    print(f"\n>>> {text}")
                    # Here you would send to Claude Code:
                    # subprocess.run(['claude', '-p', text])
            else:
                partial = json.loads(rec.PartialResult())
                partial_text = partial.get("partial", "")
                if partial_text:
                    print(f"\r[...] {partial_text}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\nStopped.")
```

---

## Appendix B: References

1. **OpenAI Whisper**: https://github.com/openai/whisper
2. **Faster-Whisper**: https://github.com/guillaumekln/faster-whisper
3. **Whisper.cpp**: https://github.com/ggerganov/whisper.cpp
4. **Vosk**: https://alphacephei.com/vosk/
5. **sounddevice**: https://python-sounddevice.readthedocs.io/
6. **PyAudio**: https://people.csail.mit.edu/hubert/pyaudio/
7. **WebRTC VAD**: https://github.com/wiseman/py-webrtcvad
