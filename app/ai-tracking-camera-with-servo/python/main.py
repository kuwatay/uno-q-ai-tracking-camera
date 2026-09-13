# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l.
# SPDX-License-Identifier: MPL-2.0

import time
import threading

from arduino.app_utils import App, Logger, Bridge
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_bricks.web_ui import WebUI
from arduino.app_peripherals.camera import Camera


# ============================================================
# Camera / image settings
# ============================================================

WIDTH = 640
HEIGHT = 480

CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

# Dead zone around the image center
DEAD_X = 40
DEAD_Y = 30


# ============================================================
# Servo settings
# ============================================================

# We confirmed 1200-1800 us works.
# Use a slightly narrower range for normal tracking.
PAN_MIN = 1250
PAN_MAX = 1750

TILT_MIN = 1250
TILT_MAX = 1750

PAN_CENTER = 1500
TILT_CENTER = 1500

pan_us = PAN_CENTER
tilt_us = TILT_CENTER


# Servo direction
#
# If the camera moves AWAY from the face instead of toward it,
# change +1 to -1 for that axis.
PAN_DIR = -1
TILT_DIR = -1


# First test PAN only.
ENABLE_PAN = True
ENABLE_TILT = True


# Minimum interval between servo commands
SERVO_INTERVAL = 0.10

last_servo_update = 0.0

TRACKING_ENABLED = True


# ============================================================
# Logger
# ============================================================

logger = Logger("FaceTracker")


# ============================================================
# Camera
# ============================================================

camera = Camera(
    "/dev/video2",
    resolution=(WIDTH, HEIGHT),
    fps=15
)


# ============================================================
# Web UI
# ============================================================

ui = WebUI()

# Live camera stream for:
#   http://<UNO-Q-IP>:7000/camera
ui.expose_camera("/camera", camera)


# ============================================================
# Face detector
# ============================================================

detector = VideoObjectDetection(
    camera=camera,
    confidence=0.5,
    debounce_sec=0.0
)


# ============================================================
# Tracking state for Web UI
# ============================================================

state_lock = threading.Lock()

tracking_state = {
    "face": False,

    "x0": 0,
    "y0": 0,
    "x1": 0,
    "y1": 0,

    "face_x": 0,
    "face_y": 0,

    "error_x": 0,
    "error_y": 0,

    "confidence": 0.0,
    "status": "NO FACE",

    "center_x": CENTER_X,
    "center_y": CENTER_Y,

    "dead_x": DEAD_X,
    "dead_y": DEAD_Y,

    "pan_us": pan_us,
    "tilt_us": tilt_us,

    "pan_enabled": ENABLE_PAN,
    "tilt_enabled": ENABLE_TILT,

    "tracking_enabled": TRACKING_ENABLED
}


# ============================================================
# Utility: face area
# ============================================================

def face_area(face):
    box = face.get("bounding_box_xyxy")

    if box is None:
        return 0

    x0, y0, x1, y1 = box

    return max(0, x1 - x0) * max(0, y1 - y0)


# ============================================================
# Utility: servo step
# ============================================================

def servo_step(error, dead_zone):
    """
    Calculate servo movement in microseconds.

    No motion inside the dead zone.
    Larger image error produces a larger servo movement.
    """

    excess = abs(error) - dead_zone

    if excess <= 0:
        return 0

    # Proportional-like control
    step = int(excess * 0.1)

    # Minimum useful movement
    step = max(step, 3)

    # Limit one movement to avoid sudden motion
    step = min(step, 15)

    return step


# ============================================================
# Web API
# ============================================================

def get_tracking():
    with state_lock:
        return dict(tracking_state)


ui.expose_api(
    method="GET",
    path="/tracking",
    function=get_tracking
)

def toggle_tracking():
    global TRACKING_ENABLED

    TRACKING_ENABLED = not TRACKING_ENABLED

    with state_lock:
        tracking_state["tracking_enabled"] = TRACKING_ENABLED

    logger.info(
        "Tracking {}".format(
            "ON" if TRACKING_ENABLED else "OFF"
        )
    )

    return {
        "tracking_enabled": TRACKING_ENABLED
    }

ui.expose_api(
    method="POST",
    path="/tracking/toggle",
    function=toggle_tracking
)

def center_servos():
    global pan_us
    global tilt_us
    global last_servo_update

    pan_us = PAN_CENTER
    tilt_us = TILT_CENTER

    Bridge.notify(
        "set_servos",
        int(pan_us),
        int(tilt_us)
    )

    last_servo_update = time.monotonic()

    with state_lock:
        tracking_state["pan_us"] = pan_us
        tracking_state["tilt_us"] = tilt_us

    logger.info(
        "Servos centered: PAN={}us TILT={}us".format(
            pan_us,
            tilt_us
        )
    )

    return {
        "pan_us": pan_us,
        "tilt_us": tilt_us
    }
    
