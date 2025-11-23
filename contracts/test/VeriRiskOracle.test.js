const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VeriRiskOracle", function () {
  let oracle;
  let consumer;
  let owner;
  let signer;
  let unauthorized;

  beforeEach(async function () {
    [owner, signer, unauthorized] = await ethers.getSigners();

    // Deploy Oracle
    const VeriRiskOracle = await ethers.getContractFactory("VeriRiskOracle");
    oracle = await VeriRiskOracle.deploy(signer.address);
    await oracle.waitForDeployment();

    // Deploy Consumer
    const ConsumerDemo = await ethers.getContractFactory("ConsumerDemo");
    consumer = await ConsumerDemo.deploy(await oracle.getAddress());
    await consumer.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the correct authorized signer", async function () {
      expect(await oracle.authorizedSigner()).to.equal(signer.address);
    });

    it("Should set the correct owner", async function () {
      expect(await oracle.owner()).to.equal(owner.address);
    });
  });

  describe("Risk Submission", function () {
    it("Should accept valid signed risk submission", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));
      const score = 75;
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      // Create signature
      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await signer.signMessage(ethers.getBytes(dataHash));

      // Submit risk
      await expect(
        oracle.submitRisk(poolId, score, timestamp, signature, cidHash, nonce)
      )
        .to.emit(oracle, "RiskUpdated")
        .withArgs(poolId, score, timestamp, cidHash);

      // Verify stored data
      const [storedScore, storedTimestamp, storedCidHash] =
        await oracle.getLatestRisk(poolId);
      expect(storedScore).to.equal(score);
      expect(storedTimestamp).to.equal(timestamp);
      expect(storedCidHash).to.equal(cidHash);
    });

    it("Should reject submission with invalid signature", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));
      const score = 75;
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      // Create signature with wrong signer
      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await unauthorized.signMessage(
        ethers.getBytes(dataHash)
      );

      // Should revert
      await expect(
        oracle.submitRisk(poolId, score, timestamp, signature, cidHash, nonce)
      ).to.be.revertedWith("Invalid signature");
    });

    it("Should reject submission with reused nonce", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));
      const score = 75;
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      // Create signature
      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await signer.signMessage(ethers.getBytes(dataHash));

      // First submission should succeed
      await oracle.submitRisk(
        poolId,
        score,
        timestamp,
        signature,
        cidHash,
        nonce
      );

      // Second submission with same nonce should fail
      await expect(
        oracle.submitRisk(poolId, score, timestamp, signature, cidHash, nonce)
      ).to.be.revertedWith("Nonce already used");
    });

    it("Should reject score > 100", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));
      const score = 150; // Invalid
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await signer.signMessage(ethers.getBytes(dataHash));

      await expect(
        oracle.submitRisk(poolId, score, timestamp, signature, cidHash, nonce)
      ).to.be.revertedWith("Score must be 0-100");
    });
  });

  describe("Signer Management", function () {
    it("Should allow owner to update signer", async function () {
      const newSigner = unauthorized.address;

      await expect(oracle.updateAuthorizedSigner(newSigner))
        .to.emit(oracle, "SignerUpdated")
        .withArgs(signer.address, newSigner);

      expect(await oracle.authorizedSigner()).to.equal(newSigner);
    });

    it("Should not allow non-owner to update signer", async function () {
      await expect(
        oracle.connect(unauthorized).updateAuthorizedSigner(unauthorized.address)
      ).to.be.reverted;
    });
  });

  describe("Risk Staleness", function () {
    it("Should correctly identify stale risk data", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));

      // No data yet - should be stale
      expect(await oracle.isRiskStale(poolId, 3600)).to.be.true;

      // Submit fresh data
      const score = 50;
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await signer.signMessage(ethers.getBytes(dataHash));
      await oracle.submitRisk(
        poolId,
        score,
        timestamp,
        signature,
        cidHash,
        nonce
      );

      // Should not be stale
      expect(await oracle.isRiskStale(poolId, 3600)).to.be.false;
    });
  });

  describe("Consumer Contract", function () {
    it("Should simulate pause action for high risk", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));
      const score = 80; // Above pause threshold (75)
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      // Submit high risk
      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await signer.signMessage(ethers.getBytes(dataHash));
      await oracle.submitRisk(
        poolId,
        score,
        timestamp,
        signature,
        cidHash,
        nonce
      );

      // Simulate action
      const [action, riskScore] = await consumer.simulateAction(poolId);
      expect(action).to.equal("PAUSE_POOL");
      expect(riskScore).to.equal(score);
    });

    it("Should execute pause action", async function () {
      const poolId = ethers.keccak256(ethers.toUtf8Bytes("test_pool_1"));
      const score = 80;
      const timestamp = Math.floor(Date.now() / 1000);
      const cidHash = ethers.keccak256(ethers.toUtf8Bytes("QmTest"));
      const nonce = 1;

      // Submit high risk
      const dataHash = ethers.keccak256(
        ethers.solidityPacked(
          ["bytes32", "uint16", "uint256", "bytes32", "uint256"],
          [poolId, score, timestamp, cidHash, nonce]
        )
      );
      const signature = await signer.signMessage(ethers.getBytes(dataHash));
      await oracle.submitRisk(
        poolId,
        score,
        timestamp,
        signature,
        cidHash,
        nonce
      );

      // Execute action
      await expect(consumer.checkAndAct(poolId))
        .to.emit(consumer, "PoolPaused")
        .withArgs(poolId, score);

      expect(await consumer.isPaused(poolId)).to.be.true;
    });
  });
});
