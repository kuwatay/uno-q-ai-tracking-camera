# UNO Q AI Tracking Camera

A face-tracking pan/tilt camera built with **Arduino UNO Q**.

This project combines on-device face detection, a USB camera, and two RC servos to automatically keep a person near the center of the frame. A browser-based Web UI provides a live preview, tracking information, and basic controls.

The current version is a working prototype. Support for using the camera directly with applications such as Microsoft Teams or Zoom is planned as a future extension.

---

## Features

- USB camera input on Arduino UNO Q
- On-device face detection
- Automatic two-axis pan/tilt tracking
- Adjustable dead zone around the image center
- Servo movement limits for safer operation
- Browser-based live video monitor
- Face bounding box and tracking overlay
- Display of face position, tracking error, confidence, and servo pulse width
- Tracking ON/OFF control
- Center button for returning the camera to its neutral position
- Local processing on the UNO Q

---

## Current Status

- [x] USB camera capture
- [x] Face detection
- [x] PAN servo control
- [x] TILT servo control
- [x] Automatic face tracking
- [x] Browser-based live monitor
- [x] Tracking ON/OFF control
- [x] Center control
- [ ] Microsoft Teams / Zoom virtual camera support

---

## Hardware

The prototype currently uses:

- **Arduino UNO Q 2GB**
- USB 2.0 camera
  - USB VID/PID: `056e:7001`
  - Linux device: `/dev/video2`
- 2-axis pan/tilt mechanism
- Two **GWS S03N/2BBMG** RC servos
- External 5 V supply for the servos
- Powered USB-C hub for the camera

The project was intentionally developed using an older USB camera and an existing servo pan/tilt mechanism as a practical hardware retrofit experiment.

---

## Servo Connections

| Function | UNO Q Pin |
|---|---|
| PAN servo signal | D9 |
| TILT servo signal | D10 |

The servos are powered from an **external 5 V supply**.

The external servo power supply ground and the UNO Q ground must be connected together.

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

> Do not power the servos directly from the UNO Q when the servo current may exceed the board's available output current.

---

## Camera Configuration

The USB camera is available as:

```text
/dev/video2
```

The current application uses:

```text
Resolution : 640 x 480
Frame rate : 15 fps
Format     : YUYV
```

Useful checks:

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video2 --list-formats-ext
```

A simple capture test can be performed with:

```bash
ffmpeg \
  -f v4l2 \
  -input_format yuyv422 \
  -video_size 640x480 \
  -framerate 15 \
  -i /dev/video2 \
  -frames:v 1 \
  test.jpg
```

---

## Software Architecture

The application is split between the Linux side of the UNO Q and the MCU side.

```text
USB Camera
    |
    v
UNO Q Linux
    |
    +-- Video Object Detection
    |      |
    |      +-- Face bounding box
    |      +-- Face center
    |      +-- Tracking error
    |
    +-- Web UI
    |      |
    |      +-- Live camera image
    |      +-- Overlay
    |      +-- Tracking ON/OFF
    |      +-- Center
    |
    +-- RouterBridge
           |
           v
        MCU side
           |
           +-- D9  -> PAN servo
           +-- D10 -> TILT servo
```

The Linux-side Python application performs face detection and tracking logic.

Servo commands are sent to the MCU through `Arduino_RouterBridge`.

The MCU generates the servo control pulses using `Arduino_HardwareServo`.

---

## Project Structure

```text
uno-q-ai-tracking-camera/
├── README.md
├── LICENSE
├── .gitignore
│
├── app/
│   └── ai-tracking-camera-with-servo/
│       ├── app.yaml
│       ├── python/
│       │   └── main.py
│       ├── sketch/
│       │   ├── sketch.ino
│       │   └── sketch.yaml
│       └── assets/
│           └── index.html
│
├── examples/
│   └── servotest/
│       ├── README.md
│       └── sketch/
│           ├── sketch.ino
│           └── sketch.yaml
│
└── images/
    ├── prototype.jpg
    ├── webui-screenshot.png
    └── system-overview.png