ui.expose_api(
    method="POST",
    path="/center",
    function=center_servos
)

# ============================================================
# Detection callback
# ============================================================

def on_detections(detections: dict):

    global pan_us
    global tilt_us
    global last_servo_update

    faces = detections.get("face", [])

    # --------------------------------------------------------
    # No face
    # --------------------------------------------------------

    if not faces:

        with state_lock:
            tracking_state["face"] = False
            tracking_state["status"] = "NO FACE"
            tracking_state["pan_us"] = pan_us
            tracking_state["tilt_us"] = tilt_us

        # Keep the current servo position.
        return


    # --------------------------------------------------------
    # Select target face
    # --------------------------------------------------------

    # If several faces exist, track the largest one.
    face = max(
        faces,
        key=face_area
    )

    box = face.get("bounding_box_xyxy")

    if box is None:
        return

    x0, y0, x1, y1 = box


    # --------------------------------------------------------
    # Face center
    # --------------------------------------------------------

    face_x = int(
        (x0 + x1) / 2
    )

    face_y = int(
        (y0 + y1) / 2
    )


    # --------------------------------------------------------
    # Error from image center
    # --------------------------------------------------------

    error_x = face_x - CENTER_X
    error_y = face_y - CENTER_Y

    confidence = float(
        face.get("confidence", 0.0)
    )


    # --------------------------------------------------------
    # Centered?
    # --------------------------------------------------------

    centered = (
        abs(error_x) <= DEAD_X
        and
        abs(error_y) <= DEAD_Y
    )

    if centered:
        status = "CENTERED"
    else:
        status = "TRACKING"


    # ========================================================
    # Servo tracking
    # ========================================================

    now = time.monotonic()

    if now - last_servo_update >= SERVO_INTERVAL:

        servo_changed = False


        # ----------------------------------------------------
        # PAN
        # ----------------------------------------------------

        if TRACKING_ENABLED and ENABLE_PAN:

            step = servo_step(
                error_x,
                DEAD_X
            )

            if step > 0:

                if error_x > 0:
                    pan_us += PAN_DIR * step

                elif error_x < 0:
                    pan_us -= PAN_DIR * step


                # Software limit
                pan_us = max(
                    PAN_MIN,
                    min(PAN_MAX, pan_us)
                )

                servo_changed = True


        # ----------------------------------------------------
        # TILT
        # ----------------------------------------------------

        if TRACKING_ENABLED and ENABLE_TILT:

            step = servo_step(
                error_y,
                DEAD_Y
            )

            if step > 0:

                if error_y > 0:
                    tilt_us += TILT_DIR * step

                elif error_y < 0:
                    tilt_us -= TILT_DIR * step


                # Software limit
                tilt_us = max(
                    TILT_MIN,
                    min(TILT_MAX, tilt_us)
                )

                servo_changed = True


        # ----------------------------------------------------
        # Send servo positions to STM32
        # ----------------------------------------------------

        if servo_changed:

            Bridge.notify(
                "set_servos",
                int(pan_us),
                int(tilt_us)
            )

            logger.info(
                f"Servo PAN={pan_us}us "
                f"TILT={tilt_us}us"
            )


        last_servo_update = now


    # ========================================================
    # Update Web UI data
    # ========================================================

    with state_lock:

        tracking_state.update({

            "face": True,

            "x0": int(x0),
            "y0": int(y0),
            "x1": int(x1),
            "y1": int(y1),

            "face_x": face_x,
            "face_y": face_y,

            "error_x": error_x,
            "error_y": error_y,

            "confidence": confidence,
            "status": status,

            "pan_us": pan_us,
            "tilt_us": tilt_us,

            "pan_enabled": ENABLE_PAN,
            "tilt_enabled": ENABLE_TILT,
            "tracking_enabled": TRACKING_ENABLED
        })


    # ========================================================
    # Console log
    # ========================================================

    logger.info(
        f"face confidence={confidence:.2f} "
        f"center=({face_x},{face_y}) "
        f"error=({error_x:+d},{error_y:+d}) "
        f"PAN={pan_us}us "
        f"TILT={tilt_us}us "
        f"{status}"
    )


# ============================================================
# Start detector
# ============================================================

detector.on_detect_all(
    on_detections
)


# ============================================================
# Run application
# ============================================================

App.run()