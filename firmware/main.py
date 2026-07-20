# =====================================================================
#  허스키렌즈 → ESP32 (NodeMCU ESP-32S) → SPIKE Prime (App3 워드 블럭)
#  [MicroPython / SPIKE 색 센서 위장 + 콤보 모드]
# =====================================================================
#
#  ■ 이 펌웨어가 하는 일
#    ESP32 가 SPIKE 허브에게 자신을 "레고 색 센서(id 61)"라고 소개한다.
#    허브는 색 센서의 값을 콤보 모드(0x5C)로 한꺼번에 읽어 가는데,
#    패치된 lpf2.py 가 그 요청을 해석해 허스키렌즈에서 받은 값을 실어 보낸다.
#    덕분에 SPIKE App 3 의 워드 블럭에서 추가 설치 없이 카메라 값을 쓸 수 있다.
#
# ---------------------------------------------------------------------
#  ■ 허스키렌즈 알고리즘별 값 매핑  (★ 펌웨어는 자동으로 구분한다)
#
#  허스키렌즈는 요청(0x20)에 두 종류로 응답한다.
#    · 블록(Block, 0x2A)  : 네모 상자로 잡히는 대상 → 아래 ①
#    · 화살표(Arrow, 0x2B): 라인 추적 전용          → 아래 ②
#
#  ① 블록형 알고리즘  —  아래 알고리즘은 전부 같은 매핑으로 동작한다
#       · Face Recognition      (얼굴 인식)
#       · Object Tracking       (물체 추적)
#       · Object Recognition    (물체 인식)
#       · Color Recognition     (색상 인식)
#       · Tag Recognition       (태그/QR 인식)
#       · Object Classification (물체 분류)
#
#       [색상]      = 학습된 ID (0 = 아무것도 없음, 1,2,3... = 학습 번호)
#       [원시 빨강] = 중심 X   (0~320, 화면 중앙 160)   ← 좌우 위치
#       [원시 초록] = 중심 Y   (0~240, 화면 중앙 120)   ← 위아래 위치
#       [원시 파랑] = 가로 폭 W (클수록 가까움)          ← 거리 대용
#
#  ② 화살표형 알고리즘  —  Line Tracking (라인 추적) 전용
#
#       [색상]      = 1 이면 라인 감지, 0 이면 라인 없음
#       [원시 빨강] = 화살표 시작 X (아래쪽 = 로봇 바로 앞)  0~320
#       [원시 초록] = 화살표 끝   X (위쪽 = 앞쪽 방향)      0~320
#       [원시 파랑] = 화살표 끝   Y                        0~240
#
#       → 기본 조향은 [원시 빨강](지금 라인 위치, 중앙 160),
#         곡선 예측은 [원시 초록] − [원시 빨강](앞쪽에서 휘는 방향).
#
#  ※ 어느 경우든 감지가 없으면 모든 값이 0 이 된다.
#  ※ ESP32 는 설정할 것이 없다. 허스키렌즈 본체에서 알고리즘만 바꾸면
#     값의 의미가 바로 바뀐다. SPIKE 프로그램만 모드에 맞게 쓰면 된다.
#
# ---------------------------------------------------------------------
#  ■ 허스키렌즈 설정
#       General Settings → Protocol Type = "Serial 9600"
#       원하는 알고리즘 선택 후 학습(learn) 시킬 것
#
#  ■ 배선 (NodeMCU ESP-32S)
#    · SPIKE LPF2 : UART2 기본핀 → GPIO18(RX), GPIO19(TX)
#         허브 핀5(TX)→GPIO18,  핀6(RX)→GPIO19,  핀3(GND)→GND
#    · 허스키렌즈 : UART1 → GPIO16(RX), GPIO17(TX)   ※ T/R 는 교차 연결
#         허스키 T(초록)→GPIO16,  R(파랑)→GPIO17,  −(검정)→GND
#    · 전원 : 허스키렌즈는 5V 급전 권장(USB/파워뱅크). GND 는 반드시 공통.
#             허브 3.3V(핀4) 공유는 전류가 빠듯해 권장하지 않음.
#
#  ■ 필요 파일 : 같은 폴더에 lpf2.py (콤보 모드 패치본), pupremote.py
# =====================================================================

from machine import UART, Pin
import time
import struct
import lpf2

