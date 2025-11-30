"""
crew_cloud_only.py - Cloud-Only Baseline

All processing happens in centralized cloud - no edge intelligence.
Tests latency impact of cloud round-trip vs edge processing.

For paper comparison: Cloud-Only baseline system.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Tuple

from data_layer.weaviate_client import ensure_schema, get_recent_readings, close_client
from autonomous.reasoning_agent import call_chatgpt_reasoner
from autonomous.email_alert import send_email_alert

logger = logging.getLogger(__name__)

# Configuration
ABSOLUTE_EMERGENCY_PPM = float(os.getenv("ABSOLUTE_EMERGENCY_PPM", "5000.0"))
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS", "15"))
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))

# Cloud processing adds latency (simulate network round-trip)
CLOUD_LATENCY_MS = float(os.getenv("CLOUD_LATENCY_MS", "150"))  # Average cloud round-trip

_last_alert_ts = {}


def simulate_cloud_processing(readings: list[dict]) -> dict:
    """
    Simulate sending data to cloud for processing.
    Adds network latency to represent cloud round-trip time.
    
    In production, this would be:
    - POST data to cloud API endpoint
    - Wait for cloud to process
    - Receive decision from cloud
    """
    start_time = time.time()
    
    # Simulate network latency (upload)
    time.sleep(CLOUD_LATENCY_MS / 2000)  # Half for upload
    
    # Cloud processing (happens remotely)
    # In real implementation, this would be an HTTP request
    anomalies = [r for r in readings if float(r.get("methane_ppm", 0)) >= ABSOLUTE_EMERGENCY_PPM]
    
    if not anomalies:
        result = {
            "decision": "SAFE",
            "reasoning": "No anomalies detected in cloud processing",
            "cloud_processing": True
        }
    else:
        # Cloud calls LLM (happens remotely)
        try:
            llm_report = call_chatgpt_reasoner(anomalies, context_readings=readings)
            result = llm_report if isinstance(llm_report, dict) else {"reasoning": str(llm_report)}
            result["cloud_processing"] = True
        except Exception as e:
            logger.error(f"Cloud LLM error: {e}")
            result = {
                "reasoning": f"Cloud LLM failed: {e}",
                "cloud_processing": True
            }
    
    # Simulate network latency (download)
    time.sleep(CLOUD_LATENCY_MS / 2000)  # Half for download
    
    # Add cloud processing metadata
    result.update({
        "system": "Cloud-Only",
        "processing_location": "Centralized Cloud",
        "total_latency_ms": (time.time() - start_time) * 1000,
        "network_latency_ms": CLOUD_LATENCY_MS,
        "note": "All processing in cloud - no edge intelligence"
    })
    
    return result


def run_detection_once(limit: int = 50, send_to: list = None) -> Tuple[bool, str]:
    """
    Run detection with cloud processing (no edge intelligence)
    """
    # Edge device only collects data
    readings = get_recent_readings(limit=limit) or []
    if not readings:
        return False, "No readings found."
    
    # All processing happens in cloud
    report = simulate_cloud_processing(readings)
    
    if report.get("decision") == "SAFE":
        return False, json.dumps(report, indent=2)
    
    # Extract anomalies from report
    anomalies = [r for r in readings if float(r.get("methane_ppm", 0)) >= ABSOLUTE_EMERGENCY_PPM]
    
    # Filter for cooldown
    new_anomalies = []
    for r in anomalies:
        trace_id = r.get("trace_id") or r.get("id") or ""
        if not trace_id or trace_id not in _last_alert_ts:
            new_anomalies.append(r)
            if trace_id:
                _last_alert_ts[trace_id] = time.time()
        elif (time.time() - _last_alert_ts[trace_id]) >= ALERT_COOLDOWN_SECONDS:
            new_anomalies.append(r)
            _last_alert_ts[trace_id] = time.time()
    
    if not new_anomalies:
        return False, "Anomalies in cooldown period."
    
    report_text = json.dumps(report, indent=2)
    
    # Send email (edge device can handle this)
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []
    
    if not send_to:
        return False, report_text + "\n\nNo recipients."
    
    subject = f"⚠️ Cloud-Only Alert: {len(new_anomalies)} reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    body = f"Cloud processing result:\n\n{report_text}\n\nReadings:\n{json.dumps(new_anomalies, indent=2, default=str)}"
    
    try:
        send_email_alert(subject, body, send_to)
        return True, report_text
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}"


def run_monitoring_loop(limit: int = 50, send_to: list = None):
    """Continuous monitoring with cloud processing"""
    logger.info(f"▶️ Starting Cloud-Only monitoring")
    logger.info(f"   System: Centralized cloud processing")
    logger.info(f"   Network latency: {CLOUD_LATENCY_MS} ms (simulated)")
    logger.info(f"   Edge: Data collection only, NO intelligence")
    
    try:
        while True:
            try:
                sent, report = run_detection_once(limit=limit, send_to=send_to)
                now = datetime.now(timezone.utc).isoformat()
                logger.info(f"[{now}] Detection complete. Alert sent: {sent}")
            except Exception as e:
                logger.error(f"Error: {e}")
            
            time.sleep(CHECK_INTERVAL_SECONDS)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Stopping.")
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
    
    logger.info("🚀 Launching Cloud-Only Baseline")
    logger.info(f"   Simulating cloud latency: {CLOUD_LATENCY_MS} ms")
    ensure_schema()
    
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None
    
    run_monitoring_loop(limit=int(os.getenv("DETECTION_LIMIT", "50")), send_to=recipients)
