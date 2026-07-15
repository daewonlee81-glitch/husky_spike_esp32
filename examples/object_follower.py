# =====================================================================
#  object_follower.py — 물체를 추적하며 따라가기 (SPIKE App 3 / Python)
# ---------------------------------------------------------------------
#  red_ball_tracker.py 는 제자리에서 좌우로 돌기만 한다.
#  이 코드는 한 걸음 더 나아가, 물체를 화면 중앙에 두면서(조향)
#  일정한 크기(=거리)를 유지하도록 앞뒤로도 움직인다.
#
#  값 매핑
#    색상(color)      = HuskyLens ID  (0 이면 아무것도 안 보임)
#    원시 빨강(red)   = 중심 X   (0~320, 중앙 160)   → 좌우 조향
#    원시 초록(green) = 중심 Y   (0~240)
#    원시 파랑(blue)  = 가로폭 W (클수록 가까움)      → 앞뒤 거리
#
#  동작
#    - 물체 없음(color=0)        → 정지
#    - 물체가 왼쪽/오른쪽        → 그쪽으로 조향
#    - 물체가 작다(멀다)         → 전진해서 다가감
#    - 물체가 크다(가깝다)       → 후진해서 물러남
#    - 목표 크기 부근            → 조향만, 전진속도 0
# =====================================================================

from hub import port
import runloop
import color_sensor
import motor_pair

SENSOR = port.C          # ESP32 (색 센서)
LEFT   = port.A          # 왼쪽 모터
RIGHT  = port.E          # 오른쪽 모터

CENTER_X = 160           # 화면 가로 중앙
TARGET_W = 100           # 유지할 물체 크기(거리). 클수록 더 가까이 따라감
W_DEADBAND = 15          # 이 폭 안이면 전진/후진 안 함(떨림 방지)

STEER_GAIN = 0.6         # 조향 세기 (클수록 민감)
DRIVE_GAIN = 3.0         # 전후진 세기
MAX_VEL    = 300         # 최대 속도(deg/s)

motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


async def main():
    while True:
        # r=중심 X, g=중심 Y, b=가로폭 W, i=색상 ID
        r, g, b, i = color_sensor.rgbi(SENSOR)

        if i == 0:
            # 아무것도 안 보임 → 정지 (원하면 여기서 제자리 탐색 회전 가능)
            motor_pair.stop(motor_pair.PAIR_1)
        else:
            # 좌우 조향: 중앙에서 벗어난 만큼
            steering = clamp(int((r - CENTER_X) * STEER_GAIN), -100, 100)

            # 앞뒤 속도: 목표 크기보다 작으면(멀면) 전진(+), 크면(가까우면) 후진(-)
            w_err = TARGET_W - b
            if -W_DEADBAND < w_err < W_DEADBAND:
                velocity = 0
            else:
                velocity = clamp(int(w_err * DRIVE_GAIN), -MAX_VEL, MAX_VEL)

            if velocity == 0:
                # 거리 OK → 제자리에서 조향만
                motor_pair.move(motor_pair.PAIR_1, steering, velocity=120)
            else:
                # 조향 + 전/후진
                motor_pair.move(motor_pair.PAIR_1, steering, velocity=velocity)

        await runloop.sleep_ms(20)


runloop.run(main())
