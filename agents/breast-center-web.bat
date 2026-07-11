@echo off
title xhaip - 乳腺中心智能体 (:8797)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 乳腺中心智能体 on http://127.0.0.1:8797
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8797
pause
