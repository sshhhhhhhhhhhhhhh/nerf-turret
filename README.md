# Nerf Turret
Raspberry Pi based vision-guided Nerf turret developed as a course project.

## Overview

This project implements a physical, vision-based Nerf turret prototype designed for area monitoring and non-lethal response. The system uses a camera to continuously observe its surroundings, detects the presence of a person, and autonomously controls a motorized Nerf blaster to track detected targets along a horizontal axis. The project was developed as part of a software engineering course and serves as a prototype. Its purpose is to demonstrate the integration of computer vision, embedded control, and mechanical actuation into a single system, with an emphasis on safety, clear operational modes, and reproducible behavior on equivalent hardware. 

## System Capabilities

The system continuously captures video frames from the mounted camera and analyzes them using a human-detection algorithm. When a person is detected with sufficient confidence, the system estimates the horizontal position of the target within the frame and rotates the turret to keep the target centered using a pan servo. Depending on the selected system mode, the turret can remain in a safe monitoring state or execute a controlled, non-lethal response by activating the Nerf blaster through relay-based actuation. The system is structured around clearly defined operational states such as idle monitoring, target detection, tracking, and response execution. Optional features, including a live camera feed and remote notifications, are designed so that they do not interfere with the core detection and control loop.


## Hardware Requirements

This is a **physical** prototype and cannot be meaningfully executed without the required hardware. Reproducing the system requires assembling the components on a Raspberry Pi setup with appropriate mechanical mounting and power delivery.

At a high level, the system consists of a Raspberry Pi, a camera module for real-time video input, a servo motor providing horizontal pan control, and a Nerf blaster whose flywheel and feeder mechanisms are controlled via relay modules. Custom 3D designed & printed mechanical modifications and mounting components are used to securely attach the blaster and actuators to a stable platform. The system is designed to operate safely with non-lethal projectiles only and includes mechanisms for user control, safe mode operation, and immediate shutdown.

Additional details about hardware wiring, mechanical adaptations, and physical assembly are documented in the `docs/` directory.

## Reproducing the Demo (Step-by-Step)

This project is a physical prototype and requires the **appropriate** hardware setup to reproduce its behavior. The instructions below describe how to reproduce the demonstrated functionality on a **Raspberry Pi based** system with equivalent components.

### Assumptions

The system is fully assembled with the required hardware, including a mounted camera, a horizontally actuated servo mechanism, and a Nerf blaster whose flywheel and feeder are controlled via relay modules. The device is placed on a stable surface with a clear and unobstructed field of view. Indoor lighting conditions sufficient for person detection are assumed.

### Software Environment

The system is intended to run on a Raspberry Pi with a Linux-based operating system. Python is used as the primary programming language. Required third-party libraries include computer vision and hardware control libraries appropriate for camera access, servo control, and relay actuation.

### Installation

1. Clone the repository onto the Raspberry Pi.
2. Install the required Python dependencies listed in `requirements.txt`.
3. Ensure that the camera interface is enabled in the Raspberry Pi system configuration.
4. Verify that the servo and relay hardware are connected to the correct GPIO pins as described in the hardware documentation.

### Running the System

1. Navigate to the project source directory.
2. Launch the main control script.
3. Observe system initialization messages indicating successful camera and hardware setup.
4. Place a person within the camera’s field of view. 

### Expected Behavior

When running correctly, the system initializes in a monitoring state and begins capturing video frames. Upon detecting a person, the turret rotates horizontally to track the target. If active response mode is enabled, the system triggers the Nerf blaster in a controlled, non-lethal manner. System state changes and detection events are logged during operation.
