# Fall Alarm Application

English| [中文](README_zh.md)

This project is an on-device fall detection application based on the Quectel Pi H1 smart mainboard. It captures video frames in real time through a USB camera, uses YOLOv8-Pose to extract human keypoints, and then applies a pre-trained Random Forest classifier to determine whether the monitored person has fallen. When a fall is detected, an alarm light is activated automatically and alarm images are uploaded.

![Fall Detection Demo](tools/demo.png)

## Features

- **Real-time Human Pose Recognition based on YOLOv8-Pose**
  - Real-time detection of 17 human keypoints
  - Support for simultaneous multi-person detection
  - CPU inference, no GPU required

- **Intelligent Fall Detection**
  - Random Forest classifier for posture classification
  - Multi-feature fusion (keypoints, angles, body shape)
  - Secondary verification by geometric rules (torso angle, height/width ratio, keypoint distribution) — a fall is confirmed only when both pass

- **Automatic Alarm Mechanism**
  - Alarm light activation upon fall detection
  - Automatic alarm image saving
  - Upload to remote server, receive notifications and view images in the mobile app

---

## Environment Configuration

### System Requirements

- **Operating System**: Linux/Debian 13
- **Python Version**: 3.8+
- **Qt Version**: Qt6 (via PySide6)
- **OpenCV Version**: 4.8+
- **PySide6 Version**: 6.5+
- **numpy Version**: 1.24+
- **scikit-learn Version**: 1.3+
- **ultralytics Version**: 8.0+

### System Dependencies (Linux / Debian 13)

```bash
sudo apt update && sudo apt install -y \
    python3-pip \
    python3-venv \
    libopenblas-dev \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0t64 \
    v4l-utils
```

> Note: Debian 13 has removed old package names such as `libatlas-base-dev`, `libjasper-dev`, and `libgl1-mesa-glx`. The scientific-computing base is now `libopenblas-dev`; `v4l-utils` provides `v4l2-ctl` for camera troubleshooting.

### Dependency Installation (a virtual environment is recommended)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> The serial library `pyserial` is already included in `requirements.txt` and does not need to be installed separately.

---

## Project Code Structure

```
├── requirements.txt             # Python dependency list
├── README.md                    # Project documentation (English)
├── README_zh.md                 # Project documentation (Chinese)
│
├── src/                         # Fall detection application source code
│   ├── main.py                  # Main entry point, starts the fall detection app
│   ├── camera_manager.py        # Camera management class, handles video capture, preview, fall detection
│   ├── fall_detector.py         # Fall detector, YOLOv8 inference and classification
│   ├── light_control.py         # Alarm light control via serial communication
│   ├── ui_manager.py            # UI manager, PySide6 GUI implementation
│   └── log_manager.py           # Log management class
│
├── model/                       # Pre-trained models directory
│   ├── yolov8n-pose.pt                  # YOLOv8-Nano Pose model
│   ├── fall_multi_person_model.pkl      # Random Forest classifier (fall detection)
│   ├── feature_scaler_multi.pkl         # Feature scaler
│   └── model_info_multi.pkl             # Model metadata
│
├── tools/                       # Demo assets and mobile app package
│   ├── demo.png / demo2.png     # Demo screenshots
│   └── FallAlarm.apk            # Mobile app installer
│
└── picture/                     # Alarm image storage directory (auto-created at runtime)
    ├── fall_20240326_143022.jpg # Example alarm image
    └── ...
```
---

## Hardware Requirements

### USB Camera (Specifications are not strictly required; the following are specs used in this project)

- **Interface Type**: USB
- **Resolution Requirements**:
  - Recommended resolution: 1280×720 or higher
  - Support for other standard USB camera resolutions
- **Frame Rate**: Support for 15fps or above
- **Output Format**: YUYV/MJPG

### Alarm Light (Optional)

- **Interface Type**: USB to serial or GPIO
- **Communication Protocol**: Serial communication (9600 bps baud rate)
- **Control Command**: Hexadecimal instruction sequence

### Runtime Environment

- **Development Board/PC**: Linux device supporting USB camera
- **Memory**: Recommended 2GB or above (for YOLOv8 inference)
- **GPU**: Not required (pure CPU computing)
- **Network**: Optional (for uploading alarm images to server)

