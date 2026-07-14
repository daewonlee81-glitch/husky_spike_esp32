# =====================================================================
#  red_ball_tracker.py — 색상 추적 (SPIKE App 3 / Python)
#  워드 블럭 버전(docs/redball_blocks.png)과 똑같이 동작하는 파이썬 코드
# ---------------------------------------------------------------------
#  하드웨어
#    포트 C    : ESP32 (색 센서로 위장 — HuskyLens 값 전달)
#    포트 A, E : 좌·우 구동 모터
#
#  값 매핑
#    색상(color)      = HuskyLens ID
#    원시 빨강(red)   = 물체 중심 X   (0 ~ 320, 화면 중앙 = 160)
#    원시 초록(green) = 물체 중심 Y   (0 ~ 240)
#    원시 파랑(blue)  = 물체 가로폭 W (클수록 가까움)
#
#  동작
#    X < 120  → 물체가 왼쪽   → 왼쪽으로 제자리 회전
#    X > 200  → 물체가 오른쪽 → 오른쪽으로 제자리 회전
#    그 외    → 중앙에 있음   → 정지
# =====================================================================

from hub import port
import runloop
import color_sensor
import motor_pair

SENSOR = port.C          # ESP32 (색 센서)
LEFT   = port.A          # 왼쪽 모터
RIGHT  = port.E          # 오른쪽 모터

SPEED    = 15            # 동작 속도 15 %
VELOCITY = SPEED * 10    # 워드 블럭의 15 % ≈ 150 deg/s

LEFT_EDGE  = 120         # 이 값보다 작으면 물체가 왼쪽
RIGHT_EDGE = 200         # 이 값보다 크면 물체가 오른쪽

motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)


async def main():
    while True:
        # r = 중심 X, g = 중심 Y, b = 가로폭 W
        r, g, b, i = color_sensor.rgbi(SENSOR)

        if r < LEFT_EDGE:
            # 왼쪽: 방향(steering) -100 → 제자리 좌회전
            motor_pair.move(motor_pair.PAIR_1, -100, velocity=VELOCITY)
        elif r > RIGHT_EDGE:
            # 오른쪽: 방향(steering) 100 → 제자리 우회전
            motor_pair.move(motor_pair.PAIR_1, 100, velocity=VELOCITY)
        else:
            # 중앙 → 이동 멈추기
            motor_pair.stop(motor_pair.PAIR_1)

        await runloop.sleep_ms(20)


runloop.run(main())
