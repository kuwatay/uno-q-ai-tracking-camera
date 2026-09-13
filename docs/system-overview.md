# System Overview

## UNO Q AI Tracking Camera

This document describes the system architecture of the **UNO Q AI Tracking Camera** project.

The system uses an Arduino UNO Q, a USB camera, and a two-axis pan/tilt mechanism driven by RC servos. Face detection runs locally on the UNO Q. The detected face position is converted into pan/tilt correction values, which are sent to the MCU side of the UNO Q through Arduino RouterBridge.

A browser-based Web UI provides live video, tracking overlays, status information, and simple controls.

---

## 1. System Architecture

```text
                         +----------------------+
                         |      Web Browser     |
                         |                      |
                         | Live Video           |
                         | Tracking Overlay     |
                         | Tracking ON/OFF      |
                         | Center Control       |
                         +----------+-----------+
                                    ^
                                    |
                              HTTP / WebUI
                                    |
                                    v
+-------------+            +----------------------+
| USB Camera  |----------->|   Arduino UNO Q      |
|             |  USB/UVC   |     Linux side      |
+-------------+            |                      |
                           |  Camera / V4L2       |
                           |        |             |
                           |        v             |
                           |  Face Detection      |
                           |        |             |
                           |        v             |
                           |  Tracking Logic      |
                           |        |             |
                           |        +----------+  |
                           |                   |  |
                           |                 WebUI|
                           |                   |  |
                           |        RouterBridge  |
                           +-------------+--------+
                                         |
                                         v
                           +----------------------+
                           |   UNO Q MCU side     |
                           |                      |
                           | Arduino_HardwareServo|
                           +----------+-----------+
                                      |
                         +------------+------------+
                         |                         |
                         v                         v
                   +-----------+             +-----------+
                   | PAN Servo |             |TILT Servo |
                   |    D9     |             |   D10     |
                   +-----+-----+             +-----+-----+
                         |                         |
                         +-----------+-------------+
                                     |
                                     v
                           +----------------------+
                           | Pan/Tilt Mechanism   |
                           |      USB Camera      |
                           +----------------------+
```

---

## 2. Main Components

### Arduino UNO Q

The UNO Q performs two different roles.

**Linux side**

- USB camera capture
- Face detection
- Face position calculation
- Tracking control logic
- Web UI
- Communication with the MCU through RouterBridge

**MCU side**

- Receives requested servo positions
- Generates servo control pulses
- Drives the PAN and TILT servos

This separation allows the Linux environment to handle AI and application logic while the MCU handles real-time hardware control.

---

## 3. Camera Input

The prototype uses a USB 2.0 camera connected through a powered USB-C hub.

Current capture device:

```text
/dev/video2
```

Current video settings:

```text
Resolution : 640 x 480
Frame rate : 15 fps
Format     : YUYV
```

The camera is accessed by the UNO Q Linux environment using V4L2.

---

## 4. Face Detection

Face detection is performed using the Arduino App Lab **Video Object Detection** component.

For each detected face, the application obtains a bounding box:

```text
(x0, y0) ------------+
   |                  |
   |       FACE       |
   |         +        |
   |      center      |
   |                  |
   +------------ (x1, y1)
```

The face center is calculated as:

```text
face_x = (x0 + x1) / 2
face_y = (y0 + y1) / 2
```

For a 640 x 480 image, the image center is:

```text
center_x = 320
center_y = 240
```

The tracking error is:

```text
error_x = face_x - center_x
error_y = face_y - center_y
```

---

## 5. Tracking Control

A dead zone is used around the image center to prevent unnecessary servo movement caused by small variations in face detection.

Current settings:

```text
Dead zone X : +/-40 pixels
Dead zone Y : +/-30 pixels
```

Conceptually:

```text
+--------------------------------------+
|                                      |
|                 FACE                 |
|                  o                   |
|                  |                   |
|                  |                   |
|          +-------+-------+           |
|          |   dead zone   |           |
|          |       +       |           |
|          +---------------+           |
|                                      |
+--------------------------------------+
```

If the face remains inside the dead zone, no servo correction is made.

If the face moves outside the dead zone, a correction is calculated. Larger errors result in larger servo movements, up to a configured maximum step.

---

## 6. Servo Control

The prototype uses two GWS S03N/2BBMG RC servos.

Pin assignment:

```text
PAN  : D9
TILT : D10
```

Tracking range:

```text
PAN  : 1250 - 1750 us
TILT : 1250 - 1750 us
```

Center position:

```text
PAN  : 1500 us
TILT : 1500 us
```

The physical mechanism was tested over approximately:

```text
1200 - 1800 us
```

but the narrower range is used during automatic tracking for safety.

For the current servo installation:

