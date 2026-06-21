#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess
import threading
import time


def run_agent_in_background():
    """ኤጀንቱን ከጀርባ አስኬድ"""
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        from django.conf import settings
        if getattr(settings, 'AUTONOMOUS_AGENT_ENABLED', True):
            print("🚀 Starting Autonomous Agent in background...")
            from marketplace.growth_agent import run_autonomous_agent
            # በልዩ ክር ውስጥ አስኬድ
            thread = threading.Thread(target=run_autonomous_agent, daemon=True)
            thread.start()
    except Exception as e:
        print(f"⚠️ Could not start agent: {e}")


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # ሸል ካልሆነ ኤጀንቱን አስነሳ
    if 'shell' not in sys.argv and 'migrate' not in sys.argv:
        try:
            run_agent_in_background()
        except Exception:
            pass
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()