"""
crew_static_threshold.py - Static Threshold Baseline (No AI)

This is the baseline system with NO AI agents, NO LLM reasoning, NO multi-agent coordination.
Simply applies static threshold rules: if methane >= 5000 ppm, send alert.

For paper comparison: Static-Threshold baseline system.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Tuple

from data_layer.weaviate_client import ensure_schema, get_recent_readings, close_client
from autonomous.email_alert import send_email_alert

logger = logging.getLogger(__name__)

# Configuration
ABSOLUTE_EMERGENCY_PPM = float(os.getenv("ABSOLUTE_EMERGENCY_PPM", "5000.0"))
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS", "15"))
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))

# Track alerts to avoid duplicates
_last_alert_ts = {}


def detect_static_threshold(readings: list[dict]) -> list[dict]:
    """
    Static threshold detection - no AI, no statistics, just if/else
    """
    anomalies = []
    for r in readings:
        try:
            ppm = float(r.get("methane_ppm", 0))
            if ppm >= ABSOLUTE_EMERGENCY_PPM:
                anomalies.append({
                    "reason": f"Static threshold exceeded: {ppm} >= {ABSOLUTE_EMERGENCY_PPM}",
                    "reading": r
                })
        except (ValueError, TypeError):
            continue
    return anomalies


def run_detection_once(limit: int = 50, send_to: list = None) -> Tuple[bool, str]:
    """
    Run one detection pass using static threshold only
    Returns (alert_sent, report)
    """
    start_time = time.time()
    
    # Get readings
    readings = get_recent_readings(limit=limit) or []
    if not readings:
        return False, "No readings found."
    
    # Detect anomalies
    anomalies = detect_static_threshold(readings)
    if not anomalies:
        return False, "No anomalies detected."
    
    # Filter for cooldown
    new_anomalies = []
    for a in anomalies:
        r = a["reading"]
        trace_id = r.get("trace_id") or r.get("id") or ""
        
        if not trace_id or trace_id not in _last_alert_ts:
            new_anomalies.append(r)
            if trace_id:
                _last_alert_ts[trace_id] = time.time()
        elif (time.time() - _last_alert_ts[trace_id]) >= ALERT_COOLDOWN_SECONDS:
            new_anomalies.append(r)
            _last_alert_ts[trace_id] = time.time()
    
    if not new_anomalies:
        return False, "Anomalies present but in cooldown period."
    
    # Build simple report (no LLM reasoning)
    max_ppm = max([float(r.get("methane_ppm", 0)) for r in new_anomalies])
    report = {
        "system": "Static-Threshold",
        "detection_time_ms": (time.time() - start_time) * 1000,
        "anomalies_count": len(new_anomalies),
        "max_methane_ppm": max_ppm,
        "threshold": ABSOLUTE_EMERGENCY_PPM,
        "decision": "ALERT" if max_ppm >= ABSOLUTE_EMERGENCY_PPM else "SAFE",
        "reasoning": f"Simple rule: methane ({max_ppm} ppm) >= threshold ({ABSOLUTE_EMERGENCY_PPM} ppm)"
    }
    
    report_text = json.dumps(report, indent=2)
    
    # Send email
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []
    
    if not send_to:
        return False, report_text + "\n\nNo recipients configured."
    
    subject = f"⚠️ Static Threshold Alert: {len(new_anomalies)} reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    body = f"Static threshold detection:\n\n{report_text}\n\nRaw readings:\n{json.dumps(new_anomalies, indent=2, default=str)}"
    
    try:
        send_email_alert(subject, body, send_to)
        return True, report_text
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}"


def run_monitoring_loop(limit: int = 50, send_to: list = None):
    """Continuous monitoring loop"""
    logger.info(f"▶️ Starting Static-Threshold monitoring (interval: {CHECK_INTERVAL_SECONDS}s)")
    logger.info(f"   Threshold: {ABSOLUTE_EMERGENCY_PPM} ppm")
    logger.info(f"   System: NO AI, NO agents, static rules only")
    
    try:
        while True:
            try:
                sent, report = run_detection_once(limit=limit, send_to=send_to)
                now = datetime.now(timezone.utc).isoformat()
                logger.info(f"[{now}] Detection pass complete. Alert sent: {sent}")
            except Exception as e:
                logger.error(f"Error during detection: {e}")
            
            time.sleep(CHECK_INTERVAL_SECONDS)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Received KeyboardInterrupt — stopping.")
    finally:
        try:
            close_client()
        except Exception:
            pass
        logger.info("✅ Shutdown complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Launching Static-Threshold Baseline System")
    ensure_schema()
    
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None
    
    run_monitoring_loop(limit=int(os.getenv("DETECTION_LIMIT", "50")), send_to=recipients)
