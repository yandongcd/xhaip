@echo off
title xhaip - 围术期心脏评估 (:8801)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 围术期心脏评估 on http://127.0.0.1:8801
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8801
pause
