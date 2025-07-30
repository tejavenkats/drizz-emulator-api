from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import shutil
import time
import asyncio
from fastapi.responses import StreamingResponse
from typing import List

# Locate Android SDK tools, fallback to environment variable if PATH lookup fails
SDK_ROOT = os.environ.get("ANDROID_SDK_ROOT", "")
ADB_CMD = shutil.which("adb") or os.path.join(SDK_ROOT, "platform-tools", "adb")
EMU_CMD = shutil.which("emulator") or os.path.join(SDK_ROOT, "emulator", "emulator")

def wait_for_emulator(serial: str, timeout: int = 60):
    """
    Polls the emulator until boot is complete or timeout is reached.
    """
    start = time.time()
    while True:
        try:
            output = subprocess.check_output([ADB_CMD, "-s", serial, "shell", "getprop", "sys.boot_completed"])
            if output.strip() == b'1':
                return
        except subprocess.CalledProcessError:
            pass
        if time.time() - start > timeout:
            raise RuntimeError(f"Emulator {serial} did not boot within {timeout} seconds")
        time.sleep(1)

def ensure_video_ready(serial: str, timeout: int = 30):
    """
    Polls the emulator framebuffer until a valid video frame is obtained or timeout.
    """
    start_time = time.time()
    while True:
        try:
            img = subprocess.check_output([
                ADB_CMD, "-s", serial, "exec-out", "screencap", "-p"
            ], timeout=5)
            if img:
                return
        except Exception:
            pass
        if time.time() - start_time > timeout:
            raise RuntimeError(f"Video feed for {serial} not ready within {timeout} seconds")
        time.sleep(1)

def kill_emulator(serial: str):
    """
    Kills the emulator instance for the given serial, if running.
    """
    try:
        subprocess.run(
            [ADB_CMD, "-s", serial, "emu", "kill"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    except Exception:
        pass


app = FastAPI(title="Android Emulator Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EmuRequest(BaseModel):
    name: str                # AVD name, e.g. "Medium_Phone_API_36.0"
    port: int = Field(..., ge=5554, le=5584, description="Even-numbered TCP port for this emulator")


class CmdRequest(BaseModel):
    serial: str  # emulator serial from `adb devices`, e.g. "emulator-5554"


class StartAndOpenRequest(BaseModel):
    name: str               # AVD name
    port: int = Field(..., ge=5554, le=5584, description="Even-numbered TCP port for this emulator")
    open_chrome: bool = False
    open_dialer: bool = False


@app.post("/start_emulator")
async def start_emulator(req: EmuRequest):
    """
    Launches an Android emulator on the exact port you specify.
    """
    # ensure port is even
    if req.port % 2 != 0:
        raise HTTPException(status_code=400, detail="Port must be an even number (e.g. 5554, 5556, ...)")
    try:
        # derive serial and kill any existing emulator on this port
        serial = f"emulator-{req.port}"
        kill_emulator(serial)
        subprocess.Popen([
            EMU_CMD,
            "-avd", req.name,
            "-port", str(req.port),
            "-read-only",
            "-no-window",
            "-no-audio",
        ])
        # wait for the emulator to finish booting
        wait_for_emulator(serial)
        # ensure emulator framebuffer is streaming before returning
        ensure_video_ready(serial)
        return {
            "status": "ok",
            "message": f"AVD '{req.name}' started and booted on port {req.port}",
            "serial": serial,
            "feed_url": f"http://localhost:8000/video_feed/{serial}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/open_chrome")
async def open_chrome(cmd: CmdRequest):
    try:
        # wait for emulator to finish booting
        wait_for_emulator(cmd.serial)
        # ensure emulator framebuffer is streaming before issuing commands
        ensure_video_ready(cmd.serial)
        subprocess.run([
            ADB_CMD, "-s", cmd.serial,
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", "http://www.google.com"
        ], check=True)
        return {"status": "ok", "message": "Chrome opened"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr)


@app.post("/open_dialer")
async def open_dialer(cmd: CmdRequest):
    try:
        # wait for emulator to finish booting
        wait_for_emulator(cmd.serial)
        # ensure emulator framebuffer is streaming before issuing commands
        ensure_video_ready(cmd.serial)
        subprocess.run([
            ADB_CMD, "-s", cmd.serial,
            "shell", "am", "start",
            "-a", "android.intent.action.DIAL"
        ], check=True)
        return {"status": "ok", "message": "Dialer opened"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr)


@app.post("/start_and_open")
async def start_and_open(req: StartAndOpenRequest):
    """
    Launches an emulator, waits for it to boot and video ready, then opens Chrome and/or Dialer.
    """
    if req.port % 2 != 0:
        raise HTTPException(status_code=400, detail="Port must be an even number (e.g. 5554, 5556, ...)")
    serial = f"emulator-{req.port}"
    try:
        # kill any existing emulator and start a new one
        kill_emulator(serial)
        subprocess.Popen([
            EMU_CMD,
            "-avd", req.name,
            "-port", str(req.port),
            "-read-only",
            "-no-window",
            "-no-audio",
        ])
        # wait for boot and video
        wait_for_emulator(serial)
        ensure_video_ready(serial)
        # run requested opens
        if req.open_chrome:
            subprocess.run([
                ADB_CMD, "-s", serial,
                "shell", "am", "start",
                "-a", "android.intent.action.VIEW",
                "-d", "http://www.google.com"
            ], check=True)
        if req.open_dialer:
            subprocess.run([
                ADB_CMD, "-s", serial,
                "shell", "am", "start",
                "-a", "android.intent.action.DIAL"
            ], check=True)
        return {
            "status": "ok",
            "serial": serial,
            "feed_url": f"http://localhost:8000/video_feed/{serial}",
            "chrome": req.open_chrome,
            "dialer": req.open_dialer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Streams the emulator screen as an MJPEG stream.
@app.get("/video_feed/{serial}")
async def video_feed(serial: str):
    """
    Streams the emulator screen as an MJPEG stream.
    """
    async def frame_generator():
        while True:
            try:
                # Capture screen as PNG
                img = subprocess.check_output([
                    ADB_CMD, "-s", serial, "exec-out", "screencap", "-p"
                ])
                # Yield frame boundary and data
                yield b"--frame\r\n"
                yield b"Content-Type: image/png\r\n\r\n"
                yield img
                yield b"\r\n"
                # control frame rate
                await asyncio.sleep(0.1)
            except Exception:
                break

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )