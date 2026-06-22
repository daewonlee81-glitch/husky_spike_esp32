# =====================================================================
#  허스키렌즈 -> ESP32 (NodeMCU ESP-32S) -> SPIKE Prime (App3 워드 블럭)
#  [MicroPython / 색 센서 + 콤보 모드]  ★ 원시 RGB 워드 블럭
# ---------------------------------------------------------------------
#  색 센서(id 61)를 모드 0~6 으로 흉내 내고, 콤보 모드(0x5C)를 처리하는
#  패치된 lpf2.py 를 사용한다. SPIKE3 색 센서 워드 블럭 매핑:
#
#     [색상]      = 감지된 ID        (콤보 mode0)
#     [원시 빨강] = 중심 X (0~320)   (콤보 mode5 R)
#     [원시 초록] = 중심 Y (0~240)   (콤보 mode5 G)
#     [원시 파랑] = 가로 W           (콤보 mode5 B)
#     (감지 없으면 0)
#
#  연결 (NodeMCU ESP-32S):
#   - SPIKE LPF2 : UART2 기본핀 → GPIO18(RX), GPIO19(TX)  (연결 검증됨)
#       허브 핀5(TX)->GPIO18, 핀6(RX)->GPIO19, 핀3(GND)->GND
#   - 허스키렌즈 : UART1 → GPIO16(RX), GPIO17(TX)
#       허스키 T(초록)->GPIO16, R(파랑)->GPIO17, +(빨강)->3.3V, -(검정)->GND
#
#  필요 파일: 같은 폴더에 lpf2.py (콤보 모드 패치본), pupremote.py
# =====================================================================

from machine import UART, Pin
import time
import struct
import lpf2

HL_UART_ID = 1
HL_RX_PIN  = 16
HL_TX_PIN  = 17
HL_BAUD    = 9600
LED_PIN    = 2
SPIKE_COLOR_ID = 61

HEADER       = b'\x55\xAA\x11'
CMD_REQUEST  = 0x20
CMD_RET_INFO = 0x29
CMD_RET_BLK  = 0x2A
CMD_RET_ARW  = 0x2B


class HuskyLens:
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
        if self._read_exact(1) != b'\x55': return None
        if self._read_exact(1) != b'\xAA': return None
        if self._read_exact(1) != b'\x11': return None
        hl = self._read_exact(2)
        if not hl: return None
        length, cmd = hl[0], hl[1]
        data = self._read_exact(length) if length else b''
        self._read_exact(1)
        return cmd, data

    def request_first_block(self):
        while self.uart.any():
            self.uart.read()
        self._send(CMD_REQUEST)
        first = self._read_frame()
        if not first or first[0] != CMD_RET_INFO or len(first[1]) < 2:
            return None
        n = struct.unpack('<H', first[1][0:2])[0]
        for _ in range(n):
            f = self._read_frame()
            if not f:
                break
            cmd, data = f
            if cmd == CMD_RET_BLK and len(data) >= 10:
                x, y, w, h, oid = struct.unpack('<HHHHH', data[:10])
                return (oid, x, y, w)
            elif cmd == CMD_RET_ARW and len(data) >= 10:
                xt, yt, xh, yh, oid = struct.unpack('<HHHHH', data[:10])
                return (oid, xh, yh, 0)
        return None


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def build_modes():
    M = lpf2.LPF2.mode
    D8 = lpf2.DATA8
    D16 = lpf2.DATA16
    # 진짜 SPIKE 색 센서(id 61) 모드 0~6 (워드 블럭/콤보는 0,1,5 사용)
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
    try:
        led = Pin(LED_PIN, Pin.OUT); led.value(0)
    except Exception:
        led = None

    hl_uart = UART(HL_UART_ID, baudrate=HL_BAUD,
                   tx=Pin(HL_TX_PIN), rx=Pin(HL_RX_PIN), timeout=50)
    husky = HuskyLens(hl_uart)

    lp = lpf2.LPF2(build_modes(), sensor_id=SPIKE_COLOR_ID, max_packet_size=32)

    print("Connecting to hub (color sensor + combo)...")
    blink = 0
    while not lp.connected:
        lp.connect()
        if led:
            blink ^= 1; led.value(blink)
        if not lp.connected:
            time.sleep_ms(200)
    if led:
        led.value(1)
    print("Connected! color=ID, rawR=X, rawG=Y, rawB=W")

    last_husky = time.ticks_ms()
    oid = x = y = w = 0
    miss = 0          # 연속 미감지 횟수 (플리커 방지용 디바운스)
    MISS_MAX = 5      # 약 300ms 연속 미감지 시에만 0 으로
    while True:
        lp.heartbeat()                                   # 허브 서비스 (자주)
        if time.ticks_diff(time.ticks_ms(), last_husky) >= 60:
            last_husky = time.ticks_ms()
            try:
                res = husky.request_first_block()
            except Exception:
                res = None
            if res:
                oid, x, y, w = res
                oid = clamp(oid, 0, 10)
                x = clamp(x, 0, 1023); y = clamp(y, 0, 1023); w = clamp(w, 0, 1023)
                miss = 0
            else:
                # 한두 번 놓쳐도 마지막 값을 유지 (0과 번갈이 = 플리커 방지)
                miss += 1
                if miss >= MISS_MAX:
                    oid = x = y = w = 0
            # 콤보 모드용 값: mode0=색상(ID), mode1=반사광(0), mode5=RGB[R,G,B,4th]
            #   (허브가 요청한 순서대로 lpf2 가 알아서 채움)
            lp.mode_values = {0: [oid], 1: [0], 5: [x, y, w, 0]}
            # 개별 모드는 '저장만'(load_payload). 콤보가 정확하므로 비요청 전송
            # (update_payload)은 프레임을 끼어들게 해 깜빡임을 유발하므로 안 함.
            # 전송은 허브 요청(NACK=콤보, Select=해당 모드)에 대한 응답으로만.
            lp.load_payload([oid], 0)            # mode0 COLOR (저장만)
            lp.load_payload([x, y, w, 0], 5)     # mode5 RGB I (저장만)
        time.sleep_ms(3)


main()
