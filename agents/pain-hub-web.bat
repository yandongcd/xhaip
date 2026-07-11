@echo off
title xhaip - 疼痛专病智能体门户 (:8840)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 疼痛专病智能体门户 on http://127.0.0.1:8840
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8840
pause
