import os

# 경로 설정
bat_path = r"D:\projects\run_upbit_bot.bat"
venv_python = r"D:\projects\.venv\Scripts\python.exe"
target_script = r"D:\projects\업비트감시\upbit_notice_Bot_V1.py"

# .bat 내용 구성
bat_content = f'''@echo off
"{venv_python}" "{target_script}"
'''

# 파일 생성
with open(bat_path, "w", encoding="utf-8") as f:
    f.write(bat_content)

print(f"[✅ 생성 완료] {bat_path}")
