# System Architecture

## Overview

The Nerf turret is built as a **real-time control system** with a continuous feedback loop. The system captures video frames, detects people, tracks targets by adjusting servo position, and executes responses based on configuration and detection status.

## High-Level Architecture

```mermaid
graph TB
    subgraph "MAIN CONTROL LOOP"
        Camera[Camera Capture]
        Detection[Detection Engine]
        Tracking[Tracking Logic]
        Response[Response Control]
        
        Camera -->|RGB Frame| Detection
        Detection -->|Bounding Box| Tracking
        Tracking -->|Servo Position| Response
    end
    
    subgraph "HARDWARE ABSTRACTION LAYER"
        CamAPI[Camera API]
        GPIO[GPIO Control]
        ServoCtrl[Servo Control]
    end
    
    Camera --> CamAPI
    Tracking --> ServoCtrl
    Response --> GPIO
    
    subgraph "PHYSICAL HARDWARE"
        PiCam[Pi Camera]
        Relays[Relay Module]
        Servo[Servo Motor]
    end
    
    CamAPI --> PiCam
    GPIO --> Relays
    ServoCtrl --> Servo
    
    Relays --> Blaster[Nerf Blaster]
    Servo --> Blaster
```

---

## Core Components

### 1. Camera Capture Module

```mermaid
flowchart LR
    A[Pi Camera] -->|30 FPS| B[Picamera2 API]
    B -->|RGB Array| C[Optional 180° Rotation]
    C -->|Frame| D[Detection Engine]
    C -->|Frame| E[HTTP Stream Server]
```

**Purpose:** Continuously captures video frames from the Pi Camera

**Implementation:**
- Uses `Picamera2` library for camera interface
- Captures at 640x480 resolution
- Optional 180° rotation for inverted mounting
- Runs in main thread (blocking capture)

**Key Code:**
```python
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
raw = picam2.capture_array()  # Gets frame as numpy array
```

---

### 2. Detection Engine

```mermaid
flowchart TB
    A[RGB Frame] --> B[BGR Conversion]
    B --> C[Blob Creation]
    C --> D[MobileNet-SSD<br/>Neural Network]
    D --> E[Detection Results]
    E --> F{Class 15<br/>Person?}
    F -->|No| G[Continue Scanning]
    F -->|Yes| H{Confidence<br/>>50%?}
    H -->|No| G
    H -->|Yes| I[Valid Detection]
    I --> J[Calculate Bounding Box]
    J --> K[Select Best Target]
    K --> L[Output to Tracking]
```

**Purpose:** Identifies people in captured frames using computer vision

**Implementation:**
- Uses **MobileNet-SSD** pre-trained model
- Detects 20 object classes (we filter for class 15 = person)
- Confidence threshold: 50% (adjustable)
- Runs inference on every captured frame

**Key Algorithm:**
```python
# Convert to blob for neural network
blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
net.setInput(blob)
detections = net.forward()

# Filter for people (class 15) above threshold
for detection in detections:
    if class_id == 15 and confidence > 0.5:
        # Valid person detected
        bounding_box = calculate_box(detection)
```

**Output:** 
- `None` if no person detected
- `(x1, y1, x2, y2)` bounding box coordinates if person found

---

### 3. Tracking Logic

```mermaid
flowchart TB
    A[Bounding Box] --> B[Calculate Target Center]
    B --> C[Apply Exponential Smoothing]
    C --> D[Calculate Horizontal Error]
    D --> E[Compute Adaptive Speed]
    E --> F[Calculate Servo Adjustment]
    F --> G[Clamp to Valid Range]
    G --> H[Update Servo Position]
    H --> I{Error < 12px?}
    I -->|Yes| J[FIRE ZONE]
    I -->|No| K[TRACKING]
```

**Purpose:** Calculates servo adjustments to keep detected person centered

**Key Concepts:**
- **Error Calculation:** Horizontal distance between target center and frame center
- **Smoothing:** Exponential moving average to reduce jitter
- **Adaptive Speed:** Moves faster when far from target, slower when close

