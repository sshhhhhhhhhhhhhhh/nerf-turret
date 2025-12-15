import requests
from datetime import datetime
import time
import cv2
import sys, site
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import RPi.GPIO as GPIO

site.addsitedir("/usr/lib/python3/dist-packages")
from picamera2 import Picamera2
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory

# --------- config ----------
FLIP_180 = 1
CAM_RES = (640, 480)
CONFIDENCE_THRESHOLD = 0.5
STREAM_PORT = 8080

# Servo config
SERVO_PIN = 12

# Shooting config
FLYWHEEL_PIN = 17   # GPIO 17 - STAYS ON during entire tracking mode
FEEDER_PIN = 27     # GPIO 27 - ON only when locked on target
RELAY_ACTIVE_LOW = True

# Scanning config
SCAN_LEFT = -0.2
SCAN_RIGHT = 0.8
SCAN_STEP = 0.015

# Tracking config
FIRE_ZONE = 12  # Pixels - how close to center before we start feeding

# Smart speed adjustment
MIN_SPEED = 0.02
MAX_SPEED = 0.20
SPEED_SCALE = 300

# Smoothing
TARGET_SMOOTHING = 0.4

# Timeouts
LOST_TARGET_TIMEOUT = 5.0  # After 3 seconds of no target, turn off motors and scan

# --------- Telegram config ----------
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "bot_token" # bot's token
TELEGRAM_CHAT_ID = chat_id # chat id of either your account or the group
# ---------------------------


current_frame = None
frame_lock = threading.Lock()

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><img src="/stream" style="width:100%;max-width:800px;"></body></html>')
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            while True:
                with frame_lock:
                    if current_frame is None:
                        continue
                    _, jpeg = cv2.imencode('.jpg', current_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                try:
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
                except:
                    break
                time.sleep(0.03)

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def gpio_levels(active_low):
    return (GPIO.LOW, GPIO.HIGH) if active_low else (GPIO.HIGH, GPIO.LOW)

def telegram_log(event, mode, image=None):
    if not TELEGRAM_ENABLED:
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caption = (
            f"[{timestamp}]\n"
            f"Event: {event}\n"
            f"Mode: {mode}"
        )

        if image is None:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": caption
                },
                timeout=5
            )
        else:
            _, jpeg = cv2.imencode(".jpg", image)
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": caption
                },
                files={"photo": jpeg.tobytes()},
                timeout=10
            )
    except:
        pass