---

## Usage Flow

### Complete Fall Detection Flow

```
┌─────────────────────────────────────────────────────────────
│               Fall Detection Application Usage Flow          
├─────────────────────────────────────────────────────────────
│  Step 1: Prepare Model Files                                
│  ├── Download yolov8n-pose.pt to model/ (or use existing)                      
│  ├── Prepare fall_multi_person_model.pkl         
│  └── Prepare feature_scaler_multi.pkl             
│                                                             
│  Step 2: Install Dependencies                              
│  ├── python3 -m venv venv && source venv/bin/activate       
│  └── pip install -r requirements.txt                        
│                                                              
│  Step 3: Run Fall Detection Application                     
│  ├── cd src                                                 
│  ├── python3 main.py (activate venv first)                  
│  ├── starts camera preview        
│  └── Alarm automatically activates when fall detected       
│                                                                                       
└─────────────────────────────────────────────────────────────
```

### Install Dependencies

**Run command:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Serial port permissions (alarm light functionality, optional):**

```bash
sudo usermod -a -G dialout $USER  # takes effect after re-login
```

### Run Application

**Run command:**

```bash
cd src
python3 main.py    # make sure the venv is activated (source ../venv/bin/activate)
```

![Fall Detection Demo](tools/demo2.png)

**Application Interface Description:**

| Interface Area | Function Description |
|---|---|
| Camera Preview | Displays real-time video stream with detected persons and fall status |
| Log Area | Displays model loading, detection results, alarm status, etc. |
| Alarm Alert | Top of screen shows fall alarm information (with timestamp) |
| Status Bar | Shows current camera, FPS, detection status |

**Demo Case**

![Fall Detection Demo](tools/demo.png)

---

## Detection Parameter Configuration

**Keypoint and geometric-rule parameters** (`src/fall_detector.py`):

```python
# Keypoint detection configuration
MIN_CONFIDENCE = 0.4           # Keypoint confidence threshold
MIN_KEYPOINTS = 10             # Minimum number of valid keypoints
YOLO_IMG_SIZE = 320            # YOLOv8 input image size

# Fall detection thresholds (geometric rules)
FALL_BODY_ANGLE_THRESHOLD = 55        # Torso angle threshold (degrees); angle > value scores
FALL_HEIGHT_RATIO_THRESHOLD = 1.2     # Body height/shoulder-width ratio (H/W); ratio < value scores
```

**Classifier and detection-frequency parameters** (`src/camera_manager.py`):

```python
DETECT_INTERVAL = 0.15            # Detection interval (seconds)
FALL_CONFIDENCE_THRESHOLD = 0.75  # Classifier / confidence threshold
FALL_DISPLAY_DURATION = 1.0       # How long the overlay stays after a detection (seconds)
```

### Server Configuration

Alarm image upload-related configuration in `src/camera_manager.py`:

```python
SERVER_IP = "118.31.23.236"   # Replace with your server IP address
SERVER_UPLOAD_URL = f"http://{SERVER_IP}:8000/upload_fall"  # Replace with your server upload endpoint
self._fall_save_interval = 1.0  # Minimum interval between alarm image saves/uploads (seconds)
```

> Uploads are asynchronous in a background thread and do not block the main program. There is currently no "disable upload" switch; to turn it off, comment out the upload call inside `_save_fall_detection()`.

## Technical Principles

### Fall Detection Flow

```
Video Capture
   ↓
YOLOv8-Pose Keypoint Detection (17 keypoints)
   ↓
Feature Extraction (keypoints, angles, body shape)
   ↓
Feature Normalization (using scaler)
   ↓
Random Forest Classifier Inference (label 2 = fall)
   ↓
Secondary Verification by Geometric Rules (torso angle, height/width ratio, keypoint distribution)
   ↓
Both pass AND confidence ≥ FALL_CONFIDENCE_THRESHOLD
   ↓
Trigger Alarm → Activate Alarm Light → Save Image → Upload to Server
```

---

## FAQ

### Model Loading

**Q: Model loading fails with "Model not found"**

A: Check the following:
1. Ensure the `model/` directory exists
2. Check if model filenames are correct
   - `yolov8n-pose.pt`
   - `fall_multi_person_model.pkl`
   - `feature_scaler_multi.pkl`