**Adaptive Speed Formula:**
```python
distance = abs(error_x)
speed_factor = min(distance / 300, 1.0)  # Normalize to [0, 1]
adaptive_speed = 0.02 + (0.20 - 0.02) × speed_factor
# Result: 0.02 (near center) to 0.20 (far from center)
```

---

### 4. Response Control

```mermaid
flowchart TB
    A{Person Detected?} -->|Yes| B[Switch to TRACKING]
    A -->|No| C{Time Since<br/>Last Target?}
    
    B --> D[Turn ON Flywheel]
    D --> E{Error < Fire Zone?}
    
    E -->|Yes| F[Turn ON Feeder]
    E -->|No| G[Turn OFF Feeder]
    
    F --> H[FIRING]
    G --> I[TRACKING]
    
    C -->|< 5 seconds| J[Keep Motors ON]
    C -->|> 5 seconds| K[Turn OFF All Motors]
    K --> L[Return to SCANNING]
```

**Purpose:** Manages firing mechanism based on tracking state

**Hardware Control:**
```python
# Active-low relays (LOW = ON, HIGH = OFF)
GPIO.output(FLYWHEEL_PIN, GPIO.LOW)   # Turn ON flywheel
GPIO.output(FEEDER_PIN, GPIO.LOW)     # Turn ON feeder
```

---

## State Machine

```mermaid
stateDiagram-v2
    [*] --> SCANNING
    
    SCANNING --> TRACKING : Person Detected<br/>(Confidence > 50%)
    
    state SCANNING {
        [*] --> PanLeft
        PanLeft --> PanRight : Reached Left Limit
        PanRight --> PanLeft : Reached Right Limit
    }
    
    state TRACKING {
        [*] --> FollowTarget
        FollowTarget --> Firing : Error < 12px
        Firing --> FollowTarget : Error > 12px
    }
    
    TRACKING --> SCANNING : No Target for 5s
    
    note right of SCANNING
        • Servo sweeps L↔R
        • All motors OFF
        • Low power mode
    end note
    
    note right of TRACKING
        • Flywheel ON
        • Feeder ON when locked
        • Active response mode
    end note
```

### SCANNING Mode
**Behavior:**
- Servo sweeps left and right at constant speed
- Scan range: -0.2 to 0.8 (servo value)
- Both motors OFF (no power consumption)
- Detection runs every frame looking for people

**State Variables:**
```python
mode = "SCANNING"
scan_direction = 1  # 1 = right, -1 = left
servo_pos += scan_direction × SCAN_STEP
```

**Transition to TRACKING:** When `confidence > 0.5` for class 15 (person)

---

### TRACKING Mode
**Behavior:**
- Servo actively follows detected person
- Flywheel motor ON continuously (fast response time)
- Feeder motor ON only when aim is good (within fire zone)
- Updates servo position based on target location

**State Variables:**
```python
mode = "TRACKING"
smooth_cx = exponential_moving_average(target_center_x)
last_target_seen_time = current_time
```

**Transition to SCANNING:** When `time_since_target > 5.0 seconds`

---

## Data Flow Pipeline

```mermaid
graph TD
    A[Pi Camera Hardware] -->|30 FPS| B[Picamera2 API]
    B -->|RGB Array| C[Frame Processing]
    C -->|BGR Frame| D[MobileNet-SSD]
    C -->|RGB Frame| E[HTTP Stream]
    
    D -->|Detections| F{Person Found?}
    F -->|No| G[Continue Loop]
    F -->|Yes| H[Calculate Target Center]
    
    H --> I[Apply Smoothing]
    I --> J[Calculate Error]
    J --> K[Adaptive Speed]
    K --> L[Servo Adjustment]
    
    L --> M[gpiozero PWM]
    M --> N[Servo Motor]
    
    J --> O{In Fire Zone?}
    O -->|Yes| P[Activate Feeder]
    O -->|No| Q[Deactivate Feeder]
    
    P --> R[RPi.GPIO]
    Q --> R
    R --> S[Relay Module]
    S --> T[Nerf Blaster]
    
    style A fill:#e1f5ff
    style T fill:#ffe1e1
    style D fill:#fff4e1
```

