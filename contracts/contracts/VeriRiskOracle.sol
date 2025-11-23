// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title VeriRiskOracle
 * @dev Verifiable AI Risk Oracle with cryptographic signature verification
 */
contract VeriRiskOracle is Ownable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    // Authorized signer address
    address public authorizedSigner;

    // Risk data structure
    struct RiskData {
        uint16 score;           // Risk score 0-100
        uint256 timestamp;      // Timestamp of risk computation
        bytes32 cidHash;        // IPFS CID hash for model artifacts
        uint256 nonce;          // Nonce for replay protection
    }

    // Pool ID => Latest risk data
    mapping(bytes32 => RiskData) public latestRisk;

    // Signer => Pool ID => Last used nonce
    mapping(address => mapping(bytes32 => uint256)) public lastNonce;

    // Events
    event RiskUpdated(
        bytes32 indexed poolId,
        uint16 score,
        uint256 timestamp,
        bytes32 cidHash
    );

    event SignerUpdated(
        address indexed oldSigner,
        address indexed newSigner
    );

    constructor(address _authorizedSigner) Ownable(msg.sender) {
        require(_authorizedSigner != address(0), "Invalid signer address");
        authorizedSigner = _authorizedSigner;
        emit SignerUpdated(address(0), _authorizedSigner);
    }

    /**
     * @dev Submit risk data with signature verification
     * @param poolId Pool identifier (bytes32)
     * @param score Risk score (0-100)
     * @param timestamp Timestamp of computation
     * @param signature Cryptographic signature
     * @param cidHash IPFS CID hash
     * @param nonce Unique nonce for replay protection
     */
    function submitRisk(
        bytes32 poolId,
        uint16 score,
        uint256 timestamp,
        bytes calldata signature,
        bytes32 cidHash,
        uint256 nonce
    ) external {
        require(score <= 100, "Score must be 0-100");
        require(timestamp <= block.timestamp + 300, "Timestamp too far in future");
        require(timestamp >= block.timestamp - 3600, "Timestamp too old");

        // Verify signature
        bytes32 dataHash = keccak256(
            abi.encodePacked(poolId, score, timestamp, cidHash, nonce)
        );
        bytes32 ethSignedMessageHash = dataHash.toEthSignedMessageHash();
        address recoveredSigner = ethSignedMessageHash.recover(signature);

        require(recoveredSigner == authorizedSigner, "Invalid signature");

        // Check nonce (must be greater than last used)
        require(nonce > lastNonce[recoveredSigner][poolId], "Nonce already used");
        lastNonce[recoveredSigner][poolId] = nonce;

        // Store risk data
        latestRisk[poolId] = RiskData({
            score: score,
            timestamp: timestamp,
            cidHash: cidHash,
            nonce: nonce
        });

        emit RiskUpdated(poolId, score, timestamp, cidHash);
    }

    /**
     * @dev Get latest risk for a pool
     * @param poolId Pool identifier
     * @return score Risk score
     * @return timestamp Timestamp
     * @return cidHash IPFS CID hash
     */
    function getLatestRisk(bytes32 poolId)
        external
        view
        returns (
            uint16 score,
            uint256 timestamp,
            bytes32 cidHash
        )
    {
        RiskData memory data = latestRisk[poolId];
        return (data.score, data.timestamp, data.cidHash);
    }

    /**
     * @dev Update authorized signer (only owner)
     * @param newSigner New signer address
     */
    function updateAuthorizedSigner(address newSigner) external onlyOwner {
        require(newSigner != address(0), "Invalid signer address");
        address oldSigner = authorizedSigner;
        authorizedSigner = newSigner;
        emit SignerUpdated(oldSigner, newSigner);
    }

    /**
     * @dev Check if risk data is stale
     * @param poolId Pool identifier
     * @param maxAge Maximum age in seconds
     * @return isStale True if data is older than maxAge
     */
    function isRiskStale(bytes32 poolId, uint256 maxAge)
        external
        view
        returns (bool)
    {
        uint256 dataTimestamp = latestRisk[poolId].timestamp;
        if (dataTimestamp == 0) return true;
        return (block.timestamp - dataTimestamp) > maxAge;
    }
}
