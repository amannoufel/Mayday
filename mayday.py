import threading
import queue
import tempfile
import os
import sys
import time
import torch
import whisper
import numpy as np
import sounddevice as sd
from datetime import datetime

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
DEVICE = "pulse"  # Set to None to use default device
CHUNK_DURATION = 3  # seconds
LANGUAGE = "en"  # Change to your language code

class LiveTranscriber:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.recording = False
        self.full_transcript = []
        
        # Set up device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Load the Whisper medium model with half-precision to save VRAM
        print("Loading Whisper medium model...")
        self.model = whisper.load_model("small", device=self.device)
        print("Model loaded!")
        
        # Create output directory
        self.output_dir = "transcripts"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create temporary directory for audio chunks
        self.temp_dir = tempfile.mkdtemp()
        
    def audio_callback(self, indata, frames, time, status):
        """This is called for each audio block."""
        if status:
            print(f"Audio callback status: {status}")
        if self.recording:
            self.audio_queue.put(indata.copy())
            
    def process_audio(self):
        """Process audio from the queue and transcribe it."""
        while self.recording:
            if not self.audio_queue.empty():
                # Get audio data
                audio_data = self.audio_queue.get()
                
                # Save to temporary file
                temp_file = os.path.join(self.temp_dir, f"chunk_{time.time()}.wav")
                
                # Convert from float32 to int16
                audio_data_int = (audio_data * 32767).astype(np.int16)
                
                import soundfile as sf
                sf.write(temp_file, audio_data_int, SAMPLE_RATE)
                
                # Transcribe
                try:
                    options = {
                        "fp16": True,
                        "language": LANGUAGE,
                        "task": "transcribe",
                    }
                    
                    result = self.model.transcribe(temp_file, **options)
                    transcript = result["text"].strip()
                    
                    if transcript:
                        self.result_queue.put(transcript)
                        self.full_transcript.append(transcript)
                        
                        # Print the transcript
                        print(f"\nTranscript: {transcript}")
                    
                    # Clean up temporary file
                    os.remove(temp_file)
                    
                except Exception as e:
                    print(f"Error transcribing audio: {e}")
            
            else:
                # If no audio in queue, sleep briefly to prevent CPU spinning
                time.sleep(0.1)
                
    def start(self):
        """Start recording and transcribing."""
        self.recording = True
        
        # Start the processing thread
        self.process_thread = threading.Thread(target=self.process_audio)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        print("\nStarting live transcription...")
        print("Press Ctrl+C to stop recording\n")
        
        # Start recording
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                callback=self.audio_callback,
                blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
                device=DEVICE
            ):
                # Keep main thread alive
                while self.recording:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            print(f"Error in audio stream: {e}")
            self.stop()
            
    def stop(self):
        """Stop recording and save the transcript."""
        print("\nStopping transcription...")
        self.recording = False
        
        # Wait for processing to complete
        if hasattr(self, 'process_thread') and self.process_thread.is_alive():
            self.process_thread.join(timeout=2)
            
        # Save full transcript
        if self.full_transcript:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"transcript_{timestamp}.txt")
            
            with open(output_file, "w") as f:
                f.write("\n".join(self.full_transcript))
                
            print(f"\nFull transcript saved to: {output_file}")
        else:
            print("\nNo transcript to save.")
            
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")

def list_audio_devices():
    """List all available audio input devices."""
    print("\nAvailable audio input devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"[{i}] {device['name']} (Inputs: {device['max_input_channels']})")
    print()

if __name__ == "__main__":
    # List available audio devices
    list_audio_devices()
    
    # Ask user to select a device
    try:
        device_id = input("Enter device number to use (or press Enter for default): ").strip()
        if device_id:
            DEVICE = int(device_id)
    except ValueError:
        print("Invalid device ID, using default device.")
        DEVICE = None
    
    transcriber = LiveTranscriber()
    transcriber.start()