"""
blockchain_client.py - Web3.py wrapper for ADAM blockchain governance
"""
import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


class BlockchainClient:
    """
    Client for interacting with ADAM governance smart contracts on Fides Innova
    """
    
    def __init__(
        self,
        rpc_url: str = None,
        private_key: str = None,
        deployment_file: str = None
    ):
        """
        Initialize blockchain client
        
        Args:
            rpc_url: RPC endpoint (default: from env)
            private_key: Private key for transactions (default: from env)
            deployment_file: Path to deployment JSON (default: latest)
        """
        # Setup Web3 connection
        self.rpc_url = rpc_url or os.getenv("FIDES_RPC_URL", "https://fidesf1-rpc.fidesinnova.io/")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Add PoA middleware for Fides Innova (if needed)
        try:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except ValueError:
            pass  # Already added
        
        # Check connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")
        
        logger.info(f"✅ Connected to Fides Innova (Chain ID: {self.w3.eth.chain_id})")
        
        # Load account
        self.private_key = private_key or os.getenv("AGENT_PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("No private key provided. Set AGENT_PRIVATE_KEY env variable.")
        
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        logger.info(f"🔑 Using account: {self.address}")
        
        # Load contract addresses and ABIs
        self.contracts = self._load_contracts(deployment_file)
        logger.info("📄 Loaded contract addresses and ABIs")
    
    def _load_contracts(self, deployment_file: Optional[str] = None) -> Dict:
        """Load contract addresses and ABIs from deployment file"""
        
        # Find deployment file
        if deployment_file is None:
            blockchain_dir = Path(__file__).parent
            deployments_dir = blockchain_dir / "deployments"
            deployment_file = deployments_dir / "latest-fidesinnova.json"
        else:
            deployment_file = Path(deployment_file)
        
        if not deployment_file.exists():
            raise FileNotFoundError(
                f"Deployment file not found: {deployment_file}. "
                "Run: cd blockchain && npm run deploy:fides"
            )
        
        # Load deployment info
        with open(deployment_file, 'r') as f:
            deployment = json.load(f)
        
        contracts = {}
        
        # Load each contract
        for contract_name in ["GovernanceRules", "CrewRegistry", "DecisionLogger", "ConsensusValidator"]:
            address = deployment["contracts"][contract_name]
            
            # Load ABI from artifacts
            abi_path = Path(__file__).parent / "artifacts" / "contracts" / f"{contract_name}.sol" / f"{contract_name}.json"
            
            if abi_path.exists():
                with open(abi_path, 'r') as f:
                    artifact = json.load(f)
                    abi = artifact["abi"]
            else:
                # Fallback to minimal ABI
                logger.warning(f"⚠️ ABI not found for {contract_name}, using minimal ABI")
                abi = []
            
            # Create contract instance
            contracts[contract_name] = {
                "address": address,
                "abi": abi,
                "instance": self.w3.eth.contract(address=address, abi=abi)
            }
        
        return contracts
    
    # =========================
    # Governance Rules
    # =========================
    
    def is_critical(self, methane_ppm: int) -> bool:
        """Check if methane level is critical"""
        contract = self.contracts["GovernanceRules"]["instance"]
        return contract.functions.isCritical(methane_ppm).call()
    
    def is_warning(self, methane_ppm: int) -> bool:
        """Check if methane level requires warning"""
        contract = self.contracts["GovernanceRules"]["instance"]
        return contract.functions.isWarning(methane_ppm).call()
    
    def get_thresholds(self) -> Dict[str, int]:
        """Get current governance thresholds"""
        contract = self.contracts["GovernanceRules"]["instance"]
        return {
            "critical": contract.functions.criticalThreshold().call(),
            "warning": contract.functions.warningThreshold().call(),
            "same_event_window": contract.functions.sameEventWindow().call(),
            "consensus_percentage": contract.functions.consensusPercentage().call()
        }
    
    # =========================
    # Crew Registry
    # =========================
    
    def register_agent(
        self,
        agent_address: str,
        node_address: str,
        role: int  # 0=Sensor, 1=Aggregator, 2=Decision, 3=Coordinator
    ) -> str:
        """Register a new agent (owner only)"""
        contract = self.contracts["CrewRegistry"]["instance"]
        
        tx = contract.functions.registerAgent(
            agent_address,
            node_address,
            role
        ).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        return self._send_transaction(tx)
    
    def form_crew(
        self,
        event_id: bytes,
        members: List[str],
        methane_ppm: int
    ) -> Tuple[str, int]:
        """
        Form a new crew
        
        Returns:
            (transaction_hash, crew_id)
        """
        contract = self.contracts["CrewRegistry"]["instance"]
        
        tx = contract.functions.formCrew(
            event_id,
            members,
            methane_ppm
        ).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        tx_hash = self._send_transaction(tx)
        
        # Get crew ID from transaction receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        crew_id = self._extract_crew_id_from_receipt(receipt)
        
        return (tx_hash, crew_id)
    
    def get_crew_members(self, crew_id: int) -> List[str]:
        """Get members of a crew"""
        contract = self.contracts["CrewRegistry"]["instance"]
        return contract.functions.getCrewMembers(crew_id).call()
    
    def is_active_agent(self, agent_address: str) -> bool:
        """Check if agent is registered and active"""
        contract = self.contracts["CrewRegistry"]["instance"]
        return contract.functions.isActiveAgent(agent_address).call()
    
    # =========================
    # Decision Logger
    # =========================
    
    def log_decision(
        self,
        crew_id: int,
        decision_hash: bytes,
        decision_type: int,  # 0=CrewFormation, 1=AnomalyDetection, 2=ActionExecution
        severity: int,  # 0=Safe, 1=Warning, 2=Critical
        methane_ppm: int,
        voters: List[str],
        signatures: List[bytes],
        notes: str = ""
    ) -> Tuple[str, int]:
        """
        Log a decision to blockchain
        
        Returns:
            (transaction_hash, decision_id)
        """
        contract = self.contracts["DecisionLogger"]["instance"]
        
        tx = contract.functions.logDecision(
            crew_id,
            decision_hash,
            decision_type,
            severity,
            methane_ppm,
            voters,
            signatures,
            notes
        ).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        tx_hash = self._send_transaction(tx)
        
        # Get decision ID from receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        decision_id = self._extract_decision_id_from_receipt(receipt)
        
        return (tx_hash, decision_id)
    
    def mark_executed(self, decision_id: int) -> str:
        """Mark decision as executed"""
        contract = self.contracts["DecisionLogger"]["instance"]
        
        tx = contract.functions.markExecuted(decision_id).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        return self._send_transaction(tx)
    
    def get_decision(self, decision_id: int) -> Dict:
        """Get decision details"""
        contract = self.contracts["DecisionLogger"]["instance"]
        decision = contract.functions.getDecision(decision_id).call()
        
        return {
            "decision_id": decision[0],
            "crew_id": decision[1],
            "decision_hash": decision[2],
            "decision_type": decision[3],
            "severity": decision[4],
            "methane_ppm": decision[5],
            "timestamp": decision[6],
            "voters": decision[7],
            "executed": decision[8],
            "executed_at": decision[9],
            "notes": decision[10]
        }
    
    def get_nonce(self, agent_address: str = None) -> int:
        """Get current nonce for agent (for signing)"""
        contract = self.contracts["DecisionLogger"]["instance"]
        addr = agent_address or self.address
        return contract.functions.getNonce(addr).call()
    
    # =========================
    # Consensus Validator
    # =========================
    
    def request_consensus(
        self,
        crew_id: int,
        proposal_hash: bytes
    ) -> Tuple[str, int]:
        """
        Request consensus validation
        
        Returns:
            (transaction_hash, request_id)
        """
        contract = self.contracts["ConsensusValidator"]["instance"]
        
        tx = contract.functions.requestConsensus(
            crew_id,
            proposal_hash
        ).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        tx_hash = self._send_transaction(tx)
        
        # Get request ID from receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        request_id = self._extract_request_id_from_receipt(receipt)
        
        return (tx_hash, request_id)
    
    def cast_vote(self, request_id: int, approved: bool) -> str:
        """Cast vote on consensus request"""
        contract = self.contracts["ConsensusValidator"]["instance"]
        
        tx = contract.functions.castVote(request_id, approved).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        return self._send_transaction(tx)
    
    def has_consensus_passed(self, request_id: int) -> bool:
        """Check if consensus has passed"""
        contract = self.contracts["ConsensusValidator"]["instance"]
        return contract.functions.hasConsensusPassed(request_id).call()
    
    # =========================
    # Utilities
    # =========================
    
    def sign_decision(self, decision_hash: bytes) -> bytes:
        """Sign a decision hash with agent's private key"""
        nonce = self.get_nonce()
        
        # Create message with nonce (prevents replay attacks)
        message_hash = Web3.solidity_keccak(
            ['bytes32', 'uint256'],
            [decision_hash, nonce]
        )
        
        # Sign with eth_sign prefix
        message = encode_defunct(hexstr=message_hash.hex())
        signed = self.account.sign_message(message)
        
        return signed.signature
    
    def _send_transaction(self, tx: Dict) -> str:
        """Sign and send transaction"""
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"📤 Transaction sent: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            logger.info(f"✅ Transaction confirmed in block {receipt['blockNumber']}")
        else:
            logger.error(f"❌ Transaction failed!")
            raise Exception("Transaction failed")
        
        return tx_hash.hex()
    
    def _extract_crew_id_from_receipt(self, receipt) -> int:
        """Extract crew ID from CrewFormed event"""
        contract = self.contracts["CrewRegistry"]["instance"]
        crew_formed_event = contract.events.CrewFormed()
        logs = crew_formed_event.process_receipt(receipt)
        
        if logs:
            return logs[0]['args']['crewId']
        return 0
    
    def _extract_decision_id_from_receipt(self, receipt) -> int:
        """Extract decision ID from DecisionLogged event"""
        contract = self.contracts["DecisionLogger"]["instance"]
        decision_logged_event = contract.events.DecisionLogged()
        logs = decision_logged_event.process_receipt(receipt)
        
        if logs:
            return logs[0]['args']['decisionId']
        return 0
    
    def _extract_request_id_from_receipt(self, receipt) -> int:
        """Extract request ID from ConsensusRequested event"""
        contract = self.contracts["ConsensusValidator"]["instance"]
        consensus_requested_event = contract.events.ConsensusRequested()
        logs = consensus_requested_event.process_receipt(receipt)
        
        if logs:
            return logs[0]['args']['requestId']
        return 0
    
    def get_balance(self, address: str = None) -> float:
        """Get FDS balance of address"""
        addr = address or self.address
        balance_wei = self.w3.eth.get_balance(addr)
        return self.w3.from_wei(balance_wei, 'ether')
