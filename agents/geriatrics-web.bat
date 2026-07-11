@echo off
title xhaip - 老年病科智能体 (:8790)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 老年病科智能体 on http://127.0.0.1:8790
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8790
pause
