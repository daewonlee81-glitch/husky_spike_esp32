# =====================================================================
#  line_follower.py — 라인 트레이싱 (SPIKE App 3 / Python)
# ---------------------------------------------------------------------
#  HuskyLens 알고리즘을 "Line Tracking" 으로 두고 라인을 학습시킨 뒤 사용한다.
#  ESP32 펌웨어가 화살표(Arrow) 데이터를 색 센서 원시값으로 실어 보낸다.
#
#  값 매핑 (color_sensor.rgbi(port) -> (r, g, b, i))
#    i = 색상      = 1 이면 라인 감지, 0 이면 라인 없음
#    r = 원시 빨강 = 화살표 시작 X (로봇 바로 앞 라인 위치)  0~320, 중앙 160
#    g = 원시 초록 = 화살표 끝   X (앞쪽 라인이 향하는 방향)  0~320
#    b = 원시 파랑 = 화살표 끝   Y                            0~240
#
#  제어
#    기본 조향  = (시작X - 160)          ← 지금 라인이 얼마나 치우쳤나
#    곡선 예측  = (끝X - 시작X)          ← 앞쪽에서 라인이 휘는 방향
#    조향 = 기본×KP + 예측×KD  (예측을 섞으면 커브에서 훨씬 부드럽다)
# =====================================================================

from hub import port
import runloop
import motor_pair
import color_sensor

SENSOR = port.C          # ESP32 (색 센서)
LEFT   = port.B          # 왼쪽 모터
RIGHT  = port.A          # 오른쪽 모터

CENTER_X = 160           # 화면 가로 중앙
KP       = 0.45          # 현재 위치 오차 반영 세기 (크면 민감, 흔들리면 낮춘다)
KD       = 0.25          # 앞쪽 곡선 예측 반영 세기
DRIVE_VEL = 300          # 주행 속도 (deg/s). 커브가 급하면 낮춘다
SEARCH_VEL = 150         # 라인을 잃었을 때 탐색 회전 속도

motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


async def main():
    last_steer = 0       # 라인을 놓쳤을 때 마지막 방향으로 찾기 위해 기억

    while True:
        x_org, x_tgt, y_tgt, line = color_sensor.rgbi(SENSOR)

        if line == 0:
            # 라인을 놓침 → 마지막으로 꺾던 방향으로 제자리 회전하며 다시 찾기
            direction = 100 if last_steer >= 0 else -100
            motor_pair.move(motor_pair.PAIR_1, direction, velocity=SEARCH_VEL)
        else:
            error   = x_org - CENTER_X          # 지금 라인이 치우친 정도
            curve   = x_tgt - x_org             # 앞쪽에서 휘는 방향
            steering = clamp(int(error * KP + curve * KD), -100, 100)
            last_steer = steering
            motor_pair.move(motor_pair.PAIR_1, steering, velocity=DRIVE_VEL)

        await runloop.sleep_ms(20)


runloop.run(main())
