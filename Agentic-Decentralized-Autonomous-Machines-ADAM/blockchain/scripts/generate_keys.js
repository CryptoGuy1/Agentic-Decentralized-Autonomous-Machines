/**
 * generate_keys.js - Generate Ethereum key pairs for ADAM agents
 * 
 * Generates 16 key pairs (4 nodes × 4 agents per node)
 * IMPORTANT: Save the output securely and never commit to git!
 */

const { ethers } = require("ethers");
const fs = require("fs");
const path = require("path");

const NODES = ["CH4_001", "CH4_002", "CH4_003", "CH4_004"];
const ROLES = ["Sensor", "Aggregator", "Decision", "Coordinator"];

function generateKeys() {
  console.log("🔐 Generating Ethereum Key Pairs for ADAM Agents\n");
  console.log("=" .repeat(80));
  console.log("⚠️  SECURITY WARNING: Keep these keys secure and never commit to git!");
  console.log("=" .repeat(80) + "\n");

  const keys = {};
  const envContent = [];
  
  // Add header
  envContent.push("# ===========================");
  envContent.push("# ADAM Blockchain Configuration");
  envContent.push("# ===========================\n");
  
  envContent.push("# Fides Innova Network");
  envContent.push("FIDES_RPC_URL=https://fidesf1-rpc.fidesinnova.io/");
  envContent.push("FIDES_CHAIN_ID=706883");
  envContent.push("FIDES_EXPLORER=https://explorer.fidesinnova.io\n");
  
  envContent.push("# Deployment Account (generate separately or use one of the node keys)");
  envContent.push("DEPLOYER_PRIVATE_KEY=REPLACE_WITH_YOUR_KEY\n");
  
  envContent.push("# Enable/Disable Blockchain");
  envContent.push("ENABLE_BLOCKCHAIN=true\n");

  // Generate node addresses (one per Raspberry Pi)
  console.log("📡 Generating Node Addresses (Raspberry Pi):\n");
  const nodeKeys = {};
  
  for (let i = 0; i < NODES.length; i++) {
    const wallet = ethers.Wallet.createRandom();
    nodeKeys[`NODE${i + 1}`] = {
      address: wallet.address,
      privateKey: wallet.privateKey,
      mnemonic: wallet.mnemonic.phrase
    };
    
    console.log(`${NODES[i]}:`);
    console.log(`  Address:     ${wallet.address}`);
    console.log(`  Private Key: ${wallet.privateKey}`);
    console.log(`  Mnemonic:    ${wallet.mnemonic.phrase}\n`);
  }

  // Add node addresses to .env
  envContent.push("# ===========================");
  envContent.push("# Node Addresses (Raspberry Pi)");
  envContent.push("# ===========================\n");
  
  for (let i = 1; i <= 4; i++) {
    envContent.push(`NODE${i}_ADDRESS=${nodeKeys[`NODE${i}`].address}`);
    envContent.push(`NODE${i}_PRIVATE_KEY=${nodeKeys[`NODE${i}`].privateKey}\n`);
  }

  // Generate agent addresses (4 per node)
  console.log("\n" + "=".repeat(80));
  console.log("🤖 Generating Agent Addresses (4 agents per node):\n");

  for (let nodeIdx = 0; nodeIdx < NODES.length; nodeIdx++) {
    const nodeNum = nodeIdx + 1;
    console.log(`\n${NODES[nodeIdx]} Agents:`);
    
    envContent.push(`# ===========================`);
    envContent.push(`# Node ${nodeNum} (${NODES[nodeIdx]}) Agent Addresses`);
    envContent.push(`# ===========================\n`);

    for (let roleIdx = 0; roleIdx < ROLES.length; roleIdx++) {
      const wallet = ethers.Wallet.createRandom();
      const key = `NODE${nodeNum}_${ROLES[roleIdx].toUpperCase()}`;
      
      keys[key] = {
        nodeId: NODES[nodeIdx],
        role: ROLES[roleIdx],
        roleIndex: roleIdx,
        address: wallet.address,
        privateKey: wallet.privateKey
      };

      console.log(`  ${ROLES[roleIdx]}:`);
      console.log(`    Address:     ${wallet.address}`);
      console.log(`    Private Key: ${wallet.privateKey}`);

      envContent.push(`${key}_ADDRESS=${wallet.address}`);
      envContent.push(`${key}_PRIVATE_KEY=${wallet.privateKey}\n`);
    }
  }

  // Add agent configuration template
  envContent.push("\n# ===========================");
  envContent.push("# Agent Configuration (set on each Raspberry Pi)");
  envContent.push("# ===========================\n");
  envContent.push("# Example for Node 1 Coordinator:");
  envContent.push("# AGENT_PRIVATE_KEY=${NODE1_COORDINATOR_PRIVATE_KEY}");
  envContent.push("# AGENT_ADDRESS=${NODE1_COORDINATOR_ADDRESS}");
  envContent.push("# NODE_ADDRESS=${NODE1_ADDRESS}");
  envContent.push("# AGENT_ROLE=3  # 0=Sensor, 1=Aggregator, 2=Decision, 3=Coordinator\n");

  // Add existing ADAM config
  envContent.push("# ===========================");
  envContent.push("# Existing ADAM Configuration");
  envContent.push("# ===========================\n");
  envContent.push("WEAVIATE_URL=http://localhost:8080");
  envContent.push("OPENAI_API_KEY=your_openai_api_key");
  envContent.push("GMAIL_USER=your_email@gmail.com");
  envContent.push("GMAIL_APP_PASSWORD=your_app_password");
  envContent.push("ABSOLUTE_EMERGENCY_PPM=5000.0");

  // Save to files
  const outputDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Save JSON
  const jsonPath = path.join(outputDir, "agent-keys.json");
  fs.writeFileSync(jsonPath, JSON.stringify({ nodes: nodeKeys, agents: keys }, null, 2));
  
  // Save .env
  const envPath = path.join(__dirname, "../.env.generated");
  fs.writeFileSync(envPath, envContent.join("\n"));

  console.log("\n" + "=".repeat(80));
  console.log("✅ Key Generation Complete!\n");
  console.log("📁 Files saved:");
  console.log(`   ${jsonPath}`);
  console.log(`   ${envPath}\n`);
  console.log("📋 Next Steps:");
  console.log("   1. Review .env.generated and copy to .env");
  console.log("   2. Fund deployer address with FDS from faucet");
  console.log("   3. Deploy contracts: npm run deploy:fides");
  console.log("   4. Register agents: node scripts/register_agents.js");
  console.log("   5. Configure each Raspberry Pi with its agent keys\n");
  console.log("💰 Fund these addresses with FDS:");
  console.log(`   Deployer: ${nodeKeys.NODE1.address} (needs ~0.5 FDS)`);
  console.log(`   Faucet: https://explorer.fidesinnova.io\n`);
  console.log("⚠️  Keep agent-keys.json secure and never commit to git!");
  console.log("=" .repeat(80) + "\n");

  // Create funding script
  const fundingScript = `#!/bin/bash
# Funding script for ADAM agents
# Send FDS to each agent for transaction gas

echo "💰 Funding ADAM Agent Addresses"
echo "================================"
echo ""
echo "Send 0.1 FDS to each of these addresses:"
echo ""
`;

  const fundingScriptPath = path.join(outputDir, "fund-agents.sh");
  const addressList = [];
  
  for (const key in keys) {
    addressList.push(`echo "  ${keys[key].role} (${keys[key].nodeId}): ${keys[key].address}"`);
  }
  
  fs.writeFileSync(
    fundingScriptPath,
    fundingScript + addressList.join("\n") + "\n\necho \"\"\necho \"Total needed: 1.6 FDS (16 agents × 0.1 FDS)\"\n"
  );
  fs.chmodSync(fundingScriptPath, '755');

  console.log("💡 Tip: Use fund-agents.sh to see addresses that need funding\n");
}

// Run if called directly
if (require.main === module) {
  generateKeys();
}

module.exports = { generateKeys };
