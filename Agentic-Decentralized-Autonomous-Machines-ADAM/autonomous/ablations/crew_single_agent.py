"""
crew_single_agent.py - Single-Agent Baseline

One monolithic agent does everything - no crew coordination, no specialization.
Tests impact of multi-agent collaboration vs single-agent approach.

For paper comparison: Single-Agent baseline.
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

_last_alert_ts = {}


class MonolithicAgent:
    """
    Single agent that handles:
    - Data collection
    - Validation
    - Aggregation
    - Decision-making
    - Alerting
    
    No crew coordination, no agent specialization.
    """
    
    def __init__(self):
        self.name = "Monolithic-Agent"
        logger.info(f"🤖 {self.name} initialized (no crew)")
    
    def process_event(self, readings: list[dict]) -> dict:
        """Single agent processes everything"""
        start_time = time.time()
        
        # Step 1: Collect data (sensor agent role)
        if not readings:
            return {"decision": "NO_DATA", "reason": "No readings available"}
        
        # Step 2: Validate data (validator agent role)
        valid_readings = [r for r in readings if self._validate_reading(r)]
        if not valid_readings:
            return {"decision": "INVALID_DATA", "reason": "All readings invalid"}
        
        # Step 3: Aggregate data (aggregator agent role)
        aggregated = self._aggregate_readings(valid_readings)
        
        # Step 4: Detect anomalies (decision agent role)
        anomalies = [r for r in valid_readings if float(r.get("methane_ppm", 0)) >= ABSOLUTE_EMERGENCY_PPM]
        
        if not anomalies:
            return {"decision": "SAFE", "reason": "No anomalies detected"}
        
        # Step 5: Call LLM for reasoning (decision agent role)
        try:
            context = {"anomalies": anomalies, "recent_readings": valid_readings, "aggregated": aggregated}
            llm_report = call_chatgpt_reasoner(anomalies, context_readings=valid_readings)
            report = llm_report if isinstance(llm_report, dict) else {"reasoning": str(llm_report)}
        except Exception as e:
            logger.error(f"LLM error: {e}")
            report = {"reasoning": f"LLM failed: {e}"}
        
        # Step 6: Coordinate response (coordinator agent role)
        report.update({
            "system": "Single-Agent",
            "agent": self.name,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "anomalies_count": len(anomalies),
            "note": "No crew coordination - single agent handled all tasks"
        })
        
        return report
    
    def _validate_reading(self, reading: dict) -> bool:
        """Simple validation"""
        try:
            ppm = float(reading.get("methane_ppm", 0))
            return 0 <= ppm <= 100000  # Reasonable range
        except (ValueError, TypeError):
            return False
    
    def _aggregate_readings(self, readings: list[dict]) -> dict:
        """Simple aggregation"""
        ppms = [float(r.get("methane_ppm", 0)) for r in readings]
        if not ppms:
            return {}
        
        from statistics import mean, stdev
        return {
            "mean_ppm": round(mean(ppms), 2),
            "max_ppm": round(max(ppms), 2),
            "std_ppm": round(stdev(ppms), 2) if len(ppms) > 1 else 0,
            "count": len(ppms)
        }


def run_detection_once(limit: int = 50, send_to: list = None) -> Tuple[bool, str]:
    """Run detection with single agent (no crew)"""
    agent = MonolithicAgent()
    
    readings = get_recent_readings(limit=limit) or []
    if not readings:
        return False, "No readings found."
    
    # Single agent processes everything
    report = agent.process_event(readings)
    
    if report.get("decision") in ["SAFE", "NO_DATA", "INVALID_DATA"]:
        return False, json.dumps(report, indent=2)
    
    # Filter for cooldown
    anomalies = [r for r in readings if float(r.get("methane_ppm", 0)) >= ABSOLUTE_EMERGENCY_PPM]
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
    
    # Send email
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []
    
    if not send_to:
        return False, report_text + "\n\nNo recipients."
    
    subject = f"⚠️ Single-Agent Alert: {len(new_anomalies)} reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    body = f"Single agent detection:\n\n{report_text}\n\nReadings:\n{json.dumps(new_anomalies, indent=2, default=str)}"
    
    try:
        send_email_alert(subject, body, send_to)
        return True, report_text
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}"


def run_monitoring_loop(limit: int = 50, send_to: list = None):
    """Continuous monitoring with single agent"""
    logger.info(f"▶️ Starting Single-Agent monitoring")
    logger.info(f"   System: ONE agent, no crew coordination")
    
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
    
    logger.info("🚀 Launching Single-Agent Baseline")
    ensure_schema()
    
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None
    
    run_monitoring_loop(limit=int(os.getenv("DETECTION_LIMIT", "50")), send_to=recipients)

