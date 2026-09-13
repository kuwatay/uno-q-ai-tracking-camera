#include <Arduino_HardwareServo.h>

HardwareServo panServo;

const int PAN_PIN = 9;

// 最初は非常に狭い範囲だけ試す
const int CENTER_US = 1500;
const int LEFT_TEST_US = 1300;
const int RIGHT_TEST_US = 1700;

void setup()
{
    // まず安全範囲を1300～1700 usに制限
    if (panServo.attach(PAN_PIN, 1300, 1700) == INVALID_SERVO) {
        while (1) {
            delay(1000);
        }
    }

    // 起動時は中央
    panServo.writeMicroseconds(CENTER_US);

    delay(3000);
}

void loop()
{
    // 中央
    panServo.writeMicroseconds(CENTER_US);
    delay(2000);

    // 一方向へごく少し
    panServo.writeMicroseconds(LEFT_TEST_US);
    delay(2000);

    // 中央へ戻る
    panServo.writeMicroseconds(CENTER_US);
    delay(2000);

    // 反対方向へごく少し
    panServo.writeMicroseconds(RIGHT_TEST_US);
    delay(2000);

    // 中央へ戻る
    panServo.writeMicroseconds(CENTER_US);
    delay(3000);
}