---

## Timing and Performance

```mermaid
gantt
    title Control Loop Timing (per iteration)
    dateFormat X
    axisFormat %L ms
    
    Frame Capture           :a1, 0, 33
    BGR Conversion          :a2, 33, 5
    Detection Inference     :a3, 38, 120
    Tracking Calculation    :a4, 158, 5
    Servo Update            :a5, 163, 2
    GPIO Update             :a6, 165, 2
    
    section Total
    Complete Loop           :milestone, 167, 0
```

### Performance Metrics

| Operation | Target Time | Actual Performance | Status |
|-----------|-------------|-------------------|--------|
| Frame capture | 33ms (30 FPS) | ~33ms | ✅ |
| Detection inference | <150ms | ~100-150ms | ✅ |
| Servo response | <200ms | ~50-100ms | ✅ |
| Total loop time | <200ms | ~100-167ms | ✅ |
| Effective FPS | >5 FPS | 6-10 FPS | ✅ |
| Lost target timeout | 5000ms | Exactly 5000ms | ✅ |

---

## Module Architecture

```mermaid
classDiagram
    class MainControlLoop {
        +Camera camera
        +DetectionEngine detector
        +TrackingLogic tracker
        +ResponseControl responder
        +run()
    }
    
    class Camera {
        +Picamera2 picam2
        +capture_frame()
        +get_resolution()
    }
    
    class DetectionEngine {
        +cv2.dnn.Net model
        +detect_person(frame)
        +filter_detections()
    }
    
    class TrackingLogic {
        +float smooth_cx
        +calculate_error()
        +adaptive_speed()
        +update_servo()
    }
    
    class ResponseControl {
        +bool flywheel_on
        +bool feeder_on
        +control_motors()
        +check_fire_zone()
    }
    
    class HardwareLayer {
        +Servo servo
        +GPIO gpio
        +control_pin()
    }
    
    MainControlLoop --> Camera
    MainControlLoop --> DetectionEngine
    MainControlLoop --> TrackingLogic
    MainControlLoop --> ResponseControl
    ResponseControl --> HardwareLayer
    TrackingLogic --> HardwareLayer
```

---

## Configuration Parameters

### Vision Configuration
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `CONFIDENCE_THRESHOLD` | 0.5 | Detection confidence (0-1) |
| `CAM_RES` | (640, 480) | Camera resolution |
| `FLIP_180` | 1 | Rotate image if inverted |

### Servo Configuration
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `SERVO_PIN` | 12 | GPIO pin for servo |
| `SCAN_LEFT` | -0.2 | Leftmost scan position |
| `SCAN_RIGHT` | 0.8 | Rightmost scan position |
| `SCAN_STEP` | 0.015 | Movement per frame |

### Tracking Configuration
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `FIRE_ZONE` | 12 | Pixels from center to fire |
| `MIN_SPEED` | 0.02 | Minimum servo speed |
| `MAX_SPEED` | 0.20 | Maximum servo speed |
| `TARGET_SMOOTHING` | 0.4 | Smoothing factor (0-1) |
| `LOST_TARGET_TIMEOUT` | 5.0 | Seconds before giving up |

### Hardware Configuration
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `FLYWHEEL_PIN` | 17 | GPIO for flywheel relay |
| `FEEDER_PIN` | 27 | GPIO for feeder relay |
| `RELAY_ACTIVE_LOW` | True | Relay logic level |

---

## Threading Model

