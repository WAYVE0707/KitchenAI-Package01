# Kitchen AI Designer — Package 01

Локальный Windows-first прототип/рабочее приложение для Package 01 ТЗ Kitchen AI Designer v1.

## Что реализовано
- современный чат-интерфейс на Tkinter/ttk;
- локальное подключение к Ollama через HTTP API;
- автоматический список установленных моделей Ollama;
- ручной выбор модели без жёсткой привязки к Qwen;
- проекты в `Kitchen JSON`;
- локальная история чата;
- версии проекта и откат;
- необязательные PNG/JPG/JPEG/WEBP/PDF/DXF вложения;
- передача последних изображений локальной vision-модели через Ollama;
- базовое извлечение структурных изменений через `<KITCHEN_PATCH>`;
- стабильные object IDs для структурных объектов;
- проверка CPU/RAM/GPU/свободного места и рекомендация Lite/Standard/Pro;
- полностью локальное хранение пользовательских данных.

## Важная граница Package 01
Blender/геометрический движок, рендер, CAD и image-AI намеренно не маскируются под готовые функции Package 01. Их место — Package 02+.

## Запуск из исходников
```powershell
py -3 -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python src\\app.py
```

## Ollama
Установите Ollama для Windows и скачайте любую совместимую локальную модель. Приложение само получает `/api/tags` и показывает модели в выпадающем списке.

## Данные
По умолчанию Windows хранит проекты в `%LOCALAPPDATA%\\KitchenAI\\Projects`.

Каждый проект:
```text
Projects\\Client_001_xxxxxxxx\\
  project.kitchen.json
  references\\
  renders\\
  versions\\
```

## Сборка Windows
Сборку Windows нужно выполнять на Windows: PyInstaller не является кросс-компилятором. См. `build\\build_windows.ps1` и `installer\\KitchenAI.iss`.