```

---

## App Lab Components

The application currently uses:

- **Video Object Detection**
- **WebUI-HTML**
- `Arduino_HardwareServo`
- `Arduino_RouterBridge`

On recent UNO Q Zephyr platform versions, `Arduino_RouterBridge` is part of the platform and should not be explicitly added to `sketch.yaml`.

A typical `sketch.yaml` therefore contains only the servo library:

```yaml
profiles:
  default:
    fqbn:
    platforms:
      - platform: arduino:zephyr
    libraries:
      - Arduino_HardwareServo (0.0.1)

default_profile: default
```

---

## Tracking Parameters

The current prototype uses the following values:

```text
Image size       : 640 x 480
Image center     : (320, 240)

Dead zone X      : +/-40 pixels
Dead zone Y      : +/-30 pixels

PAN servo range  : 1250 - 1750 us
TILT servo range : 1250 - 1750 us

PAN center       : 1500 us
TILT center      : 1500 us

Servo update     : 100 ms
Maximum step     : 15 us/update
```

The tested servo mechanism was also checked manually over approximately `1200 - 1800 us`, but a narrower range is used during automatic tracking.

For the current mechanical installation, both servo directions are reversed in software:

```python
PAN_DIR = -1
TILT_DIR = -1
```

These values may need to be changed depending on the orientation of the servos in another pan/tilt mechanism.

---

## Tracking Behavior

The face center is calculated from the detected bounding box.

```text
error_x = face_x - image_center_x
error_y = face_y - image_center_y
```

The camera is moved only when the detected face is outside the configured dead zone.

The farther the face is from the image center, the larger the servo correction becomes, up to a configured maximum step.

When no face is detected, the current servo position is held.

---

## Web Interface

The browser interface can be opened at:

```text
http://<UNO-Q-IP>:7000
```

The interface currently displays:

- Live camera image
- Face bounding box
- Face center point
- Image center
- Dead-zone rectangle
- Line from image center to face center
- X/Y tracking error
- Detection confidence
- PAN pulse width
- TILT pulse width
- Tracking ON/OFF button
- Center button

Current endpoints:

```text
GET  /tracking
POST /tracking/toggle
POST /center
```

---

## Tracking ON/OFF

When tracking is turned OFF:

- face detection continues,
- the live image continues,
- the overlay continues to update,
- servo movement stops.

This makes it possible to adjust the camera or mechanism without disabling the entire application.

---

## Center Control

The Center button returns both servos to:

```text
PAN  = 1500 us
TILT = 1500 us
```

If tracking is still ON, automatic tracking resumes immediately after centering.

To keep the camera at the center position:

1. Turn Tracking OFF.
2. Press Center.

---

## Servo Test Example

A small standalone servo test is included in:

```text
examples/servotest/
```

This was used before integrating face tracking, allowing the servo hardware, pulse ranges, and UNO Q PWM operation to be verified independently.

---

## Future Work

The next major goal is to use the tracked camera as a webcam source for video conferencing applications.

A possible architecture is:

```text
UNO Q
   |
   | Network video
   v
PC / Mac
   |
   +-- OBS / GStreamer
   |
   +-- Virtual Camera
   |
   +-- Microsoft Teams / Zoom
```

This approach would allow the UNO Q to continue performing face detection and physical camera tracking while a PC exposes the video stream as a standard virtual webcam.

---

## Notes

This project is currently a prototype and the servo limits and movement parameters are specific to the tested hardware.

Before using different servos or another pan/tilt mechanism:

- verify the safe pulse-width range,
- confirm the servo direction,
- use an independent servo power supply,
- keep the software travel limits conservative during initial testing.

---

## Acknowledgements

This project was developed with assistance from ChatGPT for software design, debugging, documentation, and implementation ideas.

Arduino, UNO Q, and related product names are trademarks of their respective owners.
