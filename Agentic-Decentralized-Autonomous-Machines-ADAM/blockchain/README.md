# ADAM Blockchain Governance System

Complete blockchain governance implementation for the ADAM multi-agent methane monitoring system.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Fides Innova Blockchain                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Governance   │ │  Crew        │ │  Decision    │        │
│  │   Rules      │ │  Registry    │ │   Logger     │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐                                           │
│  │  Consensus   │  Smart Contracts (Solidity)               │
│  │  Validator   │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
            ↕ Web3.py
┌─────────────────────────────────────────────────────────────┐
│            Python Blockchain Integration Layer               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   BlockchainClient (blockchain_client.py)            │  │
│  │   CrewBlockchainIntegrator                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
            ↕
┌─────────────────────────────────────────────────────────────┐
│              CrewAI Agent System (crew.py)                   │
│  ┌────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Sensor │→│ Aggregator │→│ Decision │→│ Coordinator  │  │
│  └────────┘ └────────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Smart Contracts

### 1. GovernanceRules.sol

**Purpose:** Configurable governance parameters

**Features:**

- Critical threshold: 5000 ppm (adjustable)
- Warning threshold: 3000 ppm (adjustable)
- Same event window: 30 seconds
- Consensus percentage: 51% (simple majority)
- Optional weighted voting by reputation

**Key Functions:**

- `isCritical(uint256 methanePpm)` - Check if reading is critical
- `updateCriticalThreshold(uint256)` - Update threshold (owner only)
- `getRequiredConsensus(uint256)` - Calculate required votes

### 2. CrewRegistry.sol

**Purpose:** Agent registration and crew management

**Features:**

- Hybrid identity: node address + agent role
- Anti-Sybil protection (max 8 agents per node)
- Reputation tracking (0-1000 scale)
- Accuracy metrics (correct decisions / total decisions)

**Key Functions:**

- `registerAgent(address, address, role)` - Register new agent
- `formCrew(bytes32, address[], uint256)` - Form crew on-chain
- `updateReputation(address, bool)` - Update agent reputation

### 3. DecisionLogger.sol

**Purpose:** Immutable audit trail with conflict resolution

**Features:**

- Stores decision hashes (off-chain data references)
- Replay attack prevention (nonce-based signatures)
- Automatic conflict detection (same event window)
- Severity escalation (highest severity wins)
- First timestamp resolution (if same severity)

**Key Functions:**

- `logDecision(...)` - Log decision with signatures
- `markExecuted(uint256)` - Mark decision as executed
- `getConflictResolution(uint256)` - Get conflict details

### 4. ConsensusValidator.sol

**Purpose:** Byzantine fault-tolerant consensus

**Features:**

- Simple majority (51%) or weighted voting
- Reputation-based weights (1-10 scale)
- 5-minute voting window
- Automatic consensus detection

**Key Functions:**

- `requestConsensus(uint256, bytes32)` - Start voting
- `castVote(uint256, bool)` - Submit vote
- `hasConsensusPassed(uint256)` - Check result

## 🚀 Deployment Guide

### Step 1: Install Dependencies

```bash
cd blockchain
npm install
```

### Step 2: Configure Environment

```bash
cp .env.example .env
# Edit .env and add your DEPLOYER_PRIVATE_KEY
```

**Important:** Get FDS tokens from Fides Innova faucet:

- https://explorer.fidesinnova.io (use faucet button)
- You need ~0.5 FDS for deployment

### Step 3: Compile Contracts

```bash
npm run compile
```

### Step 4: Deploy to Fides Innova

```bash
npm run deploy:fides
```

This will:

1. Deploy all 4 contracts
2. Save addresses to `deployments/latest-fidesinnova.json`
3. Display contract addresses and explorer links

### Step 5: Generate Agent Keys

```bash
node scripts/generate_keys.js
```

This generates 16 Ethereum key pairs (4 nodes × 4 agents).
**Save these keys securely!**

### Step 6: Register Agents

```bash
# Update .env with generated addresses
node scripts/register_agents.js
```

Registers all 16 agents on-chain with their roles.

## 🔗 Python Integration

### Installation

```bash
pip install web3 eth-account python-dotenv
```

### Basic Usage

```python
from blockchain.python.blockchain_client import BlockchainClient

# Initialize client
client = BlockchainClient(
    private_key=os.getenv("AGENT_PRIVATE_KEY")
)

# Check if methane is critical
is_critical = client.is_critical(5500)  # True

# Form crew
tx_hash, crew_id = client.form_crew(
    event_id=event_hash,
    members=[agent1, agent2, agent3, agent4],
    methane_ppm=5500
)

# Log decision
decision_hash = Web3.solidity_keccak(['string'], [json.dumps(decision)])
signature = client.sign_decision(decision_hash)

tx_hash, decision_id = client.log_decision(
    crew_id=crew_id,
    decision_hash=decision_hash,
    decision_type=1,  # AnomalyDetection
    severity=2,  # Critical
    methane_ppm=5500,
    voters=[client.address],
    signatures=[signature],
    notes="LLM detected critical methane"
)

# Mark executed
client.mark_executed(decision_id)
```

### Integration with CrewAI

```python
from blockchain.python.crew_blockchain_integration import CrewBlockchainIntegrator

# Initialize integrator
blockchain = CrewBlockchainIntegrator(
    agent_private_key=os.getenv("AGENT_PRIVATE_KEY"),
    agent_role=3  # Coordinator
)

# In your crew formation logic:
success, crew_id, tx = blockchain.validate_crew_formation(
    event_data={"timestamp": timestamp, "node_id": "CH4_001"},
    crew_members=[sensor_addr, agg_addr, dec_addr, coord_addr],
    methane_ppm=5500
)

# In your decision logic:
if methane_ppm >= 5000:  # Critical
    passed, decision_id, tx = blockchain.validate_critical_decision(
        crew_id=crew_id,
        decision_data=llm_output,
        crew_members=crew_members,
        methane_ppm=methane_ppm
    )

# After sending alert:
blockchain.mark_action_executed(
    decision_id=decision_id,
    action_type="email_alert",
    success=True
)
```

## 🔒 Security Features

### 1. Anti-Sybil Protection

- Max 8 agents per node address
- Prevents single node from pretending to be multiple nodes

### 2. Replay Attack Prevention

- Nonce-based signatures
- Each agent has incrementing nonce
- Old signatures cannot be reused

### 3. Byzantine Fault Tolerance

- Consensus requires ⌈n/2⌉ + 1 votes
- Tolerates up to ⌊(n-1)/2⌋ malicious agents
- Example: 4-agent crew tolerates 1 malicious agent

### 4. Conflict Resolution

- Same event detection (30-second window)
- Automatic severity escalation
- First timestamp wins (if same severity)

### 5. Immutable Audit Trail

- All decisions logged on-chain
- Cannot be modified or deleted
- Full transparency and accountability

## 📊 Performance Metrics

Based on evaluation in paper:

| Metric                 | Value   | Note                       |
| ---------------------- | ------- | -------------------------- |
| T_validate mean        | ~TBD ms | Blockchain validation time |
| T_validate 95%         | ~TBD ms | 95th percentile            |
| Gas per crew formation | ~200k   | ~$0.002 at 10 gwei         |
| Gas per decision log   | ~300k   | ~$0.003 at 10 gwei         |
| Throughput             | ~15 TPS | Fides Innova capacity      |

## 🧪 Testing

### Local Testing (Hardhat Network)

```bash
# Start local blockchain
npx hardhat node

# Deploy to local network
npm run deploy:local

# Run tests
npm run test
```

### Fides Innova Testnet Testing

```bash
# Deploy
npm run deploy:fides

# Register agents
node scripts/register_agents.js

# Test Python integration
cd ..
python -m blockchain.python.crew_blockchain_integration
```

## 🔧 Configuration

### Disable Blockchain (for testing)

Set in `.env`:

```bash
ENABLE_BLOCKCHAIN=false
```

The system will run in simulation mode without blockchain calls.

### Update Governance Parameters

```javascript
// Connect to deployed GovernanceRules
const rules = await ethers.getContractAt("GovernanceRules", address);

// Update critical threshold
await rules.updateCriticalThreshold(6000); // Change to 6000 ppm

// Enable weighted voting
await rules.setWeightedVoting(true);
```

## 📁 File Structure

```
blockchain/
├── contracts/
│   ├── GovernanceRules.sol
│   ├── CrewRegistry.sol
│   ├── DecisionLogger.sol
│   └── ConsensusValidator.sol
├── scripts/
│   ├── deploy.js
│   ├── register_agents.js
│   └── generate_keys.js
├── python/
│   ├── blockchain_client.py
│   └── crew_blockchain_integration.py
├── deployments/
│   ├── latest-fidesinnova.json
│   └── agent-addresses.json
├── hardhat.config.js
├── package.json
└── .env.example
```

## 🎯 Next Steps

1. **Deploy contracts** to Fides Innova testnet
2. **Generate keys** for all 16 agents (4 nodes × 4 agents)
3. **Register agents** on-chain
4. **Update crew.py** to use blockchain integration
5. **Run 72-hour evaluation** with blockchain validation
6. **Collect metrics** (T_validate, gas costs, consensus times)

## 📚 Additional Resources

- Fides Innova Docs: https://fidesinnova.io/docs
- Explorer: https://explorer.fidesinnova.io
- Hardhat Docs: https://hardhat.org/docs
- Web3.py Docs: https://web3py.readthedocs.io

## ⚠️ Important Notes

1. **Keep private keys secure** - Never commit to git
2. **Test on testnet first** - Ensure everything works before mainnet
3. **Monitor gas prices** - Adjust gas limits if transactions fail
4. **Backup deployment files** - Save `deployments/` directory
5. **Agent reputation** - Starts at 500, adjusts based on correct decisions

## 🐛 Troubleshooting

### "insufficient funds for gas"

- Get FDS from faucet: https://explorer.fidesinnova.io

### "Agent not registered"

- Run: `node scripts/register_agents.js`

### "Transaction failed"

- Check gas limits in scripts
- Verify contract addresses in deployment file

### "Connection timeout"

- Check RPC URL: https://fidesf1-rpc.fidesinnova.io/
- Try again in a few seconds
