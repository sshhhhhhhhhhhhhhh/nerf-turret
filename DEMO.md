# Demo Documentation

## Demo Overview

This document describes the system demonstration and expected behavior of the Nerf turret prototype.

## What the Demo Shows

The demonstration showcases a complete autonomous surveillance and response system that:
1. Continuously monitors an area using computer vision
2. Detects when a person enters the monitored zone
3. Tracks the person by rotating horizontally
4. Executes a controlled non-lethal response (firing Nerf darts)
5. Returns to scanning mode when the person leaves

## System Behavior (Step-by-Step)

### Phase 1: System Initialization
**What happens:**
- System boots and initializes camera
- Servo motor moves to starting position
- HTTP stream server starts on port 8080
- Console displays system status and local IP address
- Telegram notification sent: "System started"

**What you see:**
```
Servo on GPIO 12
Flywheel on GPIO 17, Feeder on GPIO 27
Stream: http://192.168.1.X:8080
TURRET READY. Ctrl+C to stop
```

**Expected time:** ~3-5 seconds

---

### Phase 2: Scanning Mode
**What happens:**
- Turret slowly pans left and right in a sweeping pattern
- Camera continuously analyzes frames for people
- No motors running (flywheel OFF, feeder OFF)
- System is in "SCANNING" mode

**What you see:**
- Servo moving smoothly back and forth
- Console output: `[SCANNING] FPS: 8.50 | Fly: OFF | Feed: OFF`
- Live stream (if accessed) shows "SCANNING..." overlay
- Red vertical line at center of frame (aiming reference)

**Expected behavior:** Continuous scanning until a person is detected

---

### Phase 3: Target Acquisition
**What happens:**
- Person enters camera field of view
- Detection algorithm identifies person with >50% confidence
- Green bounding box appears around detected person
- **Mode switches from SCANNING → TRACKING**
- **Flywheel motors spin up immediately** (stays ON for entire tracking phase)
- Telegram notification sent with photo: "Target acquired"

**What you see:**
- Console output: `TARGET ACQUIRED - FLYWHEEL ON`
- Green rectangle around person on live stream
- Blue circle marking center of detected person
- Console shows: `[TRACKING] FPS: 8.50 | Fly: ON | Feed: OFF`
- Servo begins adjusting to follow person

**Expected time:** <1 second from person appearing to flywheel activation

---

### Phase 4: Tracking and Firing
**What happens:**
- Servo continuously adjusts to keep person centered
- System calculates horizontal error (distance from center)
- Movement speed adapts: faster when far from center, slower when close
- **When person is within 12 pixels of center (fire zone):**
  - Feeder motor activates
  - Darts are pushed into spinning flywheels
  - Continuous firing as long as aim is maintained
- **When person moves outside fire zone:**
  - Feeder stops (but flywheel keeps spinning)
  - System continues tracking

**What you see:**
- Person followed smoothly by camera
- When locked on target:
  - Console shows: `[TRACKING] FPS: 8.50 | Fly: ON | Feed: ON`
  - Live stream overlay: `FIRING!`
  - Telegram notification: "Firing started" (with photo)
  - Nerf darts being fired
- When tracking but not firing:
  - Console shows: `[TRACKING] FPS: 8.50 | Fly: ON | Feed: OFF`
  - Live stream overlay: `TRACKING... error: 45px` (shows distance from center)

**Expected behavior:** Darts fire in bursts as person is tracked and reacquired

---

### Phase 5: Target Loss and Timeout
**What happens:**
- Person leaves camera view or hides
- System continues tracking mode with flywheel ON
- **After 5 seconds with no detection:**
  - Flywheel motors turn OFF
  - Feeder turns OFF (if it was ON)
  - System returns to SCANNING mode
  - Telegram notification: "Target lost"

**What you see:**
- Immediately after loss:
  - Live stream overlay: `TARGET LOST (0.5s)`
  - Counter increments: `TARGET LOST (2.3s)`, `TARGET LOST (4.8s)`
  - Console shows: `[TRACKING] FPS: 8.50 | Fly: ON | Feed: OFF`
