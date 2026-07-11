@echo off
title xhaip - 患者数据中心 (:8766)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 患者数据中心 on http://127.0.0.1:8766
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8766
pause
