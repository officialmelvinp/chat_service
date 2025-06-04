@echo off
echo Starting Celery Worker for service_chat...
python -m celery -A service_chat worker --loglevel=info --pool=solo
pause
