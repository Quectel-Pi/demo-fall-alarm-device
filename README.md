# Fall Alarm Application

English| [中文](README_zh.md)

This project is a fall detection intelligent monitoring application based on the Quectel Pi H1 single-board computer. It collects video frames in real-time through a USB camera, uses YOLOv8-Pose for human keypoint detection, and employs a pre-trained Random Forest classifier to determine whether a user has fallen. When a fall is detected, an alarm light is automatically activated and alarm images are uploaded.

![Fall Detection Demo](tools/demo.png)

## Features

- **Real-time Human Pose Recognition based on YOLOv8-Pose**
  - Real-time detection of 17 human keypoints
  - Support for simultaneous multi-person detection
  - CPU inference, no GPU required

- **Intelligent Fall Detection**
  - Random Forest classifier-based judgment
  - Multi-feature fusion (keypoints, angles, body shape)
  - Continuous frame confirmation to effectively reduce false positives

- **Automatic Alarm Mechanism**
  - Alarm light activation upon fall detection
  - Automatic alarm image saving
  - Upload to remote server, receive notifications and view images in the app

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

### Dependency Installation

```bash
pip install -r requirements.txt
```

### System Dependencies (Linux)

```bash
# Basic dependencies
sudo apt-get install python3-pip libatlas-base-dev libjasper-dev

# Optional: Serial communication support (alarm light control)
sudo apt-get install python3-serial
```

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
│   ├── yolov8n-pose.pt          # YOLOv8-Nano Pose model
│   ├── fall_multi_person_model.pkl      # Random Forest classifier (fall detection)
│   └── feature_scaler_multi.pkl         # Feature scaler
│
├── picture/                     # Alarm image storage directory (auto-created at runtime)
│   ├── fall_20240326_143022.jpg # Example alarm image
│   └── ...
│
└── fall_train/                  # Model training tools directory (reference implementation)
    ├── extract_features_yolo.py # Feature extraction script
    ├── train_model_yolo.py      # Model training script
    ├── fall_multi_person_features.csv   # Feature dataset
    └── fall_dataset/            # Training data directory
        ├── down/                # Fall posture images
        ├── sit/                 # Sitting posture images
        └── up/                  # Standing/walking posture images
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
│  ├── pip install -r requirements.txt                        
│  └── sudo apt-get install python3-serial (optional)         
│                                                              
│  Step 3: Run Fall Detection Application                     
│  ├── cd src                                                 
│  ├── python3 main.py                                        
│  ├── starts camera preview        
│  └── Alarm automatically activates when fall detected       
│                                                                                       
└─────────────────────────────────────────────────────────────
```

### Install Dependencies

**Run command:**

```bash
pip install -r requirements.txt
```

**Optional dependencies (alarm light functionality):**

```bash
sudo pip install pyserial
sudo usermod -a -G dialout $USER  # Configure serial port permissions
```

### Run Application

**Run command:**

```bash
cd src
python3 main.py
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

Key parameters related to fall detection can be modified in `src/fall_detector.py`:

```python
# Keypoint detection configuration
MIN_CONFIDENCE = 0.4           # Keypoint confidence threshold
MIN_KEYPOINTS = 10             # Minimum number of valid keypoints
YOLO_IMG_SIZE = 320            # YOLOv8 input image size

# Fall detection threshold
FALL_BODY_ANGLE_THRESHOLD = 55        # Body angle threshold (degrees)
FALL_HEIGHT_RATIO_THRESHOLD = 1.2     # Body height-width ratio threshold
FALL_MIN_CONFIDENCE = 0.75            # Classifier confidence threshold
FALL_CONFIRM_FRAMES = 3               # Fall confirmation frame count
```

### Server Configuration

Alarm image upload-related configuration in `src/camera_manager.py`:

```python
SERVER_IP = "118.25.198.12" # Replace with your server IP address
SERVER_UPLOAD_URL = f"http://{SERVER_IP}:8000/upload_fall" # Replace with your server upload endpoint
FALL_SAVE_INTERVAL = 1.0
```

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
Random Forest Classifier Inference
   ↓
Fall Confidence Assessment
   ↓
Continuous Frame Confirmation (FALL_CONFIRM_FRAMES)
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
# List available cameras
ls -la /dev/video*

# View detailed information using v4l2-ctl
v4l2-ctl --list-devices
v4l2-ctl --list-formats -d /dev/video0
```

**Q: Camera preview is laggy or has high latency**

A: Optimize performance:
1. Lower resolution: change to 640×480
2. Increase detection interval: `DETECT_INTERVAL = 0.3`
3. Lower YOLOv8 input size: `YOLO_IMG_SIZE = 256`
4. Disable upload feature for local testing

### Fall Detection

**Q: High false positive rate (normal movements detected as falls)**

A: Adjust parameters to reduce false positives:
1. Increase classifier threshold: `FALL_MIN_CONFIDENCE = 0.85`
2. Increase confirmation frame count: `FALL_CONFIRM_FRAMES = 5`
3. Increase angle and ratio thresholds
4. Retrain classifier with more negative samples (sitting down, bending, etc.)

**Q: High miss detection rate (actual falls not detected)**

A: Adjust parameters to increase sensitivity:
1. Lower classifier threshold: `FALL_MIN_CONFIDENCE = 0.70`
2. Lower confirmation frame count: `FALL_CONFIRM_FRAMES = 2`
3. Lower keypoint requirement: `MIN_KEYPOINTS = 8`
4. Optimize camera angle (distance 1-3m, height 1.5-2m)

**Q: Can only detect falls in specific directions**

A: Retrain the model:
1. Add fall samples from multiple directions in `fall_dataset/down/`
2. Include forward, sideways, and backward falls
3. Increase data volume (at least 500 images per class)
4. Re-run the training script

## Performance Optimization

### Inference Acceleration

```python
# Lower YOLOv8 input size
YOLO_IMG_SIZE = 256  # Reduce from 320

# Increase detection interval
DETECT_INTERVAL = 0.2  # Increase from 0.15
```

### Memory Optimization

```python
# Regularly clear logs
if len(LogManager._logs) > 100:
    LogManager.clear_logs()

# Limit image saving frequency
FALL_SAVE_INTERVAL = 1.0  # Save at most one image per second
```

### Reduce False Positives

Use continuous frame confirmation and high confidence thresholds:

```python
FALL_CONFIRM_FRAMES = 5      # 5 consecutive frames to confirm a fall
FALL_MIN_CONFIDENCE = 0.80   # Classifier confidence >= 0.8
```