- After 5-second timeout:
  - Console: `TARGET LOST - MOTORS OFF - RESUMING SCAN`
  - Console shows: `[SCANNING] FPS: 8.50 | Fly: OFF | Feed: OFF`
  - Servo resumes scanning pattern

**Expected time:** 5 seconds from last detection to return to scanning

---

### Phase 6: System Shutdown
**What happens:**
- User presses Ctrl+C
- Emergency stop engages
- All relays turn OFF immediately
- Servo disengages
- Camera stops
- HTTP server shuts down
- Telegram notification: "System shutdown"

**What you see:**
```
^C
Stopped.
EMERGENCY STOP - ALL RELAYS OFF
```

**Expected time:** Immediate (<100ms)

---

## Live Stream Features

Access the live camera feed at `http://<raspberry-pi-ip>:8080`

**What you see on the stream:**
- Real-time camera view (640x480 resolution)
- Green bounding boxes around detected people
- Blue circle marking center of tracked target
- Red vertical crosshair at frame center
- Red circle showing fire zone radius (12 pixels)
- Status text overlay showing current mode
- Detection confidence and tracking error

**Update rate:** ~30 FPS stream, ~8 FPS detection

---

## Telegram Notifications

If enabled, the system sends notifications to configured Telegram chat:

**Notification Types:**
1. **System started** - When turret initializes
2. **Target acquired** - When person first detected (includes photo)
3. **Firing started** - When feeder activates (includes photo)
4. **Firing stopped** - When feeder deactivates
5. **Target lost** - When returning to scan after timeout
6. **System shutdown** - When Ctrl+C pressed

**Format:**
```
[2024-12-15 06:45:23]
Event: Target acquired
Mode: TRACKING
```

---

## Expected Performance Metrics

| Metric | Value |
|--------|-------|
| Detection FPS | 3-10 FPS |
| Detection Latency | <1 second |
| Tracking Response Time | <200ms |
| Fire Zone Accuracy | ±12 pixels from center |
| Scan Speed | Full sweep in ~15 seconds |
| Target Loss Timeout | 5 seconds |

---

## Demo Scenarios

### Scenario 1: Single Person Detection
1. System starts in SCANNING mode
2. Person walks into view from left
3. Turret locks on and tracks smoothly
4. Fires when centered
5. Person exits right
6. After 5 seconds, turret resumes scanning

**Duration:** ~30-60 seconds

---

### Scenario 2: Multiple People (Priority Selection)
1. System scanning
2. Two people enter view
3. System selects target with highest confidence
4. Tracks and fires at primary target
5. If primary target leaves, may switch to secondary target

**Note:** System tracks one target at a time (highest confidence detection)

---

### Scenario 3: Quick Movement
1. System tracking person
2. Person moves quickly across frame
3. Turret follows with adaptive speed (faster when error is large)
4. Firing occurs intermittently when aim is good
5. Demonstrates tracking capability

**Duration:** ~15-30 seconds

---

## Known Limitations

- **Single axis tracking:** Only horizontal (pan), no vertical (tilt)
- **Detection range:** ~2-10 meters depending on lighting
- **One target at a time:** Cannot track multiple people simultaneously
- **Lighting dependent:** Poor performance in very dark or very bright conditions
- **Frame rate:** 3-10 FPS (limited by Raspberry Pi processing power)
- **Accuracy:** ±12 pixels (approximately 10-15cm at 3 meters)

---

## Safety During Demo

⚠️ **Demonstration Safety Rules:**
- Clear area of fragile objects
- Participants wear safety glasses
- Maintain 2+ meter minimum distance
- Emergency stop (Ctrl+C) operator present
- Never point at faces/eyes
- Controlled indoor environment only

---

## Troubleshooting During Demo

| Issue | Quick Fix |
|-------|-----------|
| No detection | Improve lighting, person too far |
| Jittery tracking | Normal with fast movement |
| Not firing | Person not centered in fire zone |
| Stream not loading | Check IP address, refresh browser |
| Servo not moving | Check power supply, restart pigpiod |
