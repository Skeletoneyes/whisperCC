#!/usr/bin/env python3
"""
Voice Input - Speak and type into the focused window

Simple experiment: Speak and your words are typed into whatever window is focused.
Perfect for dictating to Claude Code terminal.

Usage:
  python voice_input.py

Requirements:
  pip install RealtimeSTT pyperclip anthropic

Environment:
  ANTHROPIC_API_KEY - Your Anthropic API key
"""

import subprocess
import sys
import time
import os

# Terminal title state indicators
STATE_WAITING = "🟡"   # Yellow - waiting for/detached from Claude instance
STATE_RECORDING = "🔴"  # Red - recording
STATE_READY = "🟢"      # Green - ready to record

def set_terminal_title(state: str, status: str = ""):
    """Update terminal title with state emoji and optional status text."""
    title = f"{state} Voice Input"
    if status:
        title += f" - {status}"
    # ANSI escape sequence to set terminal title (works on most terminals)
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()

# Auto-install dependencies
def ensure_installed(package, import_name=None):
    import_name = import_name or package
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

ensure_installed("RealtimeSTT")
ensure_installed("pyperclip")
ensure_installed("pyautogui")
ensure_installed("anthropic")

from RealtimeSTT import AudioToTextRecorder
import pyperclip
import pyautogui
import anthropic

# Disable pyautogui fail-safe
pyautogui.FAILSAFE = False

# Initialize Claude client
client = anthropic.Anthropic()


def cleanup_speech(raw_text: str) -> str:
    """Use Claude to clean up transcribed speech into clearer text."""
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""Clean up this transcribed speech. Make it clearer and more direct while preserving the original meaning and intent. Fix filler words, false starts, and awkward phrasing. Output ONLY the cleaned text, nothing else.

Transcribed speech:
{raw_text}"""
                }
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[CLEANUP ERROR]: {e}")
        return raw_text  # Fall back to original if cleanup fails


def type_text(text: str):
    """Paste text into the currently focused window using clipboard"""
    if not text or not text.strip():
        return

    text = text.strip()
    print(f"\n[INSERTED]: {text}")

    # Save current clipboard
    try:
        old_clipboard = pyperclip.paste()
    except:
        old_clipboard = ""

    # Copy text to clipboard and paste
    pyperclip.copy(text)
    time.sleep(0.05)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)

    # Press Ctrl+Enter twice to create paragraph break
    pyautogui.hotkey('ctrl', 'enter')
    time.sleep(0.05)
    pyautogui.hotkey('ctrl', 'enter')

    # Restore old clipboard
    try:
        pyperclip.copy(old_clipboard)
    except:
        pass

    print("[READY FOR MORE]")


def on_recording_start():
    """Callback when recording starts."""
    set_terminal_title(STATE_RECORDING, "Recording...")

def on_recording_stop():
    """Callback when recording stops (processing)."""
    set_terminal_title(STATE_WAITING, "Processing...")

def main():
    print("""
============================================================
        VOICE INPUT - Speak, Clean, Type
============================================================
  Speak naturally. Your speech is transcribed, cleaned up
  by Claude, then typed into the focused window.

  Pipeline: Mic -> Whisper -> Claude cleanup -> Paste

  How to use:
    1. Run this script
    2. Click on Claude Code terminal to focus it
    3. Speak your prompt
    4. After a pause, cleaned text is pasted

  Commands:
    - Say "exit" or "quit" to stop
    - Press Ctrl+C to force quit
============================================================
    """)

    set_terminal_title(STATE_WAITING, "Loading...")
    print("[LOADING] Initializing Whisper model...")

    recorder = AudioToTextRecorder(
        model="base.en",
        language="en",
        silero_sensitivity=0.4,
        post_speech_silence_duration=1.0,  # Wait 1 second of silence before finalizing
        min_length_of_recording=0.5,
        on_recording_start=on_recording_start,
        on_recording_stop=on_recording_stop,
    )

    set_terminal_title(STATE_READY, "Ready")
    print("[READY] Listening... Focus on Claude Code and speak!\n")
    print("(You have 3 seconds after this message to click on Claude Code)\n")
    time.sleep(3)

    try:
        while True:
            text = recorder.text()

            if text:
                lower_text = text.lower().strip()

                # Exit commands
                if lower_text in ["exit", "quit", "stop", "goodbye"]:
                    set_terminal_title(STATE_WAITING, "Stopped")
                    print("\n[GOODBYE] Stopping.")
                    break

                # Clean up the transcribed text
                print(f"[RAW]: {text}")
                print("[CLEANING UP...]")
                cleaned = cleanup_speech(text)
                print(f"[CLEANED]: {cleaned}")

                # Type the cleaned text
                type_text(cleaned)
                set_terminal_title(STATE_READY, "Ready")
                print("\n[LISTENING]...\n")

    except KeyboardInterrupt:
        set_terminal_title(STATE_WAITING, "Stopped")
        print("\n\n[STOPPED]")


if __name__ == "__main__":
    main()
