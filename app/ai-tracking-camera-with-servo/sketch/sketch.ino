#include <Arduino_HardwareServo.h>
#include <Arduino_RouterBridge.h>

HardwareServo panServo;
HardwareServo tiltServo;

const int PAN_PIN  = 9;
const int TILT_PIN = 10;

const int PAN_MIN_US  = 1250;
const int PAN_MAX_US  = 1750;
const int TILT_MIN_US = 1250;
const int TILT_MAX_US = 1750;

const int PAN_CENTER_US  = 1500;
const int TILT_CENTER_US = 1500;


// Python側から呼ばれる
void set_servos(int pan_us, int tilt_us)
{
    pan_us = constrain(
        pan_us,
        PAN_MIN_US,
        PAN_MAX_US
    );

    tilt_us = constrain(
        tilt_us,
        TILT_MIN_US,
        TILT_MAX_US
    );

    panServo.writeMicroseconds(pan_us);
    tiltServo.writeMicroseconds(tilt_us);
}


void setup()
{
    Monitor.begin(115200);

    if (panServo.attach(
            PAN_PIN,
            PAN_MIN_US,
            PAN_MAX_US
        ) == INVALID_SERVO) {

        Monitor.println("PAN servo attach failed");

        while (1) {
            delay(1000);
        }
    }

    if (tiltServo.attach(
            TILT_PIN,
            TILT_MIN_US,
            TILT_MAX_US
        ) == INVALID_SERVO) {

        Monitor.println("TILT servo attach failed");

        while (1) {
            delay(1000);
        }
    }

    // 起動時は中央
    panServo.writeMicroseconds(PAN_CENTER_US);
    tiltServo.writeMicroseconds(TILT_CENTER_US);

    Bridge.begin();

    Bridge.provide(
        "set_servos",
        set_servos
    );

    Monitor.println("Servo controller ready");
}


void loop()
{
    delay(100);
}