```mermaid
graph TB
    subgraph "Main Thread"
        A[Camera Capture<br/>BLOCKING]
        B[Detection Inference<br/>BLOCKING]
        C[Tracking Calculation]
        D[GPIO Updates]
        E[Frame Preparation]
        
        A --> B --> C --> D --> E --> A
    end
    
    subgraph "HTTP Server Thread"
        F[Accept Connections]
        G[Serve HTML]
        H[Stream JPEG Frames]
        
        F --> G
        F --> H
    end
    
    subgraph "Telegram Thread"
        I[Fire-and-Forget<br/>HTTP POST]
    end
    
    E -.->|Shared Frame| H
    C -.->|Event| I
    
    style A fill:#ffe1e1
    style B fill:#ffe1e1
    style F fill:#e1ffe1
    style I fill:#e1e1ff
```

---

## Error Handling Strategy

```mermaid
flowchart TB
    A[System Running] --> B{Hardware Error?}
    
    B -->|Camera Failure| C[Log Error]
    B -->|Servo Failure| C
    B -->|GPIO Failure| C
    
    C --> D[Stop Main Loop]
    D --> E[Emergency Shutdown]
    
    B -->|No Error| F{User Interrupt?}
    
    F -->|Ctrl+C| G[Graceful Shutdown]
    F -->|No| A
    
    G --> H[Turn OFF Flywheel]
    H --> I[Turn OFF Feeder]
    I --> J[Cleanup GPIO]
    J --> K[Stop Camera]
    K --> L[Close Server]
    L --> M[Send Telegram<br/>Shutdown Notice]
    M --> N[Exit]
    
    E --> H
    
    style E fill:#ff9999
    style G fill:#99ff99
```

### Graceful Shutdown Sequence

```python
try:
    while True:
        # Main loop
except KeyboardInterrupt:
    print("Stopped.")
finally:
    print("EMERGENCY STOP")
    GPIO.output(FLYWHEEL_PIN, OFF)  # 1. Motors OFF
    GPIO.output(FEEDER_PIN, OFF)
    GPIO.cleanup()                   # 2. Cleanup GPIO
    servo.value = None               # 3. Release servo
    picam2.stop()                    # 4. Stop camera
    server.shutdown()                # 5. Stop server
    telegram_log("System shutdown")  # 6. Notify
```

**Guarantees:** All motors turn OFF in <100ms

---

## Optional Features Architecture

### 1. HTTP Live Stream

```mermaid
sequenceDiagram
    participant Browser
    participant HTTPServer
    participant MainLoop
    participant Camera
    
    Browser->>HTTPServer: GET /stream
    HTTPServer->>Browser: HTTP 200 (multipart)
    
    loop Every 30ms
        Camera->>MainLoop: Capture frame
        MainLoop->>MainLoop: Process & annotate
        MainLoop->>HTTPServer: Update shared frame
        HTTPServer->>Browser: JPEG frame
    end
    
    Browser->>HTTPServer: Close connection
    HTTPServer->>HTTPServer: Stop stream
```

**Implementation:**
- Threaded HTTP server (`ThreadingMixIn`)
- MJPEG stream (multipart/x-mixed-replace)
- Frame shared via `threading.Lock()`
- JPEG quality: 70%

---

### 2. Telegram Notifications

```mermaid
sequenceDiagram
    participant System
    participant TelegramAPI
    participant User
    
    System->>System: Event occurs<br/>(e.g., Target acquired)
    System->>System: Capture frame
    System->>System: Encode JPEG
    
    System->>TelegramAPI: POST /sendPhoto<br/>(non-blocking, 5s timeout)
    
    alt Success
        TelegramAPI->>User: Push notification
        TelegramAPI->>System: 200 OK
    else Failure
        TelegramAPI->>System: Error/Timeout
        System->>System: Log error, continue
    end
    
    Note over System: Main loop never blocks
```

**Events Tracked:**
- System start/stop
- Target acquired/lost
- Firing started/stopped

---

## System Integration Diagram

