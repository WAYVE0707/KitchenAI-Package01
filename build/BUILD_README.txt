Сборка Windows должна выполняться на Windows. PyInstaller прямо указывает, что он не является кросс-компилятором.
Запустите PowerShell от обычного пользователя в корне проекта:
  Set-ExecutionPolicy -Scope Process Bypass
  .\build\build_windows.ps1

Для получения KitchenAI_Setup.exe нужен установленный Inno Setup и команда ISCC.exe в PATH.
