# =====================================================================
#  search_track_reverse.py — 탐색 → 추적 → 근접 → 바닥감지 후진
#  SPIKE App 3 / Python   (워드 블럭 버전과 동일한 구조)
# ---------------------------------------------------------------------
#  동작 (무한 반복)
#    1) 추적 루프 — 물체의 세로 위치(원시 초록 Y)가 NEAR_Y 를 넘을 때까지:
#         · 색상 = 0(안 보임) → 제자리 회전으로 탐색
#         · 그 외             → (원시 빨강 X - 160) ÷ 2 로 조향하며 전진
#       → Y 가 커지면 물체가 화면 아래쪽(로봇 코앞)에 온 것 = 충분히 근접
#    2) 정지 후 앞으로 직진
#    3) 포트 C 컬러센서 밝기(반사광)가 Th 를 넘을 때까지 대기
#    4) 정지 후 뒤로 30cm → 처음으로
#
#  포트
#    D : ESP32 (허스키렌즈)   — 물체 위치/색
#    C : 실제 레고 컬러센서    — 바닥 밝기
#    A, B : 좌우 구동 모터
#
#  Th 계산: 밝은 바닥(BRIGHT_VAL) 과 어두운 바닥(DARK_VAL) 의 중간값.
#           WS2812 조명을 켠 상태에서 실제로 잰 값을 넣을 것.
# =====================================================================

from hub import port
import runloop
import motor_pair
import color_sensor

VISION = port.D          # ESP32(허스키렌즈)
BRIGHT = port.C          # 실제 컬러센서 (밝기)
LEFT   = port.A
RIGHT  = port.B

CENTER_X   = 160         # 화면 가로 중앙
STEER_DIV  = 2           # (X-160)/이 값 = 조향
NEAR_Y     = 200         # 원시 초록(Y)이 이 값을 넘으면 '근접' 으로 판단
DRIVE_VEL  = 100         # 주행 속도 (deg/s). 워드블럭 10% 에 해당
SEARCH_STEER = 100       # 탐색 시 제자리 회전 방향
SEARCH_VEL = 150

# 바닥 밝기 임계값 = (밝은 값 + 어두운 값) / 2   ← 워드블럭의 (98+33)/2
BRIGHT_VAL = 98
DARK_VAL   = 33
TH = (BRIGHT_VAL + DARK_VAL) / 2

REVERSE_CM   = 30
WHEEL_DIA_MM = 56
REVERSE_DEG  = int(REVERSE_CM * 10 / (3.14159 * WHEEL_DIA_MM) * 360)

motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


async def main():
    while True:
        # 1) 추적 루프 : 물체가 가까워질(Y > NEAR_Y) 때까지
        while True:
            x, y, w, color = color_sensor.rgbi(VISION)
            if y > NEAR_Y:
                break
            if color == 0:
                # 안 보임 → 제자리 회전 탐색
                motor_pair.move(motor_pair.PAIR_1, SEARCH_STEER, velocity=SEARCH_VEL)
            else:
                # 추적 : 중앙(160) 기준 조향하며 전진
                steering = clamp((x - CENTER_X) // STEER_DIV, -100, 100)
                motor_pair.move(motor_pair.PAIR_1, steering, velocity=DRIVE_VEL)
            await runloop.sleep_ms(20)

        # 2) 정지 후 앞으로 직진
        motor_pair.stop(motor_pair.PAIR_1)
        motor_pair.move(motor_pair.PAIR_1, 0, velocity=DRIVE_VEL)

        # 3) 바닥이 Th 보다 밝아질 때까지 대기
        while color_sensor.reflection(BRIGHT) <= TH:
            await runloop.sleep_ms(20)

        # 4) 정지 후 뒤로 30cm
        motor_pair.stop(motor_pair.PAIR_1)
        await motor_pair.move_for_degrees(
            motor_pair.PAIR_1, REVERSE_DEG, 0, velocity=-DRIVE_VEL)


runloop.run(main())