# ---- 설정 -----------------------------------------------------------
HL_UART_ID = 1          # 허스키렌즈용 UART 번호
HL_RX_PIN  = 16         # ESP32 RX ← 허스키 T(초록)
HL_TX_PIN  = 17         # ESP32 TX → 허스키 R(파랑)
HL_BAUD    = 9600       # 허스키렌즈 Protocol Type = Serial 9600
LED_PIN    = 2          # 온보드 LED (연결 상태 표시)

SPIKE_COLOR_ID = 61     # SPIKE 색 센서의 장치 ID

POLL_MS  = 60           # 허스키렌즈를 읽는 주기 (ms)
MISS_MAX = 5            # 이 횟수만큼 연속 미감지여야 0 으로 (플리커 방지)

# ---- 허스키렌즈 통신 프로토콜 ---------------------------------------
HEADER       = b'\x55\xAA\x11'
CMD_REQUEST  = 0x20     # "지금 보이는 것을 알려줘"
CMD_RET_INFO = 0x29     # 결과 개수 응답
CMD_RET_BLK  = 0x2A     # 블록(네모) 데이터
CMD_RET_ARW  = 0x2B     # 화살표(라인) 데이터

KIND_NONE  = 0
KIND_BLOCK = 1
KIND_ARROW = 2


class HuskyLens:
    """허스키렌즈 UART 드라이버 (블록/화살표 모두 지원)"""

    def __init__(self, uart):
        self.uart = uart

    def _send(self, cmd, data=b''):
        body = HEADER + bytes([len(data), cmd]) + data
        self.uart.write(body + bytes([sum(body) & 0xFF]))

    def _read_exact(self, n, timeout_ms=50):
        buf = b''
        t0 = time.ticks_ms()
        while len(buf) < n:
            if self.uart.any():
                buf += self.uart.read(n - len(buf))
            elif time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                return None
        return buf

    def _read_frame(self):
        # 헤더 55 AA 11 을 찾고 [길이][명령][데이터][체크섬] 을 읽는다
        if self._read_exact(1) != b'\x55': return None
        if self._read_exact(1) != b'\xAA': return None
        if self._read_exact(1) != b'\x11': return None
        hl = self._read_exact(2)
        if not hl:
            return None
        length, cmd = hl[0], hl[1]
        data = self._read_exact(length) if length else b''
        self._read_exact(1)               # 체크섬 버림
        return cmd, data

    def request_first(self):
        """첫 번째 결과를 읽어 (종류, ID, v1, v2, v3) 로 돌려준다.

        블록  : (KIND_BLOCK, ID, 중심X,   중심Y, 가로W)
        화살표: (KIND_ARROW, ID, 시작X,   끝X,   끝Y)
        없으면 None.
        """
        while self.uart.any():            # 묵은 데이터 비우기
            self.uart.read()
        self._send(CMD_REQUEST)

        first = self._read_frame()
        if not first or first[0] != CMD_RET_INFO or len(first[1]) < 2:
            return None
        count = struct.unpack('<H', first[1][0:2])[0]

        for _ in range(count):
            f = self._read_frame()
            if not f:
                break
            cmd, data = f

            if cmd == CMD_RET_BLK and len(data) >= 10:
                # 블록: 중심X, 중심Y, 폭, 높이, ID
                x, y, w, h, oid = struct.unpack('<HHHHH', data[:10])
                return (KIND_BLOCK, oid, x, y, w)

            if cmd == CMD_RET_ARW and len(data) >= 10:
                # 화살표: 시작X, 시작Y, 끝X, 끝Y, ID
                x_org, y_org, x_tgt, y_tgt, oid = struct.unpack('<HHHHH', data[:10])
                if oid == 0:
                    oid = 1               # 화살표가 있으면 '라인 있음'
                return (KIND_ARROW, oid, x_org, x_tgt, y_tgt)

        return None


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def build_modes():
    """진짜 SPIKE 색 센서(id 61)와 같은 모드 0~6 을 만든다.

    워드 블럭이 실제로 읽는 것은 mode0(COLOR)·mode1(REFLT)·mode5(RGB I)이며,
    허브는 이들을 콤보 모드로 한 번에 요청한다.
    """
    M = lpf2.LPF2.mode
    D8 = lpf2.DATA8
    D16 = lpf2.DATA16
    return [
        M("COLOR", 1, D8,  format="2.0", raw_range=[0, 10],   si_range=[0, 10],   symbol="IDX", functionmap=[0xE4, 0x00]),
        M("REFLT", 1, D8,  format="3.0", raw_range=[0, 100],  si_range=[0, 100],  symbol="PCT", functionmap=[0x30, 0x00]),
        M("AMBI",  1, D8,  format="3.0", raw_range=[0, 100],  si_range=[0, 100],  symbol="PCT", functionmap=[0x30, 0x00]),
        M("LIGHT", 3, D8,  format="3.0", raw_range=[0, 100],  si_range=[0, 100],  symbol="PCT", functionmap=[0x00, 0x10]),
        M("RREFL", 2, D16, format="4.0", raw_range=[0, 1024], si_range=[0, 1024], symbol="RAW", functionmap=[0x10, 0x00]),
        M("RGB I", 4, D16, format="4.0", raw_range=[0, 1024], si_range=[0, 1024], symbol="RAW", functionmap=[0x10, 0x00]),
        M("HSV",   3, D16, format="4.0", raw_range=[0, 360],  si_range=[0, 360],  symbol="RAW", functionmap=[0x10, 0x00]),
    ]


