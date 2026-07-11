@echo off
title xhaip - 全院指标数据中心 (:8767)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 全院指标数据中心 on http://127.0.0.1:8767
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8767
pause