3. Try downloading the model manually:
   ```bash
   mkdir -p model
   wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt \
        -O model/yolov8n-pose.pt
   ```

### Camera

**Q: Camera not found or cannot be opened**

A: Check camera connection:

```bash
# 1) First confirm the camera is enumerated on the USB bus (most important)
lsusb
dmesg | grep -i uvc

# 2) Then check the video device nodes
ls -la /dev/video*

# 3) View detailed information using v4l2-ctl (requires: apt install v4l-utils)
v4l2-ctl --list-devices
v4l2-ctl --list-formats -d /dev/video0
```

> ⚠️ The QCS6490's on-chip dual ISP / hardware codecs create many `/dev/video*` nodes (e.g. video0/1/10/32/33) **even with no camera plugged in**. So `ls -la /dev/video*` alone cannot tell whether a USB camera is detected — check `lsusb` / `dmesg` first.

**Q: Camera preview is laggy or has high latency**

A: Optimize performance:
1. Lower resolution: change to 640×480
2. Increase detection interval: `DETECT_INTERVAL = 0.25` (`src/camera_manager.py`)
3. Lower YOLOv8 input size: `YOLO_IMG_SIZE = 256` (`src/fall_detector.py`); an overly small size noticeably reduces confidence for distant/occluded targets — re-test after adjusting
4. Check the capture side: too-high resolution, MJPG not taking effect, etc. (image upload is asynchronous and generally does not block the main thread)

### Fall Detection

**Q: High false positive rate (normal movements detected as falls)**

A: Adjust parameters to reduce false positives:
1. Increase classifier/confidence threshold: `FALL_CONFIDENCE_THRESHOLD = 0.80` (`src/camera_manager.py`)
2. Tighten the geometric rules (`src/fall_detector.py`):
   - `FALL_BODY_ANGLE_THRESHOLD = 65` (was 55; angle > value scores, so a larger value is stricter)
   - `FALL_HEIGHT_RATIO_THRESHOLD = 1.0` (was 1.2; H/W < value scores, so a smaller value is stricter)
3. Retrain the classifier with more negative samples (sitting down, bending, etc.)

**Q: High miss detection rate (actual falls not detected)**

A: Adjust parameters to increase sensitivity:
1. Lower classifier/confidence threshold: `FALL_CONFIDENCE_THRESHOLD = 0.65` (`src/camera_manager.py`)
2. Relax the geometric rules (`src/fall_detector.py`):
   - `FALL_BODY_ANGLE_THRESHOLD = 50` (was 55; lower is looser)
   - `FALL_HEIGHT_RATIO_THRESHOLD = 1.4` (was 1.2; higher is looser)
3. Relax the keypoint gate: `MIN_KEYPOINTS = 8`, `MIN_CONFIDENCE = 0.3`
4. Optimize camera angle (distance 1-3m, height 1.5-2m)

**Q: Can only detect falls in specific directions**

A: Retrain the model:
1. Add fall samples from multiple directions to the training dataset
2. Include forward, sideways, and backward falls
3. Increase data volume (at least 500 images per class)
4. Re-run the training script

## Performance Optimization

### Inference Acceleration

```python
# Lower YOLOv8 input size (src/fall_detector.py)
YOLO_IMG_SIZE = 256  # Reduce from 320; too small reduces detection of distant/occluded targets

# Increase detection interval (src/camera_manager.py)
DETECT_INTERVAL = 0.2  # Increase from 0.15
```

### Memory Optimization

```python
# Regularly clear logs
if len(LogManager._logs) > 100:
    LogManager.clear_logs()
```

Limit the alarm image saving frequency: `self._fall_save_interval = 1.0` in `src/camera_manager.py` (at most one image per second by default).

### Reduce False Positives

Raise the classifier threshold and tighten the geometric rules:

```python
# src/camera_manager.py
FALL_CONFIDENCE_THRESHOLD = 0.80   # Classifier / confidence >= 0.8

# src/fall_detector.py
FALL_BODY_ANGLE_THRESHOLD = 65     # Larger angle threshold is stricter
FALL_HEIGHT_RATIO_THRESHOLD = 1.0  # Smaller H/W threshold is stricter
```