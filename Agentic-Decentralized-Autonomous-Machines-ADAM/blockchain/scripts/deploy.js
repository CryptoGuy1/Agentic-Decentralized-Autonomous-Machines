const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying ADAM Governance System to Fides Innova...\n");

  // Get deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await hre.ethers.provider.getBalance(deployer.address)).toString(), "FDS\n");

  // =====================================================
  // 1. Deploy GovernanceRules
  // =====================================================
  console.log("📋 Deploying GovernanceRules...");
  const GovernanceRules = await hre.ethers.getContractFactory("GovernanceRules");
  const governanceRules = await GovernanceRules.deploy();
  await governanceRules.waitForDeployment();
  const governanceRulesAddress = await governanceRules.getAddress();
  console.log("✅ GovernanceRules deployed to:", governanceRulesAddress);
  console.log("   - Critical Threshold:", await governanceRules.criticalThreshold(), "ppm");
  console.log("   - Warning Threshold:", await governanceRules.warningThreshold(), "ppm");
  console.log("   - Same Event Window:", await governanceRules.sameEventWindow(), "seconds");
  console.log("   - Consensus Percentage:", await governanceRules.consensusPercentage(), "%\n");

  // =====================================================
  // 2. Deploy CrewRegistry
  // =====================================================
  console.log("👥 Deploying CrewRegistry...");
  const CrewRegistry = await hre.ethers.getContractFactory("CrewRegistry");
  const crewRegistry = await CrewRegistry.deploy();
  await crewRegistry.waitForDeployment();
  const crewRegistryAddress = await crewRegistry.getAddress();
  console.log("✅ CrewRegistry deployed to:", crewRegistryAddress, "\n");

  // =====================================================
  // 3. Deploy DecisionLogger
  // =====================================================
  console.log("📝 Deploying DecisionLogger...");
  const DecisionLogger = await hre.ethers.getContractFactory("DecisionLogger");
  const decisionLogger = await DecisionLogger.deploy(crewRegistryAddress, governanceRulesAddress);
  await decisionLogger.waitForDeployment();
  const decisionLoggerAddress = await decisionLogger.getAddress();
  console.log("✅ DecisionLogger deployed to:", decisionLoggerAddress, "\n");

  // =====================================================
  // 4. Deploy ConsensusValidator
  // =====================================================
  console.log("✅ Deploying ConsensusValidator...");
  const ConsensusValidator = await hre.ethers.getContractFactory("ConsensusValidator");
  const consensusValidator = await ConsensusValidator.deploy(crewRegistryAddress, governanceRulesAddress);
  await consensusValidator.waitForDeployment();
  const consensusValidatorAddress = await consensusValidator.getAddress();
  console.log("✅ ConsensusValidator deployed to:", consensusValidatorAddress, "\n");

  // =====================================================
  // 5. Save deployment addresses
  // =====================================================
  const deploymentInfo = {
    network: hre.network.name,
    chainId: hre.network.config.chainId,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      GovernanceRules: governanceRulesAddress,
      CrewRegistry: crewRegistryAddress,
      DecisionLogger: decisionLoggerAddress,
      ConsensusValidator: consensusValidatorAddress
    },
    initialConfig: {
      criticalThreshold: 5000,
      warningThreshold: 3000,
      sameEventWindow: 30,
      consensusPercentage: 51
    }
  };

  const fs = require("fs");
  const path = require("path");
  
  // Save to JSON file
  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }
  
  const filename = `deployment-${hre.network.name}-${Date.now()}.json`;
  fs.writeFileSync(
    path.join(deploymentsDir, filename),
    JSON.stringify(deploymentInfo, null, 2)
  );
  
  // Save latest deployment
  fs.writeFileSync(
    path.join(deploymentsDir, `latest-${hre.network.name}.json`),
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log("=".repeat(60));
  console.log("🎉 Deployment Complete!");
  console.log("=".repeat(60));
  console.log("\n📄 Contract Addresses:");
  console.log("   GovernanceRules:    ", governanceRulesAddress);
  console.log("   CrewRegistry:       ", crewRegistryAddress);
  console.log("   DecisionLogger:     ", decisionLoggerAddress);
  console.log("   ConsensusValidator: ", consensusValidatorAddress);
  console.log("\n💾 Deployment info saved to:", filename);
  console.log("\n🔗 View on Explorer:");
  console.log("   https://explorer.fidesinnova.io/address/" + governanceRulesAddress);
  console.log("\n📝 Next Steps:");
  console.log("   1. Update .env with contract addresses");
  console.log("   2. Register agents using scripts/register_agents.js");
  console.log("   3. Run Python integration tests\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
