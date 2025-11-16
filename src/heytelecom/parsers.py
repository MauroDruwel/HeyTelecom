"""Parsing utilities for Hey Telecom data."""
import re
from datetime import datetime


def parse_data_amount(text):
    """Parse data amount like '2.25 GB' to numeric GB value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*(GB|MB|TB)', text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'MB':
            value = value / 1024  # Convert to GB
        elif unit == 'TB':
            value = value * 1024  # Convert to GB
        return round(value, 2)
    return None


def parse_price(text):
    """Parse price like '5 €/maand' to numeric value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*€', text)
    if match:
        return float(match.group(1))
    return None


def parse_date(text):
    """Parse date like '04.04.2025' or '20/10/2025' to ISO format."""
    if not text:
        return None
    # Try DD.MM.YYYY format
    match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    # Try DD/MM/YYYY format
    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return None


def parse_period(text):
    """Parse period like 'Van 11/10/2025 tot 11/11/2025' to start and end dates."""
    if not text:
        return None
    match = re.search(r'(\d{2}/\d{2}/\d{4})\s*tot\s*(\d{2}/\d{2}/\d{4})', text)
    if match:
        start_str, end_str = match.groups()
        return {
            "start": parse_date(start_str),
            "end": parse_date(end_str)
        }
    return None


def parse_minutes(text):
    """Parse minutes like '5 minuten' to numeric value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*min', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def parse_sms_count(text):
    """Parse SMS count like '0 sms/mms' to numeric value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*sms', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_last_update(text):
    """Parse last update like 'Laatste update : 03/11 17:54' to ISO datetime."""
    if not text:
        return None
    match = re.search(r'(\d{2}/\d{2})\s*(\d{2}:\d{2})', text)
    if match:
        date_part, time_part = match.groups()
        day, month = date_part.split('/')
        # Assume current year
        year = datetime.now().year
        return f"{year}-{month}-{day}T{time_part}:00"
    return None


def is_unlimited(text):
    """Check if a limit is unlimited."""
    if not text:
        return False
    return 'onbeperkt' in text.lower() or 'unlimited' in text.lower()