def main():
    global current_frame

    # Setup GPIO for shooting
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    on_level, off_level = gpio_levels(RELAY_ACTIVE_LOW)
    GPIO.setup(FLYWHEEL_PIN, GPIO.OUT, initial=off_level)
    GPIO.setup(FEEDER_PIN, GPIO.OUT, initial=off_level)

    # Setup servo
    factory = PiGPIOFactory()
    servo = Servo(SERVO_PIN, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)
    
    servo_pos = SCAN_LEFT
    servo.value = servo_pos
    scan_direction = 1
    
    # Setup mode
    mode = "SCANNING"  # SCANNING or TRACKING
    
    smooth_cx = None
    last_target_seen_time = time.time()
    
    print(f"Servo on GPIO {SERVO_PIN}")
    print(f"Flywheel on GPIO {FLYWHEEL_PIN}, Feeder on GPIO {FEEDER_PIN}")

    # Set model & Cam
    net = cv2.dnn.readNetFromCaffe(
        "MobileNetSSD_deploy.prototxt",
        "MobileNetSSD_deploy.caffemodel"
    )

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": CAM_RES, "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(0.5)

    # Set HTTPServer
    server = ThreadedHTTPServer(('0.0.0.0', STREAM_PORT), StreamHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()

    print(f"Stream: http://{ip}:{STREAM_PORT}")
    print("TURRET READY. Ctrl+C to stop")

    frame_count = 0
    fps_time = time.time()
    frame_center_x = CAM_RES[0] // 2

    # Set telegram
    prev_mode = None
    prev_feeder_state = None

    telegram_log("System started", mode)

    try:
        while True:
            raw = picam2.capture_array()

            if FLIP_180:
                raw = cv2.rotate(raw, cv2.ROTATE_180)

            frame = raw.copy()
            h, w = frame.shape[:2]
            frame_bgr = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)

            blob = cv2.dnn.blobFromImage(frame_bgr, 0.007843, (300, 300), 127.5)
            net.setInput(blob)
            detections = net.forward()

            best_detection = None
            best_conf = 0

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                class_id = int(detections[0, 0, i, 1])

                if class_id == 15 and confidence > CONFIDENCE_THRESHOLD:
                    box = detections[0, 0, i, 3:7] * [w, h, w, h]
                    x1, y1, x2, y2 = box.astype(int)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    if confidence > best_conf:
                        best_conf = confidence
                        best_detection = (x1, y1, x2, y2)

            # Draw crosshair
            cv2.line(frame, (frame_center_x, 0), (frame_center_x, h), (0, 0, 255), 2)
            cv2.circle(frame, (frame_center_x, h//2), FIRE_ZONE, (0, 0, 255), 2)

            current_time = time.time()

            # === TARGET DETECTION ===
            if best_detection is not None:
                # WE SEE A TARGET!
                last_target_seen_time = current_time
                
                # Switch to TRACKING mode if we were scanning
                if mode == "SCANNING":
                    mode = "TRACKING"
                    print("TARGET ACQUIRED - FLYWHEEL ON")
                    GPIO.output(FLYWHEEL_PIN, on_level)  # TURN ON FLYWHEEL
                    
                    x1, y1, x2, y2 = best_detection
                    person_img = frame[y1:y2, x1:x2]
                    telegram_log("Target acquired", mode, person_img)

                x1, y1, x2, y2 = best_detection
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                #person_img = frame[y1:y2, x1:x2]
                #telegram_log("Target acquired", mode, person_img)

                # Smooth the target position
                if smooth_cx is None:
                    smooth_cx = cx
                else:
                    smooth_cx = smooth_cx + TARGET_SMOOTHING * (cx - smooth_cx)

                error_x = smooth_cx - frame_center_x

                # Draw target center
                cv2.circle(frame, (int(smooth_cx), cy), 8, (255, 0, 0), -1)

                # === INTELLIGENT SPEED CONTROL ===
                distance = abs(error_x)
                speed_factor = min(distance / SPEED_SCALE, 1.0)
                adaptive_speed = MIN_SPEED + (MAX_SPEED - MIN_SPEED) * speed_factor
                
                # Move servo towards target
                adjustment = (error_x / frame_center_x) * adaptive_speed
                servo_pos -= adjustment
                servo_pos = max(-1.0, min(1.0, servo_pos))
                servo.value = servo_pos
                
                # === CONTINUOUS FIRING LOGIC ===
                if abs(error_x) <= FIRE_ZONE:
                    # AIM IS ON TARGET - FEED DARTS!
                    GPIO.output(FEEDER_PIN, on_level)
                    cv2.putText(frame, " FIRING! ", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                else:
                    # AIM IS OFF TARGET - STOP FEEDING (but flywheel stays on)
                    GPIO.output(FEEDER_PIN, off_level)
                    cv2.putText(frame, f"TRACKING... error: {int(error_x)}px", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                current_feeder_state = GPIO.input(FEEDER_PIN)
                if current_feeder_state != prev_feeder_state:
                    if current_feeder_state == on_level:
                        telegram_log("Firing started", mode, person_img)
                    else:
                        telegram_log("Firing stopped", mode)
                    prev_feeder_state = current_feeder_state

            else:
                # NO TARGET DETECTED
                smooth_cx = None
                time_since_target = current_time - last_target_seen_time
                
                # If we're in tracking mode but lost target
                if mode == "TRACKING":
                    if time_since_target > LOST_TARGET_TIMEOUT:
                        # TIMEOUT! Turn everything OFF and go back to scanning
                        print("❌ TARGET LOST - MOTORS OFF - RESUMING SCAN")
                        GPIO.output(FLYWHEEL_PIN, off_level)  # TURN OFF FLYWHEEL
                        GPIO.output(FEEDER_PIN, off_level)    # TURN OFF FEEDER
                        mode = "SCANNING"
                        telegram_log("Target lost", mode)
                    else:
                        # Just lost target, keep flywheel on, stop feeding
                        GPIO.output(FEEDER_PIN, off_level)
                        cv2.putText(frame, f"TARGET LOST ({time_since_target:.1f}s)", (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
                
                # SCANNING MODE
                if mode == "SCANNING":
                    servo_pos += scan_direction * SCAN_STEP
                    
                    if servo_pos >= SCAN_RIGHT:
                        servo_pos = SCAN_RIGHT
                        scan_direction = -1
                    elif servo_pos <= SCAN_LEFT:
                        servo_pos = SCAN_LEFT
                        scan_direction = 1
                    
                    servo.value = servo_pos
                    cv2.putText(frame, "SCANNING...", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            with frame_lock:
                current_frame = frame.copy()

            frame_count += 1
            if current_time - fps_time >= 2.0:
                fps = frame_count / (current_time - fps_time)
                flywheel_state = "ON" if GPIO.input(FLYWHEEL_PIN) == on_level else "OFF"
                feeder_state = "ON" if GPIO.input(FEEDER_PIN) == on_level else "OFF"
                print(f"[{mode}] FPS: {fps:.2f} | Fly: {flywheel_state} | Feed: {feeder_state}")
                fps_time = current_time
                frame_count = 0

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        print(" EMERGENCY STOP - ALL RELAYS OFF")
        GPIO.output(FLYWHEEL_PIN, off_level)
        GPIO.output(FEEDER_PIN, off_level)
        GPIO.cleanup()
        servo.value = None
        picam2.stop()
        server.shutdown()
        telegram_log("System shutdown", mode)

if __name__ == "__main__":
    main()
