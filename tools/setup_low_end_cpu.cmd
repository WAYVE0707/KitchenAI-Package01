@echo off
setlocal
cd /d "%~dp0.."

where ollama >nul 2>&1
if errorlevel 1 (
  echo Ollama не найден. Установите Ollama для Windows и повторите.
  pause
  exit /b 1
)

echo Проверяем базовую модель qwen3.5:4b...
ollama pull qwen3.5:4b
if errorlevel 1 (
  echo Не удалось скачать qwen3.5:4b
  pause
  exit /b 1
)

>Modelfile (
  echo FROM qwen3.5:4b
  echo PARAMETER num_gpu 0
  echo PARAMETER num_ctx 2048
  echo PARAMETER num_batch 32
  echo PARAMETER num_thread 4
)

echo Создаём CPU-профиль...
ollama create qwen3.5:4b-cpu -f Modelfile
if errorlevel 1 (
  echo Не удалось создать CPU-профиль.
  del Modelfile >nul 2>&1
  pause
  exit /b 1
)

del Modelfile >nul 2>&1
echo.
echo Готово. Тестируем CPU-модель:
ollama run qwen3.5:4b-cpu "Ответь одним словом: ГОТОВО"
echo.
echo Kitchen AI в режиме Lite будет использовать CPU и не отправлять слои на GT 1030.
pause
endlocal
