// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./VeriRiskOracle.sol";

/**
 * @title ConsumerDemo
 * @dev Demo contract that consumes risk data and takes automated actions
 */
contract ConsumerDemo {
    VeriRiskOracle public oracle;
    
    // Pool state
    mapping(bytes32 => bool) public isPaused;
    mapping(bytes32 => uint16) public collateralFactor;  // Percentage (100 = 1x)
    
    // Configuration
    uint16 public pauseThreshold = 75;      // Pause if risk > 75
    uint16 public collateralThreshold = 60; // Increase collateral if risk > 60
    
    // Events
    event PoolPaused(bytes32 indexed poolId, uint16 riskScore);
    event PoolUnpaused(bytes32 indexed poolId);
    event CollateralFactorUpdated(bytes32 indexed poolId, uint16 oldFactor, uint16 newFactor);
    event ActionSimulated(bytes32 indexed poolId, string action, uint16 riskScore);
    
    constructor(address _oracleAddress) {
        oracle = VeriRiskOracle(_oracleAddress);
    }
    
    /**
     * @dev Check risk and take action for a pool
     * @param poolId Pool identifier
     */
    function checkAndAct(bytes32 poolId) external {
        (uint16 score, uint256 timestamp, ) = oracle.getLatestRisk(poolId);
        
        require(timestamp > 0, "No risk data available");
        require(!oracle.isRiskStale(poolId, 3600), "Risk data is stale");
        
        if (score >= pauseThreshold && !isPaused[poolId]) {
            _pausePool(poolId, score);
        } else if (score < pauseThreshold && isPaused[poolId]) {
            _unpausePool(poolId);
        }
        
        if (score >= collateralThreshold) {
            _adjustCollateral(poolId, score);
        }
    }
    
    /**
     * @dev Simulate action without executing (for demo)
     * @param poolId Pool identifier
     * @return action Description of action that would be taken
     */
    function simulateAction(bytes32 poolId) 
        external 
        view 
        returns (string memory action, uint16 riskScore) 
    {
        (uint16 score, uint256 timestamp, ) = oracle.getLatestRisk(poolId);
        
        if (timestamp == 0) {
            return ("NO_DATA", 0);
        }
        
        if (oracle.isRiskStale(poolId, 3600)) {
            return ("STALE_DATA", score);
        }
        
        if (score >= pauseThreshold && !isPaused[poolId]) {
            return ("PAUSE_POOL", score);
        } else if (score < pauseThreshold && isPaused[poolId]) {
            return ("UNPAUSE_POOL", score);
        } else if (score >= collateralThreshold) {
            return ("INCREASE_COLLATERAL", score);
        } else {
            return ("NO_ACTION_NEEDED", score);
        }
    }
    
    function _pausePool(bytes32 poolId, uint16 score) internal {
        isPaused[poolId] = true;
        emit PoolPaused(poolId, score);
        emit ActionSimulated(poolId, "PAUSED", score);
    }
    
    function _unpausePool(bytes32 poolId) internal {
        isPaused[poolId] = false;
        emit PoolUnpaused(poolId);
    }
    
    function _adjustCollateral(bytes32 poolId, uint16 score) internal {
        uint16 oldFactor = collateralFactor[poolId];
        // Increase collateral factor based on risk
        uint16 newFactor = 100 + (score - 50); // Example formula
        if (newFactor > 200) newFactor = 200;  // Cap at 2x
        
        if (newFactor != oldFactor) {
            collateralFactor[poolId] = newFactor;
            emit CollateralFactorUpdated(poolId, oldFactor, newFactor);
        }
    }
    
    /**
     * @dev Update thresholds (for demo/testing)
     */
    function updateThresholds(uint16 _pauseThreshold, uint16 _collateralThreshold) external {
        pauseThreshold = _pauseThreshold;
        collateralThreshold = _collateralThreshold;
    }
}
