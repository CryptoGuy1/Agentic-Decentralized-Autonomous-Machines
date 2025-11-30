"""
crew_no_weaviate.py - ADAM without Vector Database

Uses file-based storage instead of Weaviate vector database.
Tests impact of efficient vector search vs traditional file storage.

For paper comparison: ADAM-No-Weaviate ablation.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Tuple, List, Dict
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from autonomous.reasoning_agent import call_chatgpt_reasoner
from autonomous.email_alert import send_email_alert

logger = logging.getLogger(__name__)

# Configuration
ABSOLUTE_EMERGENCY_PPM = float(os.getenv("ABSOLUTE_EMERGENCY_PPM", "5000.0"))
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS", "15"))
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))

# File-based storage
STORAGE_DIR = Path("data/readings")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
READINGS_FILE = STORAGE_DIR / "readings.jsonl"

_last_alert_ts = {}


# ===== FILE-BASED STORAGE (replaces Weaviate) =====

def store_reading(reading: dict):
    """Store reading to JSONL file"""
    reading['timestamp'] = reading.get('timestamp', datetime.now(timezone.utc).isoformat())
    reading['stored_at'] = time.time()
    
    with open(READINGS_FILE, 'a') as f:
        f.write(json.dumps(reading) + '\n')


def get_recent_readings(limit: int = 50) -> List[Dict]:
    """Get recent readings from file (no vector search)"""
    if not READINGS_FILE.exists():
        return []
    
    readings = []
    with open(READINGS_FILE, 'r') as f:
        for line in f:
            try:
                readings.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    # Return most recent (simple time-based sorting, no vector search)
    readings.sort(key=lambda r: r.get('stored_at', 0), reverse=True)
    return readings[:limit]


def search_similar_readings(query_ppm: float, limit: int = 10) -> List[Dict]:
    """
    Simple similarity search (no vector database).
    Just finds readings with similar PPM values (±20%).
    Much slower and less accurate than Weaviate HNSW.
    """
    all_readings = get_recent_readings(limit=500)
    
    threshold = query_ppm * 0.2  # ±20% range
    similar = []
    
    for r in all_readings:
        try:
            ppm = float(r.get("methane_ppm", 0))
            if abs(ppm - query_ppm) <= threshold:
                similar.append(r)
        except (ValueError, TypeError):
            continue
    
    return similar[:limit]


# ===== CREWAI SETUP =====

AGENTS_CONFIG = {
    "sensor_agent": {"role": "Sensor", "goal": "Collect data", "backstory": "Sensor (no vector DB)"},
    "validator_agent": {"role": "Validator", "goal": "Validate", "backstory": "Validator"},
    "decision_agent": {"role": "Decision", "goal": "Decide", "backstory": "Decision"},
    "coordinator_agent": {"role": "Coordinator", "goal": "Coordinate", "backstory": "Coordinator"}
}

TASKS_CONFIG = {
    "collect_data_task": {"description": "Collect", "expected_output": "Data"},
    "validate_data_task": {"description": "Validate", "expected_output": "Valid"},
    "analyze_task": {"description": "Analyze", "expected_output": "Analysis"},
    "report_task": {"description": "Report", "expected_output": "Report"}
}


@CrewBase
class NoWeaviateCrew:
    """CrewAI with file-based storage instead of Weaviate"""
    
    @agent
    def sensor_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["sensor_agent"], verbose=False)
    
    @agent
    def validator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["validator_agent"], verbose=False)
    
    @agent
    def decision_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["decision_agent"], verbose=False)
    
    @agent
    def coordinator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["coordinator_agent"], verbose=False)
    
    @task
    def collect_data_task(self) -> Task:
        return Task(description="Collect data", agent=self.sensor_agent(), expected_output="Data")
    
    @task
    def validate_data_task(self) -> Task:
        return Task(description="Validate", agent=self.validator_agent(), expected_output="Valid")
    
    @task
    def analyze_task(self) -> Task:
        return Task(description="Analyze", agent=self.decision_agent(), expected_output="Analysis")
    
    @task
    def report_task(self) -> Task:
        return Task(description="Report", agent=self.coordinator_agent(), expected_output="Report")
    
    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=False)


def detect_anomalies(readings: list[dict]) -> list[dict]:
    """Detect anomalies"""
    anomalies = []
    for r in readings:
        try:
            ppm = float(r.get("methane_ppm", 0))
            if ppm >= ABSOLUTE_EMERGENCY_PPM:
                anomalies.append(r)
        except (ValueError, TypeError):
            continue
    return anomalies


def run_detection_once(limit: int = 50, send_to: list = None) -> Tuple[bool, str]:
    """Run detection with file-based storage (no Weaviate)"""
    start_time = time.time()
    
    # Read from file (slower than Weaviate)
    readings = get_recent_readings(limit=limit)
    if not readings:
        return False, "No readings found."
    
    anomalies = detect_anomalies(readings)
    if not anomalies:
        return False, "No anomalies detected."
    
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
    
    # Call LLM reasoner
    try:
        context = {"anomalies": new_anomalies, "recent_readings": readings}
        report = call_chatgpt_reasoner(new_anomalies, context_readings=readings)
        report_dict = report if isinstance(report, dict) else {"reasoning": str(report)}
    except Exception as e:
        logger.error(f"LLM error: {e}")
        report_dict = {"reasoning": f"LLM failed: {e}"}
    
    report_dict.update({
        "system": "ADAM-No-Weaviate",
        "storage": "File-based (JSONL)",
        "detection_time_ms": (time.time() - start_time) * 1000,
        "anomalies_count": len(new_anomalies),
        "note": "Using file storage instead of Weaviate vector DB"
    })
    
    report_text = json.dumps(report_dict, indent=2)
    
    # Send email
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []
    
    if not send_to:
        return False, report_text + "\n\nNo recipients."
    
    subject = f"⚠️ No-Weaviate Alert: {len(new_anomalies)} reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    body = f"File-based storage (no vector DB):\n\n{report_text}\n\nReadings:\n{json.dumps(new_anomalies, indent=2, default=str)}"
    
    try:
        send_email_alert(subject, body, send_to)
        return True, report_text
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}"


def run_monitoring_loop(limit: int = 50, send_to: list = None):
    """Continuous monitoring with file-based storage"""
    logger.info(f"▶️ Starting ADAM-No-Weaviate monitoring")
    logger.info(f"   System: CrewAI + File storage (NO vector database)")
    logger.info(f"   Storage: {READINGS_FILE}")
    
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
        logger.info("✅ Shutdown complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Launching ADAM-No-Weaviate (File-based Storage)")
    crew_instance = NoWeaviateCrew()
    _ = crew_instance.crew().kickoff()
    logger.info("✅ Crew initialized.")
    
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None
    
    run_monitoring_loop(limit=int(os.getenv("DETECTION_LIMIT", "50")), send_to=recipients)

