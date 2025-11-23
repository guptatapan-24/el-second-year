const hre = require("hardhat");

/**
 * Test script for local development
 * Run with: npx hardhat run scripts/test-local.js --network localhost
 */
async function main() {
  const [signer] = await hre.ethers.getSigners();
  
  console.log("Testing VeriRiskOracle locally...");
  console.log("Signer address:", signer.address);

  // Get deployed contract (assumes deploy script was run)
  const fs = require('fs');
  const path = require('path');
  const deploymentFile = path.join(__dirname, '../deployments/localhost-latest.json');
  
  if (!fs.existsSync(deploymentFile)) {
    console.error("No deployment found. Run deploy script first.");
    return;
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentFile, 'utf8'));
  const oracleAddress = deployment.contracts.VeriRiskOracle;

  console.log("Oracle address:", oracleAddress);

  // Get contract instance
  const VeriRiskOracle = await hre.ethers.getContractFactory("VeriRiskOracle");
  const oracle = VeriRiskOracle.attach(oracleAddress);

  // Create test submission
  const poolId = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("test_pool_1"));
  const score = 65;
  const timestamp = Math.floor(Date.now() / 1000);
  const cidHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("QmTestCID123"));
  const nonce = Date.now();

  console.log("\nCreating test risk submission:");
  console.log("Pool ID:", poolId);
  console.log("Score:", score);
  console.log("Timestamp:", timestamp);
  console.log("Nonce:", nonce);

  // Sign data
  const dataHash = hre.ethers.keccak256(
    hre.ethers.solidityPacked(
      ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
      [poolId, score, timestamp, cidHash, nonce]
    )
  );
  const signature = await signer.signMessage(hre.ethers.getBytes(dataHash));

  console.log("\nSignature:", signature);

  // Submit to contract
  console.log("\nSubmitting to contract...");
  const tx = await oracle.submitRisk(
    poolId,
    score,
    timestamp,
    signature,
    cidHash,
    nonce
  );

  console.log("Transaction hash:", tx.hash);
  const receipt = await tx.wait();
  console.log("Confirmed in block:", receipt.blockNumber);

  // Read back
  const [storedScore, storedTimestamp, storedCidHash] =
    await oracle.getLatestRisk(poolId);

  console.log("\n=== Stored Risk Data ===");
  console.log("Score:", storedScore.toString());
  console.log("Timestamp:", storedTimestamp.toString());
  console.log("CID Hash:", storedCidHash);

  console.log("\n✓ Test successful!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