```python
PAN_DIR = -1
TILT_DIR = -1
```

Both directions may need to be changed when using a different pan/tilt mechanism.

---

## 7. Linux-to-MCU Communication

Servo positions are sent from the Python application on the Linux side to the MCU using **Arduino RouterBridge**.

Python side:

```python
Bridge.notify(
    "set_servos",
    int(pan_us),
    int(tilt_us)
)
```

MCU side:

```cpp
Bridge.provide(
    "set_servos",
    set_servos
);
```

The MCU then applies the requested pulse widths using `Arduino_HardwareServo`.

This architecture keeps AI processing and servo timing separated.

---

## 8. Web Interface

The Web UI runs on the UNO Q and is accessed from another computer over the network.

Example:

```text
http://<UNO-Q-IP>:7000
```

The interface provides:

- Live camera video
- Face bounding box
- Face center
- Image center
- Dead-zone rectangle
- Tracking vector
- X/Y tracking error
- Detection confidence
- PAN servo pulse width
- TILT servo pulse width
- Tracking ON/OFF button
- Center button

The browser periodically retrieves tracking state from the UNO Q.

Current API endpoints:

```text
GET  /tracking
POST /tracking/toggle
POST /center
```

---

## 9. Tracking ON/OFF

When tracking is ON:

```text
Face Detection
      |
      v
Tracking Error
      |
      v
Servo Correction
      |
      v
Camera Movement
```

When tracking is OFF:

```text
Face Detection       continues
Live Video           continues
Tracking Overlay     continues
Servo Movement       stopped
```

This allows the camera position or mechanism to be adjusted safely without stopping the entire application.

---

## 10. Center Function

The Center button sends both servos to their neutral positions:

```text
PAN  = 1500 us
TILT = 1500 us
```

If tracking remains ON, the camera resumes tracking immediately after centering.

To leave the camera centered:

```text
Tracking OFF
      |
      v
Center
```

---

## 11. Power Configuration

The RC servos use an external 5 V power supply.

```text
External 5 V  ----+---- PAN Servo V+
                  |
                  +---- TILT Servo V+

External GND  ----+---- PAN Servo GND
                  |
                  +---- TILT Servo GND
                  |
                  +---- UNO Q GND

UNO Q D9  -------------- PAN Servo Signal
UNO Q D10 -------------- TILT Servo Signal
```

The UNO Q and servo supply must share a common ground.

A powered USB-C hub is used for the USB camera.

---

## 12. Software Structure

The main application is organized as follows:

```text
app/
└── ai-tracking-camera-with-servo/
    ├── app.yaml
    ├── python/
    │   └── main.py
    ├── sketch/
    │   ├── sketch.ino
    │   └── sketch.yaml
    └── assets/
        └── index.html
```

Responsibilities:

```text
python/main.py
    Face detection
    Tracking calculation
    Web API
    Servo command generation

sketch/sketch.ino
    RouterBridge endpoint
    Servo pulse generation

sketch/sketch.yaml
    MCU-side library dependencies

assets/index.html
    Live video
    Tracking overlay
    Web controls
```

---

## 13. Data Flow

The complete tracking loop is:

```text
1. USB camera captures a frame
          |
          v
2. Face detector finds a face
          |
          v
3. Face center is calculated
          |
          v
4. Error from image center is calculated
          |
          v
5. Dead-zone check
          |
          +---- inside ----> Hold position
          |
          +---- outside ---> Calculate servo step
                                  |
                                  v
6. Update PAN/TILT pulse widths
          |
          v
7. Send values through RouterBridge
          |
          v
8. MCU updates RC servos
          |
          v
9. Camera physically moves
          |
          v
10. Next frame repeats the loop
```

This forms a closed-loop visual tracking system.

---

## 14. Current System Status

The following functions have been tested successfully:

```text
[OK] USB camera capture
[OK] Face detection
[OK] Face-center calculation
[OK] PAN servo operation
[OK] TILT servo operation
[OK] Automatic face tracking
[OK] Web live view
[OK] Tracking overlay
[OK] Tracking ON/OFF
[OK] Center control
```

The next planned development step is to make the video output usable by applications such as Microsoft Teams and Zoom.

A possible future architecture is:

```text
UNO Q
   |
   | Network Video
   v
PC / Mac
   |
   +-- OBS / GStreamer
   |
   +-- Virtual Camera
   |
   +-- Teams / Zoom
```

---

## 15. Design Goals

The project is intended to remain:

- simple,
- understandable,
- locally processed,
- easy to reproduce,
- suitable for reusing existing camera and servo hardware,
- extensible for future video-conferencing use.

One goal of the project is to demonstrate how an older camera and pan/tilt mechanism can be upgraded with modern on-device AI using Arduino UNO Q.
