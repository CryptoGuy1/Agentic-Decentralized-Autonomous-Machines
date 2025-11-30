"""
crew_blockchain_integration.py - Connects CrewAI agents to blockchain governance

This module extends the existing crew.py to add blockchain validation for:
1. Crew formation events
2. Critical anomaly decisions (methane >= 5000 ppm)
3. Action execution (alerts, emergency shutdown)
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from web3 import Web3

from blockchain.python.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class CrewBlockchainIntegrator:
    """
    Integrates blockchain governance with CrewAI agent crews
    """
    
    # Decision types
    DECISION_TYPE_CREW_FORMATION = 0
    DECISION_TYPE_ANOMALY_DETECTION = 1
    DECISION_TYPE_ACTION_EXECUTION = 2
    
    # Severity levels
    SEVERITY_SAFE = 0
    SEVERITY_WARNING = 1
    SEVERITY_CRITICAL = 2
    
    def __init__(
        self,
        agent_private_key: str = None,
        agent_address: str = None,
        node_address: str = None,
        agent_role: int = 3,  # Default: Coordinator
        enable_blockchain: bool = True
    ):
        """
        Initialize blockchain integration
        
        Args:
            agent_private_key: Private key for this agent
            agent_address: Ethereum address of this agent
            node_address: Ethereum address of Raspberry Pi node
            agent_role: 0=Sensor, 1=Aggregator, 2=Decision, 3=Coordinator
            enable_blockchain: If False, runs in simulation mode
        """
        self.enable_blockchain = enable_blockchain and os.getenv("ENABLE_BLOCKCHAIN", "true").lower() == "true"
        
        if not self.enable_blockchain:
            logger.warning("⚠️ Blockchain integration DISABLED - running in simulation mode")
            self.client = None
            return
        
        # Load configuration
        self.agent_private_key = agent_private_key or os.getenv("AGENT_PRIVATE_KEY")
        self.agent_address = agent_address or os.getenv("AGENT_ADDRESS")
        self.node_address = node_address or os.getenv("NODE_ADDRESS")
        self.agent_role = agent_role
        
        if not self.agent_private_key:
            raise ValueError("AGENT_PRIVATE_KEY environment variable required")
        
        # Initialize blockchain client
        try:
            self.client = BlockchainClient(
                private_key=self.agent_private_key
            )
            logger.info(f"✅ Blockchain client initialized for agent: {self.client.address}")
            
            # Verify agent is registered
            if not self.client.is_active_agent(self.client.address):
                logger.warning(f"⚠️ Agent {self.client.address} not registered on-chain!")
                logger.warning("   Run: python blockchain/scripts/register_agents.py")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize blockchain client: {e}")
            logger.warning("⚠️ Falling back to simulation mode")
            self.enable_blockchain = False
            self.client = None
    
    # =========================
    # Crew Formation
    # =========================
    
    def validate_crew_formation(
        self,
        event_data: Dict,
        crew_members: List[str],
        methane_ppm: float
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate and log crew formation on blockchain
        
        Args:
            event_data: Event information (timestamp, node_id, etc.)
            crew_members: List of agent addresses in crew
            methane_ppm: Methane concentration that triggered formation
        
        Returns:
            (success, crew_id, transaction_hash)
        """
        if not self.enable_blockchain:
            logger.debug("Blockchain disabled - simulating crew formation")
            return (True, None, None)
        
        try:
            # Generate event ID (for deduplication)
            event_id = self._generate_event_id(event_data)
            
            # Form crew on-chain
            logger.info(f"🔗 Forming crew on blockchain for event {event_id.hex()[:8]}...")
            tx_hash, crew_id = self.client.form_crew(
                event_id=event_id,
                members=crew_members,
                methane_ppm=int(methane_ppm)
            )
            
            logger.info(f"✅ Crew {crew_id} formed on-chain (tx: {tx_hash[:10]}...)")
            return (True, crew_id, tx_hash)
        
        except Exception as e:
            logger.error(f"❌ Failed to form crew on blockchain: {e}")
            return (False, None, None)
    
    # =========================
    # Decision Validation
    # =========================
    
    def validate_critical_decision(
        self,
        crew_id: int,
        decision_data: Dict,
        crew_members: List[str],
        methane_ppm: float
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate critical decision (methane >= 5000 ppm) through blockchain consensus
        
        Args:
            crew_id: On-chain crew ID
            decision_data: Decision information from LLM reasoner
            crew_members: List of agent addresses who should vote
            methane_ppm: Methane concentration
        
        Returns:
            (consensus_passed, decision_id, transaction_hash)
        """
        if not self.enable_blockchain:
            logger.debug("Blockchain disabled - simulating decision validation")
            return (True, None, None)
        
        # Check if critical
        if not self.client.is_critical(int(methane_ppm)):
            logger.debug(f"Methane {methane_ppm} ppm not critical - skipping blockchain validation")
            return (True, None, None)
        
        try:
            # Generate decision hash
            decision_hash = self._generate_decision_hash(decision_data)
            
            # Determine severity
            severity = self._map_severity(decision_data.get("severity", "critical"))
            
            # Sign decision with this agent
            signature = self.client.sign_decision(decision_hash)
            
            # Collect signatures from other crew members (in real system)
            # For now, we'll assume coordinator collects all signatures
            signatures = [signature]  # TODO: Implement multi-agent signature collection
            voters = [self.client.address]  # TODO: Collect from all crew members
            
            # Log decision on-chain
            logger.info(f"🔗 Logging critical decision on blockchain...")
            tx_hash, decision_id = self.client.log_decision(
                crew_id=crew_id,
                decision_hash=decision_hash,
                decision_type=self.DECISION_TYPE_ANOMALY_DETECTION,
                severity=severity,
                methane_ppm=int(methane_ppm),
                voters=voters,
                signatures=signatures,
                notes=decision_data.get("explanation", "")[:200]  # Limit to 200 chars
            )
            
            logger.info(f"✅ Decision {decision_id} logged on-chain (tx: {tx_hash[:10]}...)")
            
            # Request consensus validation
            proposal_hash = decision_hash
            logger.info(f"🔗 Requesting consensus validation...")
            consensus_tx, request_id = self.client.request_consensus(
                crew_id=crew_id,
                proposal_hash=proposal_hash
            )
            
            # Auto-vote if we're a crew member
            if self.client.address in crew_members:
                logger.info(f"🗳️ Casting vote on consensus request {request_id}...")
                vote_tx = self.client.cast_vote(request_id, approved=True)
                logger.info(f"✅ Vote cast (tx: {vote_tx[:10]}...)")
            
            # Check if consensus reached
            # In production, wait for all votes or use event listener
            consensus_passed = self.client.has_consensus_passed(request_id)
            
            if consensus_passed:
                logger.info(f"✅ Consensus PASSED for decision {decision_id}")
            else:
                logger.warning(f"⚠️ Consensus NOT YET reached for decision {decision_id}")
                logger.warning("   Waiting for other crew members to vote...")
            
            return (consensus_passed, decision_id, tx_hash)
        
        except Exception as e:
            logger.error(f"❌ Failed to validate decision on blockchain: {e}")
            return (False, None, None)
    
    # =========================
    # Action Execution
    # =========================
    
    def mark_action_executed(
        self,
        decision_id: int,
        action_type: str,
        success: bool
    ) -> Optional[str]:
        """
        Mark action as executed on blockchain
        
        Args:
            decision_id: On-chain decision ID
            action_type: Type of action (e.g., "email_alert", "emergency_shutdown")
            success: Whether action succeeded
        
        Returns:
            transaction_hash or None
        """
        if not self.enable_blockchain or decision_id is None:
            logger.debug("Blockchain disabled or no decision_id - skipping execution logging")
            return None
        
        try:
            logger.info(f"🔗 Marking decision {decision_id} as executed on blockchain...")
            tx_hash = self.client.mark_executed(decision_id)
            logger.info(f"✅ Execution logged on-chain (tx: {tx_hash[:10]}...)")
            return tx_hash
        
        except Exception as e:
            logger.error(f"❌ Failed to mark execution on blockchain: {e}")
            return None
    
    # =========================
    # Utilities
    # =========================
    
    def _generate_event_id(self, event_data: Dict) -> bytes:
        """Generate deterministic event ID for deduplication"""
        # Use timestamp rounded to same-event window + node_id
        timestamp = event_data.get("timestamp", datetime.now(timezone.utc).isoformat())
        node_id = event_data.get("node_id", "unknown")
        
        event_str = f"{timestamp}-{node_id}"
        return Web3.solidity_keccak(['string'], [event_str])
    
    def _generate_decision_hash(self, decision_data: Dict) -> bytes:
        """Generate hash of decision data (off-chain storage)"""
        # Include key decision fields
        decision_json = json.dumps(decision_data, sort_keys=True)
        return Web3.solidity_keccak(['string'], [decision_json])
    
    def _map_severity(self, severity_str: str) -> int:
        """Map severity string to enum"""
        severity_map = {
            "safe": self.SEVERITY_SAFE,
            "normal": self.SEVERITY_SAFE,
            "warning": self.SEVERITY_WARNING,
            "critical": self.SEVERITY_CRITICAL,
            "emergency": self.SEVERITY_CRITICAL
        }
        return severity_map.get(severity_str.lower(), self.SEVERITY_WARNING)
    
    def get_governance_thresholds(self) -> Dict[str, int]:
        """Get current governance thresholds from blockchain"""
        if not self.enable_blockchain:
            return {
                "critical": 5000,
                "warning": 3000,
                "same_event_window": 30,
                "consensus_percentage": 51
            }
        
        return self.client.get_thresholds()


# =========================
# Integration with existing crew.py
# =========================

def integrate_blockchain_with_crew():
    """
    Helper function to add blockchain integration to existing crew
    
    Add this to your crew.py:
    
    from autonomous.crew_blockchain_integration import integrate_blockchain_with_crew
    
    # Initialize blockchain integration
    blockchain_integrator = integrate_blockchain_with_crew()
    
    # When forming crew:
    success, crew_id, tx = blockchain_integrator.validate_crew_formation(
        event_data={"timestamp": ..., "node_id": ...},
        crew_members=[...],
        methane_ppm=5500
    )
    
    # When making critical decision:
    passed, decision_id, tx = blockchain_integrator.validate_critical_decision(
        crew_id=crew_id,
        decision_data=reasoner_output,
        crew_members=[...],
        methane_ppm=5500
    )
    
    # After executing action:
    tx = blockchain_integrator.mark_action_executed(
        decision_id=decision_id,
        action_type="email_alert",
        success=True
    )
    """
    return CrewBlockchainIntegrator()


if __name__ == "__main__":
    # Test blockchain integration
    logging.basicConfig(level=logging.INFO)
    
    print("Testing blockchain integration...")
    integrator = CrewBlockchainIntegrator()
    
    if integrator.enable_blockchain:
        print(f"✅ Connected to blockchain")
        print(f"Agent address: {integrator.client.address}")
        print(f"Governance thresholds: {integrator.get_governance_thresholds()}")
    else:
        print("⚠️ Running in simulation mode")