```mermaid
graph TB
    subgraph "Raspberry Pi"
        subgraph "Python Application"
            Main[main.py]
            Cam[Camera Thread]
            Det[Detection Engine]
            Track[Tracking Logic]
            Resp[Response Control]
            Stream[HTTP Server]
            
            Main --> Cam
            Main --> Det
            Main --> Track
            Main --> Resp
            Main --> Stream
        end
        
        subgraph "Operating System"
            LibCam[libcamera]
            Pigpio[pigpio daemon]
            GPIO_Sys[GPIO System]
        end
        
        Cam --> LibCam
        Track --> Pigpio
        Resp --> GPIO_Sys
    end
    
    subgraph "Physical Hardware"
        PiCam[Pi Camera Module]
        Servo[MG996R Servo]
        Relay[2-Ch Relay Module]
        Blaster[Nerf Blaster]
    end
    
    LibCam <--> PiCam
    Pigpio <--> Servo
    GPIO_Sys <--> Relay
    Relay --> Blaster
    Servo --> Blaster
    
    subgraph "External Services"
        Telegram[Telegram Bot API]
        Browser[Web Browser]
    end
    
    Main -.->|HTTP POST| Telegram
    Stream -.->|MJPEG Stream| Browser
    
    style Main fill:#4a90e2
    style PiCam fill:#e1f5ff
    style Blaster fill:#ffe1e1
```

---

## Performance Optimization Strategies

```mermaid
mindmap
    root((Performance))
        Hardware
            Continuous Flywheel
                Eliminates 500ms spin-up
                Instant firing capability
            Separate Power
                Stable voltage for servo
                No brownouts
        Software
            Adaptive Speed
                Fast: far from target
                Slow: near target
                Reduces oscillation
            Target Smoothing
                EMA filter
                Reduces jitter
                Stable tracking
            Asynchronous Stream
                Non-blocking
                Independent thread
                Drops frames if slow
        Algorithm
            Single Pass Detection
                No redundant processing
            Best Target Selection
                Highest confidence
                Closest/largest
```

---

## Security & Safety Architecture

```mermaid
graph TD
    subgraph "Safety Layers"
        A[Software Timeout]
        B[GPIO Cleanup]
        C[Active-Low Relays]
        D[Emergency Stop]
        
        A -->|5s no target| E[Motors OFF]
        B -->|On exit| E
        C -->|Power loss| E
        D -->|Ctrl+C| E
    end
    
    subgraph "Security Considerations"
        F[No Authentication]
        G[Hardcoded Token]
        H[Local Network Only]
        
        F -.-> I[Low Risk<br/>Prototype]
        G -.-> I
        H -.-> I
    end
    
    style E fill:#99ff99
    style I fill:#ffff99
```

---

## Dependencies

```mermaid
graph LR
    A[main.py] --> B[picamera2]
    A --> C[opencv-python]
    A --> D[gpiozero]
    A --> E[RPi.GPIO]
    A --> F[requests]
    
    B --> G[libcamera]
    D --> H[pigpio]
    
    C --> I[MobileNetSSD<br/>Model Files]
    
    style A fill:#4a90e2
    style I fill:#ffe1e1
```

### Model Details
- **Framework:** Caffe
- **Input:** 300×300 RGB
- **Output:** 20 object classes
- **Performance:** ~100-150ms on Pi 4
- **Accuracy:** Good for 2-10m range

---

## Summary

```mermaid
mindmap
    root((Nerf Turret<br/>Architecture))
        Design Principles
            Real-time Responsiveness
                <200ms reaction
            Reliability
                Fail-safe hardware
                Graceful shutdown
            Simplicity
                Minimal threading
                Clear control flow
            Safety
                Timeouts
                Emergency stops
                Non-lethal only
        Key Features
            Vision System
                MobileNet-SSD
                6-10 FPS detection
            Tracking
                Adaptive speed
                Target smoothing
            Response
                Continuous flywheel
                Precision firing
        Educational Value
            Embedded Systems
                Sensor fusion
                State machines
                Real-time control
            Software Engineering
                Hardware abstraction
                Multi-threading
                Error handling
```

The architecture prioritizes **safe, predictable behavior** over maximum performance, making it suitable for prototype demonstration and educational purposes.