
#!/usr/bin/env python3
"""
AstraGuard AI - Timeline Logger

Event logging and timeline management for the AstraGuard system.
Provides structured logging with timestamps and event retrieval.

Author: Subhajit Roy
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# Constants
LOG_PATH = Path(__file__).parent / "event_log.txt"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB maximum log size
BACKUP_COUNT = 5  # Number of backup logs to keep


def ensure_log_directory() -> None:
    """Ensure log directory exists."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def rotate_log_if_needed() -> None:
    """
    Rotate log file if it exceeds maximum size.
    
    Creates backup files and clears the main log when needed.
    """
    ensure_log_directory()
    
    if not LOG_PATH.exists():
        return
    
    # Check file size
    if LOG_PATH.stat().st_size < MAX_LOG_SIZE:
        return
    
    # Rotate logs
    for i in range(BACKUP_COUNT - 1, 0, -1):
        backup_path = LOG_PATH.with_suffix(f".txt.{i}")
        if backup_path.exists():
            if i == BACKUP_COUNT - 1:
                # Remove oldest backup
                backup_path.unlink()
            else:
                # Move to next backup number
                new_backup_path = LOG_PATH.with_suffix(f".txt.{i + 1}")
                backup_path.rename(new_backup_path)
    
    # Move current log to backup
    backup_path = LOG_PATH.with_suffix(".txt.1")
    LOG_PATH.rename(backup_path)
    
    # Create new empty log
    LOG_PATH.touch()


def log_event(event_type: str, details: str, severity: str = "INFO") -> bool:
    """
    Log an event with timestamp, type, and details.
    
    Args:
        event_type: Type of event (e.g., "ANOMALY", "FAULT", "RECOVERY")
        details: Event description or details
        severity: Event severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        True if logging successful, False otherwise
    """
    try:
        ensure_log_directory()
        rotate_log_if_needed()
        
        # Create timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Create log entry
        entry = f"{timestamp} | {severity} | {event_type} | {details}\n"
        
        # Write to log file
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        
        return True
        
    except Exception as e:
        print(f"Failed to log event: {e}")
        return False


def read_recent(n: int = 20) -> List[str]:
    """
    Read the most recent log entries.
    
    Args:
        n: Number of recent entries to read
    
    Returns:
        List of recent log entries (newest first)
    """
    try:
        ensure_log_directory()
        
        if not LOG_PATH.exists():
            return []
        
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        
        # Return last n entries, newest first
        return lines[-n:][::-1] if lines else []
        
    except Exception as e:
        print(f"Failed to read recent logs: {e}")
        return []


def read_all() -> List[str]:
    """
    Read all log entries.
    
    Returns:
        List of all log entries
    """
    try:
        ensure_log_directory()
        
        if not LOG_PATH.exists():
            return []
        
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return f.read().strip().splitlines()
        
    except Exception as e:
        print(f"Failed to read all logs: {e}")
        return []


def filter_events(event_type: str, limit: Optional[int] = None) -> List[str]:
    """
    Filter log entries by event type.
    
    Args:
        event_type: Event type to filter for
        limit: Maximum number of entries to return
    
    Returns:
        List of filtered log entries
    """
    try:
        all_events = read_all()
        filtered = [entry for entry in all_events if event_type in entry]
        
        if limit:
            filtered = filtered[-limit:][::-1]  # Newest first
        else:
            filtered = filtered[::-1]  # Newest first
        
        return filtered
        
    except Exception as e:
        print(f"Failed to filter events: {e}")
        return []


def get_event_statistics() -> Dict[str, Any]:
    """
    Get statistics about logged events.
    
    Returns:
        Dictionary with event statistics
    """
    try:
        all_events = read_all()
        
        if not all_events:
            return {
                "total_events": 0,
                "event_types": {},
                "severity_counts": {},
                "first_event": None,
                "last_event": None
            }
        
        # Count event types and severities
        event_types = {}
        severity_counts = {}
        
        for event in all_events:
            parts = event.split(" | ")
            if len(parts) >= 3:
                severity = parts[1].strip()
                event_type = parts[2].strip()
                
                event_types[event_type] = event_types.get(event_type, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_events": len(all_events),
            "event_types": event_types,
            "severity_counts": severity_counts,
            "first_event": all_events[0] if all_events else None,
            "last_event": all_events[-1] if all_events else None
        }
        
    except Exception as e:
        print(f"Failed to get event statistics: {e}")
        return {}


def clear_log() -> bool:
    """
    Clear the log file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_log_directory()
        
        if LOG_PATH.exists():
            LOG_PATH.unlink()
        
        LOG_PATH.touch()
        return True
        
    except Exception as e:
        print(f"Failed to clear log: {e}")
        return False


def export_log(output_path: str, format_type: str = "txt") -> bool:
    """
    Export log to different formats.
    
    Args:
        output_path: Output file path
        format_type: Export format ('txt', 'csv', 'json')
    
    Returns:
        True if export successful, False otherwise
    """
    try:
        all_events = read_all()
        
        if format_type == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(all_events))
        
        elif format_type == "csv":
            import csv
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Severity", "Event Type", "Details"])
                for event in all_events:
                    parts = event.split(" | ", 3)
                    if len(parts) >= 4:
                        writer.writerow(parts)
        
        elif format_type == "json":
            import json
            events_data = []
            for event in all_events:
                parts = event.split(" | ", 3)
                if len(parts) >= 4:
                    events_data.append({
                        "timestamp": parts[0],
                        "severity": parts[1],
                        "event_type": parts[2],
                        "details": parts[3]
                    })
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(events_data, f, indent=2, ensure_ascii=False)
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        return True
        
    except Exception as e:
        print(f"Failed to export log: {e}")
        return False


def main() -> None:
    """
    Main function for testing and demonstration.
    """
    print("=" * 60)
    print("AstraGuard AI - Timeline Logger")
    print("=" * 60)
    print()
    
    # Test logging functionality
    print("Testing event logging...")
    
    test_events = [
        ("SYSTEM_START", "AstraGuard AI system initialized", "INFO"),
        ("ANOMALY_DETECTED", "Power anomaly detected with score 0.95", "WARNING"),
        ("FAULT_CLASSIFIED", "Power fault classified", "ERROR"),
        ("RECOVERY_ACTION", "Entering SAFE_MODE", "INFO"),
        ("SYSTEM_RECOVERY", "Normal operations resumed", "INFO")
    ]
    
    for event_type, details, severity in test_events:
        success = log_event(event_type, details, severity)
        print(f"{'✓' if success else '✗'} Logged: {event_type} - {details}")
    
    print()
    print("Recent events:")
    recent = read_recent(10)
    for event in recent:
        print(f"  {event}")
    
    print()
    print("Event statistics:")
    stats = get_event_statistics()
    print(f"  Total events: {stats.get('total_events', 0)}")
    print(f"  Event types: {stats.get('event_types', {})}")
    print(f"  Severity counts: {stats.get('severity_counts', {})}")
    
    print()
    print("Filtered anomaly events:")
    anomalies = filter_events("ANOMALY", 5)
    for anomaly in anomalies:
        print(f"  {anomaly}")


if __name__ == "__main__":
    main()
