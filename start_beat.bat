@echo off
echo Starting Celery Beat for service_chat...
python -m celery -A service_chat beat --loglevel=info
pause
