"""
crew_no_llm.py - ADAM without LLM Reasoning

Uses CrewAI agents BUT replaces GPT-4 reasoning with simple statistical rules.
Tests impact of LLM-based adaptive reasoning vs static logic.

For paper comparison: ADAM-No-LLM ablation.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Tuple
from statistics import mean, stdev

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from data_layer.weaviate_client import ensure_schema, get_recent_readings, close_client
from autonomous.email_alert import send_email_alert

logger = logging.getLogger(__name__)

# Configuration
ABSOLUTE_EMERGENCY_PPM = float(os.getenv("ABSOLUTE_EMERGENCY_PPM", "5000.0"))
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS", "15"))
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))

# Simplified configs (no LLM calls in agents)
AGENTS_CONFIG = {
    "sensor_agent": {"role": "Sensor", "goal": "Collect data", "backstory": "Sensor"},
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

_last_alert_ts = {}


@CrewBase
class NoLLMCrew:
    """CrewAI without LLM reasoning - uses statistical rules"""
    
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
        ensure_schema()
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=False)


def statistical_reasoning(anomalies: list[dict], context: list[dict]) -> dict:
    """
    Replace LLM reasoning with simple statistical analysis
    No GPT-4 API calls, just mean/stdev/threshold logic
    """
    if not anomalies:
        return {"decision": "SAFE", "reasoning": "No anomalies"}
    
    # Extract methane values
    anomaly_ppms = [float(a.get("methane_ppm", 0)) for a in anomalies]
    context_ppms = [float(r.get("methane_ppm", 0)) for r in context[-50:]]  # last 50
    
    max_ppm = max(anomaly_ppms)
    mean_ppm = mean(context_ppms) if context_ppms else 0
    std_ppm = stdev(context_ppms) if len(context_ppms) > 1 else 0
    
    # Simple rules (no LLM intelligence)
    if max_ppm >= ABSOLUTE_EMERGENCY_PPM:
        decision = "CRITICAL"
        severity = "critical"
        action = "Send immediate alert and notify emergency services"
        reasoning = f"Max {max_ppm} ppm exceeds emergency threshold {ABSOLUTE_EMERGENCY_PPM} ppm"
    elif max_ppm >= (mean_ppm + 3 * std_ppm):
        decision = "WARNING"
        severity = "warning"
        action = "Monitor closely, prepare for escalation"
        reasoning = f"Reading {max_ppm} ppm is {((max_ppm - mean_ppm) / std_ppm):.1f} std devs above mean"
    else:
        decision = "SAFE"
        severity = "normal"
        action = "Continue normal monitoring"
        reasoning = f"Reading {max_ppm} ppm within expected range (mean: {mean_ppm:.1f}, std: {std_ppm:.1f})"
    
    return {
        "system": "ADAM-No-LLM",
        "decision": decision,
        "severity": severity,
        "action": action,
        "reasoning": reasoning,
        "statistics": {
            "max_ppm": max_ppm,
            "mean_ppm": round(mean_ppm, 2),
            "std_ppm": round(std_ppm, 2),
            "threshold": ABSOLUTE_EMERGENCY_PPM
        }
    }


def detect_anomalies(readings: list[dict]) -> list[dict]:
    """Detect anomalies based on absolute threshold"""
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
    """Run detection with statistical reasoning instead of LLM"""
    start_time = time.time()
    
    readings = get_recent_readings(limit=limit) or []
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
    
    # Use statistical reasoning (NO LLM)
    report = statistical_reasoning(new_anomalies, readings)
    report["detection_time_ms"] = (time.time() - start_time) * 1000
    report["anomalies_count"] = len(new_anomalies)
    
    report_text = json.dumps(report, indent=2)
    
    # Send email
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []
    
    if not send_to:
        return False, report_text + "\n\nNo recipients."
    
    subject = f"⚠️ No-LLM Alert: {len(new_anomalies)} reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    body = f"Statistical reasoning (no LLM):\n\n{report_text}\n\nReadings:\n{json.dumps(new_anomalies, indent=2, default=str)}"
    
    try:
        send_email_alert(subject, body, send_to)
        return True, report_text
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}"


def run_monitoring_loop(limit: int = 50, send_to: list = None):
    """Continuous monitoring with statistical reasoning"""
    logger.info(f"▶️ Starting ADAM-No-LLM monitoring")
    logger.info(f"   System: CrewAI agents + Statistical rules (NO GPT-4)")
    
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
    
    logger.info("🚀 Launching ADAM-No-LLM (Statistical Reasoning)")
    crew_instance = NoLLMCrew()
    _ = crew_instance.crew().kickoff()
    logger.info("✅ Crew initialized.")
    
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None
    
    run_monitoring_loop(limit=int(os.getenv("DETECTION_LIMIT", "50")), send_to=recipients)