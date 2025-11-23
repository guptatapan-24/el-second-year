const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Starting deployment...\n");

  const [deployer] = await hre.ethers.getSigners();
  const network = hre.network.name;

  console.log("Deploying contracts with account:", deployer.address);
  console.log("Network:", network);
  console.log(
    "Account balance:",
    hre.ethers.formatEther(await hre.ethers.provider.getBalance(deployer.address)),
    "ETH\n"
  );

  // Deploy VeriRiskOracle
  console.log("Deploying VeriRiskOracle...");
  const VeriRiskOracle = await hre.ethers.getContractFactory("VeriRiskOracle");
  const oracle = await VeriRiskOracle.deploy(deployer.address);
  await oracle.waitForDeployment();
  const oracleAddress = await oracle.getAddress();

  console.log("VeriRiskOracle deployed to:", oracleAddress);
  console.log("Authorized signer:", deployer.address, "\n");

  // Deploy ConsumerDemo
  console.log("Deploying ConsumerDemo...");
  const ConsumerDemo = await hre.ethers.getContractFactory("ConsumerDemo");
  const consumer = await ConsumerDemo.deploy(oracleAddress);
  await consumer.waitForDeployment();
  const consumerAddress = await consumer.getAddress();

  console.log("ConsumerDemo deployed to:", consumerAddress, "\n");

  // Save deployment info
  const deploymentInfo = {
    network: network,
    deployer: deployer.address,
    contracts: {
      VeriRiskOracle: oracleAddress,
      ConsumerDemo: consumerAddress,
    },
    timestamp: new Date().toISOString(),
  };

  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  const filename = `${network}-${Date.now()}.json`;
  fs.writeFileSync(
    path.join(deploymentsDir, filename),
    JSON.stringify(deploymentInfo, null, 2)
  );

  // Also save latest deployment
  fs.writeFileSync(
    path.join(deploymentsDir, `${network}-latest.json`),
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log("Deployment info saved to:", filename);
  console.log("\n=== DEPLOYMENT SUMMARY ===");
  console.log("VeriRiskOracle:", oracleAddress);
  console.log("ConsumerDemo:", consumerAddress);
  console.log("\n=== NEXT STEPS ===");
  console.log("1. Update backend/.env with:");
  console.log(`   ORACLE_CONTRACT_ADDRESS=${oracleAddress}`);
  console.log("2. Verify contracts (if on Sepolia):");
  console.log(
    `   npx hardhat verify --network ${network} ${oracleAddress} "${deployer.address}"`
  );
  console.log(
    `   npx hardhat verify --network ${network} ${consumerAddress} "${oracleAddress}"`
  );
  console.log("3. Test the oracle:");
  console.log("   python backend/model_server.py --run-once --pool test_pool_1");
  console.log("   python backend/submit_to_chain.py --payload payload.json");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
