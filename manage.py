#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Sabse pehle logging disable karo
import logging
logging.disable(logging.CRITICAL)

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Django setup se pehle logging disable karo
    from django.conf import settings
    settings.LOGGING_CONFIG = None
    
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()