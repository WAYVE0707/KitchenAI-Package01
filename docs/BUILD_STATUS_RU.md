# Статус сборки Package 01

## Проверено в текущей среде
- исходный код синтаксически компилируется Python 3.13;
- smoke test Kitchen JSON / patch / hardware profiles проходит;
- проект содержит воспроизводимый Windows build script;
- проект содержит Inno Setup script;
- проект содержит GitHub Actions workflow для Windows installer.

## Почему в этой поставке нет готового `KitchenAI_Setup.exe`
Текущая среда исполнения — Linux. PyInstaller собирает приложения для платформы, на которой запускается сборка, и не является кросс-компилятором для Windows. Поэтому честно сгенерировать и протестировать Windows PE/installer здесь нельзя. Официальная документация PyInstaller прямо указывает это ограничение. См. ссылку в итоговом отчёте.

На реальном Windows или Windows CI:
1. запускается `build\\build_windows.cmd`;
2. создаётся `dist\\KitchenAI.exe`;
3. Inno Setup создаёт `dist\\KitchenAI_Setup.exe`;
4. GitHub Actions workflow также может собрать этот же installer как artifact.
