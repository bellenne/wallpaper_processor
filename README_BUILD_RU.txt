Сборка .exe на Windows

1. Установи Python 3.12+ для Windows и отметь опцию Add Python to PATH.
2. Открой эту папку.
3. Дважды запусти build_exe.bat
4. Готовая папка сборки появится здесь:
   dist\WallpaperProcessor

Что внутри:
- WallpaperProcessor.exe
- все нужные библиотеки
- папка assets

Важно:
- этот проект лучше собирать именно на Windows, если тебе нужен Windows .exe
- из Linux/macOS корректный Windows .exe обычным PyInstaller не собирается
