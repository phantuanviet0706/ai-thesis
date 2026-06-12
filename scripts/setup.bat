@echo off
chcp 65001 >nul
cls
echo ============================================
echo    Đang khởi tạo môi trường cho Chatbot
echo ============================================

:: 1. Kiểm tra Ollama
echo [*] Đang kiểm tra Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama chưa được cài đặt! Vui lòng cài đặt tại ollama.com
    pause
    exit /b
)

:: 2. Pull các model cần thiết về
echo [*] Đang kéo các model LLM cần thiết về thiết bị (Có thể sẽ mất thời gian) ...
ollama pull qwen2.5:1.5b
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull phi3.5:latest
ollama pull gemma2:2b
ollama pull smollm2:1.7b
ollama pull qwen2.5:0.5b
ollama pull deepseek-coder:1.3b
ollama pull stable-code:latest
echo [OK] Đã kéo xong các model

:: 3. Kiểm tra và khởi tạo môi trường ảo venv nếu cần
echo [*] Đang kiểm tra môi trường ảo (venv)
if not exist ".venv" (
    echo [+] Đang khởi tạo venv mới...
    python -m venv .venv
) else (
    echo [OK] venv đã tồn tại
)

:: 4. Active venv và cài đặt các thư viện cần thiết (pip)
echo [*] Đang cập nhật các thư viện từ requirements.txt ...
call venv\Scripts\activate
python -m pip install --upgrade pip
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo [WARNING] Không tìm thấy file requirements.txt
)

echo ============================================
echo        Chúc mừng! Mọi thứ đã sẵn sàng
echo ============================================
pause