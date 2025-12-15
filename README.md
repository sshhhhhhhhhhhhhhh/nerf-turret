# Nerf-Turret
Raspberry Pi based vision-guided Nerf turret developed as a course project.

## Overview

This project implements a physical, vision-based Nerf turret prototype designed for area monitoring and non-lethal response. The system uses a camera to continuously observe its surroundings, detects the presence of a person, and autonomously controls a motorized Nerf blaster to track detected targets along a horizontal axis. 

The project was developed as part of a software engineering course and serves as a prototype demonstrating the integration of computer vision, embedded control, and mechanical actuation into a single system, with an emphasis on safety, clear operational modes, and reproducible behavior on equivalent hardware.

## Key Features

- **Real-time person detection** using computer vision algorithms
- **Autonomous horizontal tracking** with servo-controlled pan mechanism
- **Relay-based Nerf blaster actuation** for controlled, non-lethal response
- **Multiple operational modes** (monitoring, active response)
- **Optional live camera feed** for remote observation
- **Remote notifications** via Telegram integration
- **Safety-first design** with software-level constraints and user controls

## System Capabilities

The system continuously captures video frames from the mounted camera and analyzes them using a human-detection algorithm. When a person is detected with sufficient confidence, the system estimates the horizontal position of the target within the frame and rotates the turret to keep the target centered using a pan servo. 

Depending on the selected system mode, the turret can remain in a safe monitoring state or execute a controlled response by activating the Nerf blaster through relay-based actuation. The system follows a continuous control loop that transitions between detection, tracking, and response behavior based on runtime conditions. Optional features, including a live camera feed and remote notifications, are implemented so they do not interfere with the core detection and control loop.

## Hardware Requirements

This is a **physical** prototype and cannot be meaningfully executed without the required hardware. Reproducing the system requires assembling the components on a Raspberry Pi setup with appropriate mechanical mounting and power delivery.

### Core Components

- **Raspberry Pi** (tested on Pi 4, Pi 3B+ should work)
- **Camera module** for real-time video input (Pi Camera or USB webcam)
- **Servo motor** providing horizontal pan control
- **Nerf blaster** (modified for electronic control)
- **Relay modules** (2-channel) for flywheel and feeder control
- **Custom 3D printed parts** for mounting and mechanical adaptations
- **Power supply** (separate for servos/relays recommended)

The system is designed to operate safely with non-lethal projectiles only and includes mechanisms for user control, safe mode operation, and immediate shutdown capabilities. Additional details about hardware wiring, mechanical adaptations, GPIO pin assignments, and physical assembly are documented in the `docs/` directory.

## Reproducing the Demo (Step-by-Step)

This project is a physical prototype and requires the appropriate hardware setup to reproduce its behavior. The instructions below describe how to reproduce the demonstrated functionality on a Raspberry Pi-based system with equivalent components.

### Prerequisites

Before starting, ensure you have:
- A fully assembled system with mounted camera, servo mechanism, and relay-controlled Nerf blaster
- The device placed on a stable surface with a clear and unobstructed field of view
- Indoor lighting conditions sufficient for person detection
- A Raspberry Pi running a Linux-based operating system (Raspberry Pi OS recommended)
- Python 3.7 or higher installed

### Installation

1. Clone the repository onto the Raspberry Pi:
   ```bash
   git clone https://github.com/sshhhhhhhhhhhhhhh/nerf-turret.git
   cd nerf-turret
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Enable the camera interface in the Raspberry Pi system configuration:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options → Camera → Enable
   ```

4. Verify hardware connections match the GPIO pin assignments described in `docs/hardware.md`

### Running the System

1. Navigate to the source directory:
   ```bash
   cd src
   ```

2. Launch the main control script:
   ```bash
   python main.py
   ```

3. Observe system initialization messages indicating successful camera and hardware setup

4. Place a person within the camera's field of view to test detection and tracking

### Expected Behavior

When running correctly, the system initializes in a monitoring state and begins capturing video frames. Upon detecting a person, the turret rotates horizontally to track the target and center them in the frame. If active response mode is enabled, the system triggers the Nerf blaster in a controlled manner after maintaining target lock. System state changes and detection events are logged to the console during operation.

## System Architecture

The turret runs as a continuous control loop on the Raspberry Pi. Each iteration captures a camera frame, runs person detection, selects a target (if present), and updates the pan servo to reduce horizontal offset from the frame center. Based on user configuration (e.g., active response enabled/disabled) and current detection status, the system may trigger relay-based actuation for the blaster. Optional subsystems such as live preview and Telegram logging are implemented so they do not block or destabilize the main loop.

More details, including system diagrams and state machine documentation, are available in `docs/architecture.md`.

## Project Structure

```
nerf-turret/
├── assets/          # Photos, diagrams, and media files
├── docs/            # Detailed documentation (hardware, architecture, safety)
├── scripts/         # Utility scripts for testing and calibration
├── src/             # Main source code
└── README.md        # This file
```

## Safety Notes

- This system uses **non-lethal foam projectiles only**
- Always operate in a controlled environment with appropriate safety measures
- The system includes software-level safety constraints to prevent unintended activation
- Emergency stop functionality is available through keyboard interrupt (Ctrl+C)
- Review `docs/safety.md` before operating the system

## Media

Visual materials, including project photos, mechanical modifications, and system diagrams, are indexed in [`assets/media.md`](assets/media.md).

## References

- Raspberry Pi Foundation. Raspberry Pi Documentation.  
  https://www.raspberrypi.com/documentation/

- OpenCV. OpenCV Documentation.  
  https://docs.opencv.org/

- Telegram Bot API Documentation.  
  https://core.telegram.org/bots/api

- TensorFlow Lite Models.  
  https://www.tensorflow.org/lite/models

- Tolga Özuygur. *Automated Nerf Turret*.  
  https://www.youtube.com/watch?v=0b1APorlbUA

> **Note:** This project was inspired by earlier automated Nerf turret work, particularly the project demonstrated by Tolga Özuygur. This implementation was developed independently as part of a course project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
