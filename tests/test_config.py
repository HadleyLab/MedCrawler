import logging
import os
from pathlib import Path
from config import (
    APP_NAME,
    LOG_LEVEL,
    BASE_DIR,
    NOTIFICATION_DEFAULTS,
    LOGGING_CONFIG
)

def test_base_configuration():
    assert isinstance(APP_NAME, str)
    assert LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert isinstance(BASE_DIR, Path)
    assert BASE_DIR.exists()

def test_notification_defaults():
    assert isinstance(NOTIFICATION_DEFAULTS, dict)
    assert "position" in NOTIFICATION_DEFAULTS
    assert "timeout" in NOTIFICATION_DEFAULTS
    assert isinstance(NOTIFICATION_DEFAULTS["timeout"], int)
    assert NOTIFICATION_DEFAULTS["position"] in [
        "top-left", "top-right", "bottom-left", 
        "bottom-right", "top", "bottom", "left", 
        "right", "center"
    ]

def test_logging_configuration():
    assert isinstance(LOGGING_CONFIG, dict)
    assert "version" in LOGGING_CONFIG
    assert "handlers" in LOGGING_CONFIG
    assert "loggers" in LOGGING_CONFIG
    
    # Test log file creation
    log_file = BASE_DIR / "app.log"
    logger = logging.getLogger(__name__)
    logger.info("Test log entry")
    assert log_file.exists()
    
    with open(log_file, 'r') as f:
        log_content = f.read()
        assert "Test log entry" in log_content