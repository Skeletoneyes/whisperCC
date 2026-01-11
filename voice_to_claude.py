#!/usr/bin/env python3
"""
Voice to Claude Code - Speak directly to Claude Code CLI

Pipeline:
  Microphone -> RealtimeSTT (local Whisper) -> Claude Code CLI

All processing is 100% local. No audio leaves your machine.

Usage:
  python voice_to_claude.py

Requirements:
  pip install RealtimeSTT

For GPU acceleration (recommended):
  pip install torch --index-url https://download.pytorch.org/whl/cu118
"""

import subprocess
import sys
import os

try:
    from RealtimeSTT import AudioToTextRecorder
except ImportError:
    print("RealtimeSTT not installed. Installing now...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "RealtimeSTT"])
    from RealtimeSTT import AudioToTextRecorder


def send_to_claude(text: str):
    """Send transcribed text to Claude Code CLI"""
    if not text or not text.strip():
        return

    text = text.strip()
    print(f"\n{'='*60}")
    print(f"[SENDING TO CLAUDE]: {text}")
    print('='*60)

    try:
        # Run claude with the transcribed text as a prompt
        result = subprocess.run(
            ["claude", "-p", text],
            capture_output=False,  # Let output stream to terminal
            text=True
        )
    except FileNotFoundError:
        print("\n[ERROR] 'claude' command not found.")
        print("Make sure Claude Code CLI is installed and in your PATH.")
        print("Install: npm install -g @anthropic-ai/claude-code")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           VOICE TO CLAUDE CODE - Local Pipeline              ║
╠══════════════════════════════════════════════════════════════╣
║  Speak naturally. Your speech is transcribed locally using   ║
║  Whisper, then sent to Claude Code CLI.                      ║
║                                                              ║
║  Pipeline: Mic -> Whisper (local) -> Claude Code             ║
║  Privacy:  100% local - no audio leaves your machine         ║
║                                                              ║
║  Commands:                                                   ║
║    - Speak naturally, pause when done                        ║
║    - Say "exit" or "quit" to stop                            ║
║    - Press Ctrl+C to force quit                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    print("[LOADING] Initializing Whisper model (first run downloads ~1GB)...")

    # Configure the recorder
    # Using base.en for good balance of speed and accuracy
    recorder = AudioToTextRecorder(
        model="base.en",           # Options: tiny.en, base.en, small.en, medium.en, large-v2
        language="en",
        silero_sensitivity=0.4,    # VAD sensitivity (0-1, lower = more sensitive)
        post_speech_silence_duration=0.8,  # Seconds of silence before finalizing
        min_length_of_recording=0.5,       # Minimum recording length in seconds
    )

    print("[READY] Listening... Speak now!\n")

    try:
        while True:
            # This blocks until speech is detected and completed
            text = recorder.text()

            if text:
                # Check for exit commands
                if text.lower().strip() in ["exit", "quit", "stop", "goodbye"]:
                    print("\n[GOODBYE] Stopping voice input.")
                    break

                # Send to Claude
                send_to_claude(text)
                print("\n[LISTENING] Ready for next input...\n")

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Voice input terminated.")

    finally:
        print("Cleaning up...")


if __name__ == "__main__":
    main()
