# drizz-emulator-api
A FastAPI-based server for controlling Android emulators via HTTP.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-org>/drizz-emulator-api.git
   cd drizz-emulator-api
   ```
2. **Create and activate a Python virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   .venv\Scripts\activate         # Windows
   ```
3. **Install Python dependencies:**
   ```bash
   pip install fastapi uvicorn
   ```
4. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Prerequisites
- Python 3.9 or higher
- Android SDK (ensure `emulator` and `adb` are in your PATH)
- (Optional) Node.js 16+ if integrating with a Next.js frontend

## Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-org>/drizz-emulator-api.git
   cd drizz-emulator-api
   ```
2. **Create and activate a Python virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   .venv\Scripts\activate         # Windows
   ```
3. **Install Python dependencies:**
   ```bash
   pip install fastapi uvicorn
   ```
4. **Verify Android SDK tools are available:**
   ```bash
   adb version
   emulator -version
   ```

## Running the Server
Start the FastAPI server on port 8000:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000`.

## API Endpoints
- **POST /start_emulator**  
  Launches an Android emulator.  
  ```json
  {
    "name": "AVD_Name",
    "port": 5554
  }
  ```
- **POST /open_chrome**  
  Opens Chrome on a running emulator.  
  ```json
  { "serial": "emulator-5554" }
  ```
- **POST /open_dialer**  
  Opens the Dialer on a running emulator.  
  ```json
  { "serial": "emulator-5554" }
  ```
- **GET /video_feed/{serial}**  
  Streams the emulator screen as MJPEG frames.  
- **POST /start_and_open**  
  Starts an emulator, waits for boot and video-ready, then opens Chrome and/or Dialer.  
  ```json
  {
    "name": "AVD_Name",
    "port": 5554,
    "open_chrome": true,
    "open_dialer": false
  }
  ```

## Integration with Next.js
Use the provided endpoints to start emulators and stream video into your React/Next.js UI. Ensure CORS is configured to allow `http://localhost:3000`.
