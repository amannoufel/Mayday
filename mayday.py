import torch
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import threading
import queue
import time
import subprocess
import os
import platform
import webbrowser
import serial  # For serial communication

# Load a smaller, faster Whisper model for better responsiveness
model = WhisperModel("medium.en", device="cuda" if torch.cuda.is_available() else "cpu", compute_type="float16")

# Audio parameters - shorter block for faster response
samplerate = 16000
channels = 1
block_duration = 1.5  # Reduced for faster response
buffer_duration = 0.3

# Create a queue for audio blocks
audio_queue = queue.Queue()
running = True

# Emergency mode flag
emergency_mode_active = False

# PDF file path - use absolute path for reliability
pdf_file = os.path.abspath("mayday.pdf")  # Update this path to the location of your PDF

# Serial port settings
SERIAL_PORT = "COM9"  # Change this to match your Arduino's port (e.g., "/dev/ttyUSB0" or "/dev/cu.usbmodemXXXX")
BAUD_RATE = 9600  # Must match Arduino's baud rate

# Open serial connection at the start of the program
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

def send_serial_message(message):
    try:
        ser.write((message + "\n").encode())  # Append newline for Arduino
        print(f"Sent to Arduino: {message}")
    except Exception as e:
        print(f"Error sending serial message: {e}")



def open_pdf_at_page(pdf_path, page_number):
    """
    Open the PDF file at the specified page using Foxit Reader (if available),
    or fallback to the default PDF viewer.
    """
    try:
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file '{pdf_path}' not found.")
            return False

        foxit_path = r"C:\Program Files (x86)\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe"
        if os.path.exists(foxit_path):
            subprocess.run([foxit_path, "/A", f"page={page_number}", pdf_path])
        else:
            print("⚠️ Foxit Reader not found. Opening in default browser...")
            webbrowser.open(pdf_path)

        print(f"\n{'*' * 50}")
        print(f"📖 Opening PDF at page {page_number} using Foxit Reader")
        print(f"{'*' * 50}\n")

        return True
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return False




def open_pdf_at_page(pdf_path, page_number):
    """
    Open the PDF file at the specified page using an HTML wrapper.
    """
    try:
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file '{pdf_path}' not found.")
            return False
        
        # Create HTML wrapper that embeds the PDF and navigates to the page
        html_path = create_pdf_html_wrapper(pdf_path, page_number)
        
        # Open the HTML file in the default browser
        html_url = f"file://{os.path.abspath(html_path)}"
        webbrowser.open(html_url)
        
        # Display confirmation in console
        print(f"\n{'*' * 50}")
        print(f"EMERGENCY! Opening PDF at page {page_number}")
        print(f"{'*' * 50}\n")
        
        return True
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return False

def audio_callback(indata, frames, time_info, status):
    """Callback function for the audio stream."""
    if status:
        print(f"Stream status: {status}")
    # Add audio data to the queue
    audio_queue.put(indata.copy())

def process_audio():
    """Process audio blocks from the queue."""
    global running, emergency_mode_active
    
    # Buffer to store audio that overlaps between processing blocks
    audio_buffer = np.zeros(0, dtype=np.float32)
    
    while running:
        # Collect audio data until we have enough for processing
        while not audio_queue.empty():
            new_audio = audio_queue.get()
            audio_buffer = np.append(audio_buffer, np.squeeze(new_audio))
        
        # If we have enough audio data to process
        if len(audio_buffer) >= (block_duration * samplerate):
            # Extract the block to process
            process_length = int(block_duration * samplerate)
            audio_to_process = audio_buffer[:process_length]
            
            # Keep a small buffer for overlap to avoid cutting words
            retain_samples = int(buffer_duration * samplerate)
            audio_buffer = audio_buffer[process_length - retain_samples:]
            
            # Use beam_size=1 and best_of=1 for faster processing
            segments, info = model.transcribe(audio_to_process, vad_filter=True, 
                                              beam_size=1, best_of=1)
            transcription = "".join(segment.text for segment in segments).strip()
            
            if transcription:
                print(f"Heard: {transcription}")
                transcription_lower = transcription.lower()
                
                # If already in emergency mode, listen for specific emergency keywords
                if emergency_mode_active:
                    if "runway" in transcription_lower:
                        page = 1
                        print(f"\n🛫 RUNWAY EMERGENCY DETECTED - Opening procedure manual page {page}")
                        open_pdf_at_page(pdf_file, page)
                        emergency_mode_active = False  # Reset emergency mode
                        
                    elif "engine failure" in transcription_lower or "engine" in transcription_lower:
                        page = 2
                        print(f"\n🔧 ENGINE FAILURE DETECTED - Opening procedure manual page {page}")
                        open_pdf_at_page(pdf_file, page)
                        emergency_mode_active = False  # Reset emergency mode
                        
                    elif ("descending" in transcription_lower and "rapidly" in transcription_lower) or \
                         ("descending" in transcription_lower and "rapidly" in transcription_lower) or \
                         "descending rapidly" in transcription_lower or "Descending rapidly" in transcription_lower:
                        page = 3
                        print(f"\n💥 NOSE CONE CRASH DETECTED - Opening procedure manual page {page}")
                        open_pdf_at_page(pdf_file, page)
                        emergency_mode_active = False  # Reset emergency mode
                        
                # Check for "mayday" repeated three times (or leniently two times) to activate emergency mode
                elif transcription_lower.count("mayday") >= 3 or "mayday mayday mayday" in transcription_lower or "may day may day may day" in transcription_lower or "mayday mayday" in transcription_lower:
                    print("\n🚨 EMERGENCY PROTOCOL ACTIVATED - MAYDAY SEQUENCE DETECTED 🚨")
                    print("Sending emergency signal to Arduino...")
                    
                    send_serial_message("start")  # Send "start" to Arduino
                    
                    print("Listening for emergency type... (runway, engine failure, or nose cone crash)")
                    emergency_mode_active = True
        
        # Short sleep to prevent CPU overuse
        time.sleep(0.05)

def main():
    global running
    
    print("Live Mayday Emergency Detector with PDF Navigation")
    print("-------------------------------------------------")
    print("Listening for audio... Say 'mayday mayday mayday' to activate emergency protocol.")
    print("Then specify the emergency type:")
    print("  - Say 'runway' to open emergency manual page 1")
    print("  - Say 'engine failure' to open emergency manual page 2")
    print("  - Say 'nose cone crash' to open emergency manual page 3")
    print(f"PDF file location: {pdf_file}")
    print("Press Ctrl+C to stop.")
    
    # Start the audio processing thread
    process_thread = threading.Thread(target=process_audio)
    process_thread.daemon = True
    process_thread.start()
    
    try:
        # Start the audio stream with a shorter block size for faster response
        block_size = int(samplerate * 0.05)  # 50ms blocks for lower latency
        with sd.InputStream(callback=audio_callback, channels=channels, 
                            samplerate=samplerate, dtype='float32',
                            blocksize=block_size):
            print("Stream started. Speak into the microphone...")
            # Keep the main thread alive
            while True:
                time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        running = False
        process_thread.join(timeout=1.0)
        print("Program terminated.")

if __name__ == "__main__":
    main()
