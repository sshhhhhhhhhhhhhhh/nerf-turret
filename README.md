# Nerf Turret
Raspberry Pi based vision-guided Nerf turret developed as a course project.

## Overview

This project implements a physical, vision-based Nerf turret prototype designed for area monitoring and non-lethal response. The system uses a camera to continuously observe its surroundings, detects the presence of a person, and autonomously controls a motorized Nerf blaster to track detected targets along a horizontal axis. The project was developed as part of a software engineering course and serves as a prototype. Its purpose is to demonstrate the integration of computer vision, embedded control, and mechanical actuation into a single system, with an emphasis on safety, clear operational modes, and reproducible behavior on equivalent hardware. 

## System Capabilities

The system continuously captures video frames from the mounted camera and analyzes them using a human-detection algorithm. When a person is detected with sufficient confidence, the system estimates the horizontal position of the target within the frame and rotates the turret to keep the target centered using a pan servo. Depending on the selected system mode, the turret can remain in a safe monitoring state or execute a controlled, non-lethal response by activating the Nerf blaster through relay-based actuation. The system is structured around clearly defined operational states such as idle monitoring, target detection, tracking, and response execution. Optional features, including a live camera feed and remote notifications, are designed so that they do not interfere with the core detection and control loop.


