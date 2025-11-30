/* """
// register_agents.js - Register ADAM agents on blockchain

This script registers all agents (4 nodes × 4 agents = 16 total agents) on the blockchain.
Each Raspberry Pi runs 4 agents: Sensor, Aggregator, Decision, Coordinator
"""
*/
const hre = require("hardhat");
require("dotenv").config();

// Agent role enum
const AgentRole = {
  Sensor: 0,
  Aggregator: 1,
  Decision: 2,
  Coordinator: 3
};

// Configuration: Update these with your actual addresses
const AGENTS_CONFIG = [
  // Node 1 (CH4_001)
  {
    nodeAddress: process.env.NODE1_ADDRESS || "0x0000000000000000000000000000000000000001",
    agents: [
      { address: process.env.NODE1_SENSOR_ADDRESS, role: AgentRole.Sensor },
      { address: process.env.NODE1_AGGREGATOR_ADDRESS, role: AgentRole.Aggregator },
      { address: process.env.NODE1_DECISION_ADDRESS, role: AgentRole.Decision },
      { address: process.env.NODE1_COORDINATOR_ADDRESS, role: AgentRole.Coordinator }
    ]
  },
  // Node 2 (CH4_002)
  {
    nodeAddress: process.env.NODE2_ADDRESS || "0x0000000000000000000000000000000000000002",
    agents: [
      { address: process.env.NODE2_SENSOR_ADDRESS, role: AgentRole.Sensor },
      { address: process.env.NODE2_AGGREGATOR_ADDRESS, role: AgentRole.Aggregator },
      { address: process.env.NODE2_DECISION_ADDRESS, role: AgentRole.Decision },
      { address: process.env.NODE2_COORDINATOR_ADDRESS, role: AgentRole.Coordinator }
    ]
  },
  // Node 3 (CH4_003)
  {
    nodeAddress: process.env.NODE3_ADDRESS || "0x0000000000000000000000000000000000000003",
    agents: [
      { address: process.env.NODE3_SENSOR_ADDRESS, role: AgentRole.Sensor },
      { address: process.env.NODE3_AGGREGATOR_ADDRESS, role: AgentRole.Aggregator },
      { address: process.env.NODE3_DECISION_ADDRESS, role: AgentRole.Decision },
      { address: process.env.NODE3_COORDINATOR_ADDRESS, role: AgentRole.Coordinator }
    ]
  },
  // Node 4 (CH4_004)
  {
    nodeAddress: process.env.NODE4_ADDRESS || "0x0000000000000000000000000000000000000004",
    agents: [
      { address: process.env.NODE4_SENSOR_ADDRESS, role: AgentRole.Sensor },
      { address: process.env.NODE4_AGGREGATOR_ADDRESS, role: AgentRole.Aggregator },
      { address: process.env.NODE4_DECISION_ADDRESS, role: AgentRole.Decision },
      { address: process.env.NODE4_COORDINATOR_ADDRESS, role: AgentRole.Coordinator }
    ]
  }
];

async function main() {
  console.log("🔐 Registering ADAM Agents on Blockchain\n");

  // Load deployment
  const fs = require("fs");
  const path = require("path");
  const deploymentPath = path.join(__dirname, "../deployments", `latest-${hre.network.name}.json`);
  
  if (!fs.existsSync(deploymentPath)) {
    throw new Error(`Deployment file not found: ${deploymentPath}\nRun: npm run deploy:fides`);
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
  const crewRegistryAddress = deployment.contracts.CrewRegistry;

  console.log("📄 Using CrewRegistry at:", crewRegistryAddress);

  // Get contract instance
  const CrewRegistry = await hre.ethers.getContractFactory("CrewRegistry");
  const crewRegistry = CrewRegistry.attach(crewRegistryAddress);

  // Prepare batch registration data
  const allAgentAddresses = [];
  const allNodeAddresses = [];
  const allRoles = [];

  for (const nodeConfig of AGENTS_CONFIG) {
    for (const agentConfig of nodeConfig.agents) {
      if (agentConfig.address) {
        allAgentAddresses.push(agentConfig.address);
        allNodeAddresses.push(nodeConfig.nodeAddress);
        allRoles.push(agentConfig.role);
      }
    }
  }

  console.log(`\n📋 Registering ${allAgentAddresses.length} agents...\n`);

  // Batch register
  try {
    const tx = await crewRegistry.batchRegisterAgents(
      allAgentAddresses,
      allNodeAddresses,
      allRoles,
      { gasLimit: 5000000 }
    );

    console.log("⏳ Waiting for transaction confirmation...");
    const receipt = await tx.wait();

    console.log("✅ Registration complete!");
    console.log(`   Transaction: ${receipt.hash}`);
    console.log(`   Block: ${receipt.blockNumber}`);
    console.log(`   Gas used: ${receipt.gasUsed.toString()}\n`);

    // Verify registrations
    console.log("🔍 Verifying registrations...\n");
    let successCount = 0;

    for (let i = 0; i < allAgentAddresses.length; i++) {
      const isActive = await crewRegistry.isActiveAgent(allAgentAddresses[i]);
      const roleNames = ["Sensor", "Aggregator", "Decision", "Coordinator"];
      
      if (isActive) {
        console.log(`✅ ${allAgentAddresses[i]} (${roleNames[allRoles[i]]})`);
        successCount++;
      } else {
        console.log(`❌ ${allAgentAddresses[i]} (${roleNames[allRoles[i]]}) - FAILED`);
      }
    }

    console.log(`\n📊 Summary: ${successCount}/${allAgentAddresses.length} agents registered successfully\n`);

    // Save agent addresses to file for Python integration
    const agentMapping = {};
    for (let i = 0; i < allAgentAddresses.length; i++) {
      const roleNames = ["sensor", "aggregator", "decision", "coordinator"];
      const nodeNum = Math.floor(i / 4) + 1;
      const key = `node${nodeNum}_${roleNames[allRoles[i]]}`;
      agentMapping[key] = {
        address: allAgentAddresses[i],
        nodeAddress: allNodeAddresses[i],
        role: allRoles[i]
      };
    }

    const mappingPath = path.join(__dirname, "../deployments", "agent-addresses.json");
    fs.writeFileSync(mappingPath, JSON.stringify(agentMapping, null, 2));
    console.log("💾 Agent addresses saved to:", mappingPath);

  } catch (error) {
    console.error("❌ Registration failed:", error.message);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
