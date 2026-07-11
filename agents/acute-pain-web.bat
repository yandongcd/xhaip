@echo off
title xhaip - 急性疼痛评估与管理 (:8841)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 急性疼痛评估与管理 on http://127.0.0.1:8841
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8841
pause
