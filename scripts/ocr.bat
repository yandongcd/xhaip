@echo off
:: OCR PDF/Image → text using RapidOCR
:: Usage: ocr.bat document.pdf [output.txt]
:: If output not specified, prints to stdout.
setlocal
set "IMG=%1"
if "%IMG%"=="" (
    echo Usage: ocr ^<file.pdf^|file.png^> [output.txt]
    exit /b 1
)
if "%2"=="" (
    rapidocr_onnxruntime -img "%IMG%"
) else (
    rapidocr_onnxruntime -img "%IMG%" > "%2"
)
