# KitchenAI — PROJECT HANDOFF

Дата: 2026-10-01

## Цель
Полностью бесплатный локальный Windows-конструктор кухонь:
текст + необязательные план/фото -> локальный AI -> Kitchen JSON -> точная геометрия -> Blender -> визуализация -> точечные изменения.

План и фото необязательны.

## Репозиторий
https://github.com/WAYVE0707/KitchenAI-Package01

## Package 01 сейчас
Есть:
- src/app.py — GUI/чат;
- Ollama API;
- выбор установленной модели;
- Lite/Standard/Pro;
- необязательные изображения и документы;
- Kitchen JSON;
- стабильные object IDs;
- история/версии проекта;
- smoke tests;
- Inno Setup;
- GitHub Actions для Windows EXE/installer.

Пока нет:
- реальной 3D-геометрии кухни;
- Blender pipeline;
- полноценного render;
- image-AI/inpainting.

Это Package 02+.

## ПК
Intel Core i3-9100F
8 GB DDR4-2666
NVIDIA GeForce GT 1030
2 GB VRAM
NVIDIA driver 555.85
CUDA reported by nvidia-smi: 12.5

Целевой профиль: Lite / CPU.

## Ошибка Ollama
Команда:
ollama run qwen3.5:4b

Ошибка:
CUDA error: the provided PTX was compiled with an unsupported toolchain.
llama-server crashed with 0xc0000409.

Это ошибка CUDA runner, а не приложения KitchenAI. В 2026 Ollama имеет похожие Windows/Pascal reports; для обхода GPU-проблемы разработчики указывают num_gpu=0 как рабочий способ принудительного CPU-режима.

Источники:
- https://github.com/ollama/ollama/issues/17012
- https://github.com/ollama/ollama/issues/9836
- https://github.com/ollama/ollama/blob/main/docs/troubleshooting.mdx

## Уже внесено в репозиторий
Последний фикс в src/app.py:
Lite передаёт Ollama options:
- num_gpu = 0
- num_ctx = 2048
- num_batch = 32
- num_thread = 4

Lite установлен по умолчанию.

Также создан:
tools/setup_low_end_cpu.cmd

Скрипт:
1. ollama pull qwen3.5:4b
2. создаёт Modelfile
3. создаёт модель qwen3.5:4b-cpu
4. задаёт PARAMETER num_gpu 0
5. задаёт num_ctx 2048, num_batch 32, num_thread 4
6. запускает тест

## Что сделать на ПК
1. Полностью закрыть Ollama из системного трея.
2. Убедиться, что модель есть:
   ollama pull qwen3.5:4b
3. В репозитории запустить:
   tools\setup_low_end_cpu.cmd
4. Проверить:
   ollama run qwen3.5:4b-cpu "Ответь одним словом: ГОТОВО"
5. Если ответ есть — запускать KitchenAI и использовать Lite.

Для 8 GB RAM + GT 1030 2 GB не использовать Qwen 27B. Qwen3.5:4b сейчас около 3.4 GB в Q4_K_M и поддерживает текст + изображения:
https://ollama.com/library/qwen3.5

## GitHub Actions
workflow:
.github/workflows/build.yml

Он:
- windows-latest
- Python 3.12
- requirements + PyInstaller
- smoke tests
- KitchenAI.exe
- Inno Setup
- KitchenAI_Setup.exe
- artifact KitchenAI-Package-01-Windows

До последнего фикса уже был успешный Windows artifact примерно 25.5 MB.
После последних коммитов запущены новые сборки автоматически. Нужно проверить их итог.

## Следующий шаг
После успешного Package 01:
Package 02:
- Blender headless/portable
- Kitchen JSON -> точная геометрия в миллиметрах
- стены, шкафы, техника, столешницы
- стабильные object IDs
- collision/clearance checks
- камеры и render

Затем:
Package 03 — материалы/свет/визуализация.
Package 04 — точечные изменения объекта/материала + маски/inpainting.
Package 05 — финальный installer + автоопределение железа.

## Главный принцип
CAD/3D geometry = источник истины.
AI image = только визуальный слой.
Фраза "поменяй только столешницу" не должна перестраивать всю кухню.
