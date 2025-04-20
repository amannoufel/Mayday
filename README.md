

## 🆘 Mayday Emergency Voice Detector with PDF Navigation

This Python project uses the [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) speech recognition model to detect emergency voice commands (like "Mayday") in real-time, activate an emergency protocol, and open specific pages in a PDF emergency manual. It also sends signals to an Arduino for physical emergency indications (e.g., LED, buzzer, or alert system).

### 🎯 Features
- **Real-time voice recognition** using Faster-Whisper
- **Emergency protocol activation** on detecting the keyword "mayday"
- **Context-aware commands** like "runway", "engine failure", or "nose cone crash"
- **Automatic opening of PDF emergency manual** to specific pages
- **Serial communication with Arduino** for sending emergency signals
- **Lightweight and fast** — optimized for minimal latency

### 🛠️ Requirements

#### Python Packages
Install required libraries:
```bash
pip install torch numpy sounddevice faster-whisper pyserial
```

#### Additional Requirements
- **CUDA** (for GPU support — optional but recommended)
- **Foxit PDF Reader** (optional — uses your default browser if not installed)
- **Arduino** connected via serial (e.g., COM9)

### 📁 File Setup

Ensure you have the following:
- Place your `mayday.pdf` in the correct path and update the path in the script:
  ```python
  pdf_file = os.path.abspath("C:/Users/YourUsername/Desktop/main/whisper/mayday/mayday.pdf")
  ```
- Update your **serial port**:
  ```python
  SERIAL_PORT = "COM9"  # Change to your Arduino's port
  ```

### 🔊 Voice Commands

After launching the program, it listens continuously. Use the following commands:

1. **Trigger Emergency Mode**
   ```
   mayday mayday mayday
   ```
2. **Specify Emergency Type**
   - `"runway"` → Opens page 1 of PDF
   - `"engine failure"` or `"engine"` → Opens page 2
   - `"nose cone crash"` or `"descending rapidly"` → Opens page 3

### 🚀 Running the Program

```bash
python mayday_detector.py
```

Once started:
- It listens to the mic for audio input.
- Upon hearing "mayday" 2–3 times, it sends `"start"` to the Arduino and activates emergency mode.
- Then listens for keywords to open relevant PDF manual pages.

### 📦 Arduino Integration

The script sends the string `"start\n"` over serial to your Arduino. Example Arduino sketch:
```cpp
void setup() {
  Serial.begin(9600);
  pinMode(13, OUTPUT); // Built-in LED
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    if (command == "start") {
      digitalWrite(13, HIGH);  // Indicate emergency
      delay(3000);
      digitalWrite(13, LOW);
    }
  }
}
```

### 🧠 Model Info

Using the `"medium.en"` variant of Faster-Whisper for faster performance and English-only processing. Model runs on GPU if available.

---
