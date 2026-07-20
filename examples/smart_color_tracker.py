# =====================================================================
#  smart_color_tracker.py — 색상 추적 (탐색 + 추적 + 정지)
#  SPIKE App 3 / Python
#  ---------------------------------------------------------------------
#  Pybricks "smart color tracker" 예제를 우리 시스템(ESP32 색 센서 위장)에
#  맞게 옮긴 것. unpack 이 필요 없다 — X/Y/W 가 이미 원시 RGB 로 분리돼 나온다.
#
#  값 매핑 (color_sensor.rgbi(port) -> (r, g, b, i))
#    r = 원시 빨강 = 중심 X   (0~320, 화면 중앙 160)
#    g = 원시 초록 = 중심 Y   (0~240)
#    b = 원시 파랑 = 가로폭 W  (클수록 가까움)
#    i = 색상 = HuskyLens ID  (0 = 아무것도 없음)
#
#  동작 (원본과 동일한 3단 판단)
#    W 아주 작음 → 안 보임    → 제자리 회전하며 탐색
#    W 아주 큼   → 매우 가까움 → 정지
#    그 외        → 전진하면서 X 위치로 좌우 조향
# =====================================================================

from hub import port
import runloop
import motor_pair
import color_sensor

SENSOR = port.C          # ESP32 (색 센서)
LEFT   = port.B          # 왼쪽 모터  (원본과 동일)
RIGHT  = port.A          # 오른쪽 모터

CENTER_X   = 160         # 화면 가로 중앙 (0~320)
SEARCH_W   = 2           # W 가 이 이하 → 안 보임 → 탐색
NEAR_W     = 150         # W 가 이 이상 → 너무 가까움 → 정지 (물체 크기에 맞게 조절)
STEER_GAIN = 0.6         # 조향 세기 (X 오차 × 이 값). 흔들리면 낮춘다
DRIVE_VEL  = 350         # 전진 속도 (deg/s)
SEARCH_VEL = 200         # 탐색 회전 속도 (deg/s)

motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


async def main():
    while True:
        x, y, w, i = color_sensor.rgbi(SENSOR)

        if w <= SEARCH_W:
            # 안 보임 → 제자리에서 오른쪽으로 계속 돌며 찾기
            motor_pair.move(motor_pair.PAIR_1, 100, velocity=SEARCH_VEL)

        elif w > NEAR_W:
            # 매우 가까움 → 정지
            motor_pair.stop(motor_pair.PAIR_1)

        else:
            # 추적 → 전진 + X 위치로 조향
            # X > 160 이면 물체가 오른쪽 → 조향 +(오른쪽), X < 160 이면 -(왼쪽)
            steering = clamp(int((x - CENTER_X) * STEER_GAIN), -100, 100)
            motor_pair.move(motor_pair.PAIR_1, steering, velocity=DRIVE_VEL)

        await runloop.sleep_ms(20)


runloop.run(main())
