# =====================================================================
#  color_tracker.py — 탐지한 색상 추적 (SPIKE App 3 / Python)
# ---------------------------------------------------------------------
#  HuskyLens 를 Color Recognition 모드로 두고 색을 학습(ID 1)한 뒤 사용한다.
#  탐지된 색이 화면 중앙(160)에 오도록 로봇이 좌우로 조향한다.
#
#  값 매핑 (color_sensor.rgbi(port) -> (r, g, b, i))
#    i = 색상      = 감지된 ID (0 = 아무것도 없음)
#    r = 원시 빨강 = 중심 X  (0~320, 중앙 160)   ← 조향에 사용
#    g = 원시 초록 = 중심 Y
#    b = 원시 파랑 = 가로 W  (클수록 가까움)
#
#  동작
#    색상 = 0  → 안 보임 → 정지
#    그 외     → (X - 160) ÷ 2 만큼 좌우로 조향하며 전진
# =====================================================================

from hub import port
import runloop
import motor_pair
import color_sensor

SENSOR = port.D          # ESP32(색 센서)가 꽂힌 포트 — 환경에 맞게
LEFT   = port.A          # 왼쪽 모터
RIGHT  = port.B          # 오른쪽 모터

CENTER_X   = 160         # 화면 가로 중앙
STEER_DIV  = 2           # (X-160)을 이 값으로 나눠 조향. 크게 하면 둔감
DRIVE_VEL  = 300         # 주행 속도 (deg/s)

motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


async def main():
    while True:
        x, y, w, color = color_sensor.rgbi(SENSOR)

        if color == 0:
            # 색이 안 보임 → 정지
            motor_pair.stop(motor_pair.PAIR_1)
        else:
            # 중앙(160) 기준으로 좌우 조향하며 전진
            steering = clamp((x - CENTER_X) // STEER_DIV, -100, 100)
            motor_pair.move(motor_pair.PAIR_1, steering, velocity=DRIVE_VEL)

        await runloop.sleep_ms(20)


runloop.run(main())
