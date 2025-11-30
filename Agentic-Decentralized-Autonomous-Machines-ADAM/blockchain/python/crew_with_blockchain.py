"""
crew_with_blockchain.py - Updated crew.py with blockchain governance integration

This shows how to integrate blockchain validation into the existing crew.py file.

Key changes:
1. Initialize BlockchainIntegrator on startup
2. Validate crew formation on blockchain (for critical events)
3. Log critical decisions with consensus validation
4. Mark actions as executed on-chain

For non-critical events (< 5000 ppm), blockchain is bypassed to save gas costs.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import existing modules
from data_layer.weaviate_client import ensure_schema, get_recent_readings, close_client
from autonomous.reasoning_agent import call_chatgpt_reasoner
from autonomous.email_alert import send_email_alert

# ✅ NEW: Import blockchain integration
from blockchain.python.crew_blockchain_integration import CrewBlockchainIntegrator

logger = logging.getLogger(__name__)

# Configuration
ABSOLUTE_EMERGENCY_PPM = float(os.getenv("ABSOLUTE_EMERGENCY_PPM", "5000.0"))
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS", "15"))
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))

# ✅ NEW: Initialize blockchain integrator (global instance)
blockchain_integrator = None

def initialize_blockchain():
    """Initialize blockchain integration on startup"""
    global blockchain_integrator
    
    try:
        blockchain_integrator = CrewBlockchainIntegrator(
            agent_role=3  # Coordinator role
        )
        
        if blockchain_integrator.enable_blockchain:
            thresholds = blockchain_integrator.get_governance_thresholds()
            logger.info(f"✅ Blockchain governance enabled")
            logger.info(f"   Critical threshold: {thresholds['critical']} ppm")
            logger.info(f"   Consensus required: {thresholds['consensus_percentage']}%")
        else:
            logger.info("⚠️ Blockchain disabled - running without on-chain governance")
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize blockchain: {e}")
        logger.warning("⚠️ Continuing without blockchain governance")
        blockchain_integrator = None


@CrewBase
class MethaneMonitoringCrew:
    """CrewAI orchestration with blockchain governance"""
    
    agents: List[Agent]
    tasks: List[Task]
    
    # Define agents (same as before)
    @agent
    def sensor_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("sensor_agent", {}), verbose=True)
    
    @agent
    def validator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("validator_agent", {}), verbose=True)
    
    @agent
    def decision_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("decision_agent", {}), verbose=True)
    
    @agent
    def coordinator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("coordinator_agent", {}), verbose=True)
    
    # Define tasks (same as before)
    @task
    def collect_data_task(self) -> Task:
        tc = TASKS_CONFIG.get("collect_data_task", {})
        return Task(
            description=tc.get("description", "Collect data"),
            agent=self.sensor_agent(),
            expected_output=tc.get("expected_output", "")
        )
    
    @task
    def validate_data_task(self) -> Task:
        tc = TASKS_CONFIG.get("validate_data_task", {})
        return Task(
            description=tc.get("description", "Validate data"),
            agent=self.validator_agent(),
            expected_output=tc.get("expected_output", "")
        )
    
    @task
    def analyze_task(self) -> Task:
        tc = TASKS_CONFIG.get("analyze_task", {})
        return Task(
            description=tc.get("description", "Analyze data"),
            agent=self.decision_agent(),
            expected_output=tc.get("expected_output", "")
        )
    
    @task
    def report_task(self) -> Task:
        tc = TASKS_CONFIG.get("report_task", {})
        return Task(
            description=tc.get("description", "Report"),
            agent=self.coordinator_agent(),
            expected_output=tc.get("expected_output", ""),
            output_file="methane_alert_report.md"
        )
    
    @crew
    def crew(self) -> Crew:
        ensure_schema()
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )


def detect_anomalies_from_readings(
    readings: list[dict],
    absolute_threshold: float = ABSOLUTE_EMERGENCY_PPM,
) -> list[dict]:
    """Detect anomalies based on absolute threshold"""
    anomalies = []
    for r in readings:
        ppm = float(r.get("methane_ppm", 0))
        if ppm >= absolute_threshold:
            anomalies.append({
                "reason": f"ppm >= {absolute_threshold}",
                "reading": r
            })
    return anomalies


# ✅ NEW: Blockchain-validated detection and notification
def run_detection_with_blockchain_validation(
    limit: int = 50,
    send_to: list = None
) -> Tuple[bool, str, Dict]:
    """
    Run detection with blockchain validation for critical decisions
    
    Returns:
        (alert_sent, report_text, blockchain_info)
    """
    blockchain_info = {
        "crew_id": None,
        "decision_id": None,
        "consensus_passed": None,
        "transactions": []
    }
    
    # Get recent readings
    readings = get_recent_readings(limit=limit) or []
    if not readings:
        return False, "No readings found.", blockchain_info
    
    # Detect anomalies
    anomalies = detect_anomalies_from_readings(readings)
    if not anomalies:
        return False, "No anomalies found.", blockchain_info
    
    # Extract methane level
    max_ppm = max([float(a["reading"].get("methane_ppm", 0)) for a in anomalies])
    
    # ✅ NEW: Validate crew formation on blockchain (if critical)
    crew_id = None
    if blockchain_integrator and blockchain_integrator.enable_blockchain:
        if max_ppm >= ABSOLUTE_EMERGENCY_PPM:
            logger.info(f"🔗 Critical event detected ({max_ppm} ppm) - forming crew on blockchain...")
            
            # Get crew member addresses (from environment or config)
            crew_members = _get_crew_member_addresses()
            
            event_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node_id": anomalies[0]["reading"].get("node_id", "unknown"),
                "methane_ppm": max_ppm
            }
            
            success, crew_id, tx_hash = blockchain_integrator.validate_crew_formation(
                event_data=event_data,
                crew_members=crew_members,
                methane_ppm=max_ppm
            )
            
            if success and crew_id:
                blockchain_info["crew_id"] = crew_id
                blockchain_info["transactions"].append({"type": "crew_formation", "hash": tx_hash})
                logger.info(f"✅ Crew {crew_id} formed on blockchain")
            else:
                logger.warning("⚠️ Blockchain crew formation failed - continuing without on-chain validation")
    
    # Call LLM reasoner
    try:
        anomalies_readings = [a["reading"] for a in anomalies]
        report = call_chatgpt_reasoner(anomalies_readings, context_readings=readings)
        report_text = json.dumps(report, indent=2, default=str) if not isinstance(report, str) else report
    except Exception as e:
        report_text = f"LLM reasoner failed: {e}"
        report = {"severity": "critical", "explanation": report_text}
    
    # ✅ NEW: Validate critical decision on blockchain
    decision_id = None
    if blockchain_integrator and blockchain_integrator.enable_blockchain and crew_id:
        if max_ppm >= ABSOLUTE_EMERGENCY_PPM:
            logger.info(f"🔗 Validating critical decision on blockchain...")
            
            crew_members = _get_crew_member_addresses()
            
            consensus_passed, decision_id, tx_hash = blockchain_integrator.validate_critical_decision(
                crew_id=crew_id,
                decision_data=report,
                crew_members=crew_members,
                methane_ppm=max_ppm
            )
            
            if decision_id:
                blockchain_info["decision_id"] = decision_id
                blockchain_info["consensus_passed"] = consensus_passed
                blockchain_info["transactions"].append({"type": "decision_log", "hash": tx_hash})
                
                if consensus_passed:
                    logger.info(f"✅ Consensus PASSED for decision {decision_id}")
                else:
                    logger.warning(f"⚠️ Consensus not yet reached for decision {decision_id}")
    
    # Send alert
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []
    
    if not send_to:
        return False, report_text + "\n\nNo recipients configured.", blockchain_info
    
    subject = f"⚠️ Methane Alert: {len(anomalies)} reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    
    # ✅ NEW: Include blockchain info in alert
    blockchain_status = ""
    if crew_id:
        blockchain_status = f"\n\n🔗 Blockchain Governance:\n"
        blockchain_status += f"   Crew ID: {crew_id}\n"
        if decision_id:
            blockchain_status += f"   Decision ID: {decision_id}\n"
            blockchain_status += f"   Consensus: {'✅ PASSED' if blockchain_info['consensus_passed'] else '⏳ Pending'}\n"
        if blockchain_info["transactions"]:
            blockchain_status += f"   Transactions: {len(blockchain_info['transactions'])}\n"
    
    body = f"Anomalies detected (threshold {ABSOLUTE_EMERGENCY_PPM} ppm):\n\n"
    body += f"{report_text}\n\n"
    body += f"Raw anomalies:\n{json.dumps(anomalies_readings, indent=2, default=str)}"
    body += blockchain_status
    
    try:
        send_email_alert(subject, body, send_to)
        
        # ✅ NEW: Mark action as executed on blockchain
        if blockchain_integrator and decision_id:
            logger.info(f"🔗 Marking action executed on blockchain...")
            tx_hash = blockchain_integrator.mark_action_executed(
                decision_id=decision_id,
                action_type="email_alert",
                success=True
            )
            if tx_hash:
                blockchain_info["transactions"].append({"type": "mark_executed", "hash": tx_hash})
        
        return True, report_text, blockchain_info
    
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}", blockchain_info


def _get_crew_member_addresses() -> List[str]:
    """
    Get crew member addresses from environment
    
    In production, each node would report its own agent addresses.
    For now, we'll use environment variables.
    """
    # Try to get from environment
    node_num = os.getenv("NODE_NUMBER", "1")
    
    addresses = [
        os.getenv(f"NODE{node_num}_SENSOR_ADDRESS"),
        os.getenv(f"NODE{node_num}_AGGREGATOR_ADDRESS"),
        os.getenv(f"NODE{node_num}_DECISION_ADDRESS"),
        os.getenv(f"NODE{node_num}_COORDINATOR_ADDRESS")
    ]
    
    # Filter out None values
    addresses = [addr for addr in addresses if addr]
    
    # If not enough addresses, use dummy addresses for testing
    while len(addresses) < 4:
        addresses.append(f"0x{'0' * 39}{len(addresses) + 1}")
    
    return addresses


def run_monitoring_loop(limit: int = 50, send_to: list = None):
    """Continuous monitoring loop with blockchain integration"""
    logger.info(f"▶️ Starting continuous monitor with blockchain governance")
    logger.info(f"   Interval: {CHECK_INTERVAL_SECONDS}s")
    logger.info(f"   Threshold: {ABSOLUTE_EMERGENCY_PPM} ppm")
    
    try:
        while True:
            try:
                sent, report, blockchain_info = run_detection_with_blockchain_validation(
                    limit=limit,
                    send_to=send_to
                )
                
                now = datetime.now(timezone.utc).isoformat()
                status = f"Alert sent: {sent}"
                
                if blockchain_info.get("crew_id"):
                    status += f" | Crew ID: {blockchain_info['crew_id']}"
                if blockchain_info.get("decision_id"):
                    status += f" | Decision ID: {blockchain_info['decision_id']}"
                
                logger.info(f"[{now}] Detection pass complete. {status}")
            
            except Exception as e:
                logger.error(f"Error during detection pass: {e}")
            
            time.sleep(CHECK_INTERVAL_SECONDS)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Received KeyboardInterrupt — stopping monitoring loop.")
    
    finally:
        try:
            close_client()
        except Exception:
            pass
        logger.info("✅ Clean shutdown complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Launching ADAM with Blockchain Governance")
    
    # ✅ NEW: Initialize blockchain on startup
    initialize_blockchain()
    
    # Initialize crew
    crew_instance = MethaneMonitoringCrew()
    _ = crew_instance.crew().kickoff()
    logger.info("✅ Crew startup tasks completed.")
    
    # Build recipients list
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None
    
    # Start continuous monitoring with blockchain validation
    logger.info("▶️ Entering continuous detection loop with blockchain governance...")
    run_monitoring_loop(
        limit=int(os.getenv("DETECTION_LIMIT", "50")),
        send_to=recipients
    )
