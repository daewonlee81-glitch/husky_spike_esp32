#!/usr/bin/env python3
# =====================================================================
#  ESP32-C3 미니 한 방 설치 스크립트
#  (MicroPython 펌웨어 + lpf2.py + pupremote.py + main.py)
# ---------------------------------------------------------------------
#  ※ 이 스크립트는 "당신의 컴퓨터"에서 실행합니다. (ESP32가 USB로 연결된 PC)
#
#  하는 일:
#    1) esptool, mpremote 자동 설치 (없으면)
#    2) MicroPython ESP32-C3 펌웨어(.bin) 자동 다운로드
#    3) 플래시 지우기 + 펌웨어 기록 (오프셋 0)
#    4) lpf2.py / pupremote.py / main.py 를 보드에 업로드
#
#  사용법:
#    python install_firmware.py                # 포트 자동 감지
#    python install_firmware.py --port COM5    # 윈도우 예
#    python install_firmware.py --port /dev/cu.usbmodem01   # 맥 예
#    python install_firmware.py --skip-flash   # 펌웨어는 그대로, 코드 파일만 재업로드
#
#  3개 .py 파일(main.py, lpf2.py, pupremote.py)을 이 스크립트와 같은
#  폴더에 두고 실행하세요.
# =====================================================================

import argparse
import os
import subprocess
import sys
import time
import urllib.request

# --- 설치할 MicroPython 펌웨어 (일반 ESP32 / NodeMCU ESP-32S, v1.28.0) ---
MPY_URL = "https://micropython.org/resources/firmware/ESP32_GENERIC-20260406-v1.28.0.bin"
MPY_FILE = "ESP32_GENERIC-20260406-v1.28.0.bin"
ESPTOOL_CHIP = "esp32"        # 일반 ESP32 (C3는 esp32c3)
FLASH_OFFSET = "0x1000"       # 일반 ESP32는 0x1000 (C3/S3는 0x0)

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FILES = ["lpf2.py", "pupremote.py", "main.py"]


def run(cmd):
    print("\n$ " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def ensure_tool(module, pip_name=None):
    pip_name = pip_name or module
    try:
        __import__(module)
        return
    except ImportError:
        print(f"[설치] {pip_name} 가 없어 설치합니다...")
        rc = run([sys.executable, "-m", "pip", "install", pip_name])
        if rc != 0:
            print(f"[오류] {pip_name} 설치 실패. 수동으로 'pip install {pip_name}' 해보세요.")
            sys.exit(1)


def download_firmware():
    dst = os.path.join(HERE, MPY_FILE)
    if os.path.exists(dst):
        print(f"[펌웨어] 이미 있음: {MPY_FILE}")
        return dst
    print(f"[펌웨어] 다운로드 중: {MPY_URL}")
    try:
        urllib.request.urlretrieve(MPY_URL, dst)
    except Exception as e:
        print(f"[오류] 펌웨어 다운로드 실패: {e}")
        print("       브라우저로 직접 받아 이 폴더에 두고 다시 실행하세요.")
        sys.exit(1)
    print(f"[펌웨어] 저장 완료: {MPY_FILE}")
    return dst


def esptool_cmd(port, *args):
    cmd = [sys.executable, "-m", "esptool", "--chip", ESPTOOL_CHIP]
    if port:
        cmd += ["--port", port]
    cmd += list(args)
    return cmd


def mpremote_cmd(port, *args):
    cmd = [sys.executable, "-m", "mpremote"]
    cmd += ["connect", port] if port else ["connect", "auto"]
    cmd += list(args)
    return cmd


def upload_files(port):
    missing = [f for f in UPLOAD_FILES if not os.path.exists(os.path.join(HERE, f))]
    if missing:
        print(f"[오류] 같은 폴더에 다음 파일이 없습니다: {', '.join(missing)}")
        sys.exit(1)

    # 보드가 재부팅 후 REPL 을 띄울 시간을 준 뒤, 몇 번 재시도
    print("\n[업로드] 보드 재부팅 대기 (5초)...")
    time.sleep(5)
    for attempt in range(1, 6):
        print(f"[업로드] 시도 {attempt}/5")
        ok = True
        for f in UPLOAD_FILES:
            rc = run(mpremote_cmd(port, "fs", "cp", os.path.join(HERE, f), ":" + f))
            if rc != 0:
                ok = False
                break
        if ok:
            print("\n[완료] 세 파일 업로드 성공!")
            return True
        print("   연결 실패. 3초 후 재시도...")
        time.sleep(3)
    print("[오류] 파일 업로드 실패. 포트(--port)를 지정하거나 Thonny로 수동 업로드하세요.")
    return False


def main():
    ap = argparse.ArgumentParser(description="ESP32-C3 MicroPython + 펌웨어 설치")
    ap.add_argument("--port", default=None, help="시리얼 포트 (예: COM5 / /dev/cu.usbmodem01). 생략 시 자동 감지")
    ap.add_argument("--baud", default="460800", help="플래시 속도 (기본 460800, 불안정하면 115200)")
    ap.add_argument("--skip-flash", action="store_true", help="펌웨어 플래시 건너뛰고 .py 파일만 업로드")
    ap.add_argument("--bin", default=None, help="이미 받아둔 펌웨어 .bin 경로 지정")
    args = ap.parse_args()

    print("=" * 60)
    print(" ESP32-C3 미니 펌웨어 설치 시작")
    print("=" * 60)

    ensure_tool("mpremote")

    if not args.skip_flash:
        ensure_tool("esptool")
        binpath = args.bin or download_firmware()

        print("\n[1/2] 플래시 지우기 (erase_flash)")
        if run(esptool_cmd(args.port, "erase_flash")) != 0:
            print("[오류] erase_flash 실패. 보드를 부트(다운로드) 모드로 두고 --port 를 지정해 보세요.")
            print("       (보통 BOOT 버튼을 누른 채 RESET 한 번 → BOOT 떼기)")
            sys.exit(1)

        print("\n[2/2] 펌웨어 기록 (write_flash {})".format(FLASH_OFFSET))
        if run(esptool_cmd(args.port, "--baud", args.baud, "write_flash", FLASH_OFFSET, binpath)) != 0:
            print("[오류] write_flash 실패. --baud 115200 으로 다시 시도해 보세요.")
            sys.exit(1)

    upload_files(args.port)

    print("\n" + "=" * 60)
    print(" 끝! ESP32-C3 를 SPIKE 허브 포트 C 에 꽂고 전원을 켜세요.")
    print(" SPIKE App 3 에서 '색 센서'로 잡히면 성공입니다.")
    print("=" * 60)


if __name__ == "__main__":
    main()