def main():
    # 상태 표시 LED (없어도 동작에는 지장 없음)
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.value(0)
    except Exception:
        led = None

    hl_uart = UART(HL_UART_ID, baudrate=HL_BAUD,
                   tx=Pin(HL_TX_PIN), rx=Pin(HL_RX_PIN), timeout=50)
    husky = HuskyLens(hl_uart)

    lp = lpf2.LPF2(build_modes(), sensor_id=SPIKE_COLOR_ID, max_packet_size=32)

    # --- 허브 연결 (잡힐 때까지 반복) ---
    print("Connecting to SPIKE hub as color sensor (id %d)..." % SPIKE_COLOR_ID)
    blink = 0
    while not lp.connected:
        lp.connect()
        if led:
            blink ^= 1
            led.value(blink)
        if not lp.connected:
            time.sleep_ms(200)
    if led:
        led.value(1)

    print("Connected.")
    print("  Block  (face/object/color/tag) : rawR=centerX rawG=centerY rawB=width")
    print("  Arrow  (line tracking)         : rawR=originX rawG=targetX rawB=targetY")

    # --- 메인 루프 ---
    last_poll = time.ticks_ms()
    oid = v1 = v2 = v3 = 0
    miss = 0
    last_kind = KIND_NONE

    while True:
        # 허브 서비스는 매 반복 호출해야 연결이 끊기지 않는다
        lp.heartbeat()

        if time.ticks_diff(time.ticks_ms(), last_poll) >= POLL_MS:
            last_poll = time.ticks_ms()

            try:
                res = husky.request_first()
            except Exception:
                res = None

            if res:
                kind, oid, v1, v2, v3 = res
                oid = clamp(oid, 0, 10)
                v1 = clamp(v1, 0, 1023)
                v2 = clamp(v2, 0, 1023)
                v3 = clamp(v3, 0, 1023)
                miss = 0
                if kind != last_kind:      # 알고리즘이 바뀌면 한 번 알려준다
                    last_kind = kind
                    print("mode:", "ARROW (line tracking)" if kind == KIND_ARROW
                          else "BLOCK (face/object/color/tag)")
            else:
                # 한두 번 놓쳐도 마지막 값 유지 → 0 과 번갈이(플리커) 방지
                miss += 1
                if miss >= MISS_MAX:
                    oid = v1 = v2 = v3 = 0

            # 콤보 모드용 값 저장
            #   mode0 = 색상(ID) / mode1 = 반사광(미사용) / mode5 = [R, G, B, 4번째]
            #   허브가 요청한 순서대로 lpf2 가 알아서 채워 보낸다.
            lp.mode_values = {0: [oid], 1: [0], 5: [v1, v2, v3, 0]}

            # ★ load_payload = '저장만'. update_payload 처럼 비요청 전송을 하면
            #   콤보 프레임 사이에 끼어들어 값이 깨진다. 전송은 오직 허브의
            #   요청(NACK=콤보, CMD_Select=해당 모드)에 대한 응답으로만 이뤄진다.
            lp.load_payload([oid], 0)              # mode0 COLOR
            lp.load_payload([v1, v2, v3, 0], 5)    # mode5 RGB I

        time.sleep_ms(3)


main()
