// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title GovernanceRules
 * @notice Stores and manages governance parameters for ADAM system
 * @dev Owner can update thresholds and policies
 */
contract GovernanceRules is Ownable {
    // ==================== State Variables ====================

    /// @notice Critical methane threshold (in ppm)
    uint256 public criticalThreshold;

    /// @notice Warning methane threshold (in ppm)
    uint256 public warningThreshold;

    /// @notice Time window for considering events as "same" (in seconds)
    uint256 public sameEventWindow;

    /// @notice Minimum crew size required for valid decisions
    uint256 public minCrewSize;

    /// @notice Consensus percentage required (e.g., 51 = 51%)
    uint256 public consensusPercentage;

    /// @notice Whether weighted voting by reputation is enabled
    bool public weightedVotingEnabled;

    /// @notice Minimum reputation score to participate
    uint256 public minReputationScore;

    // ==================== Events ====================

    event ThresholdUpdated(
        string thresholdType,
        uint256 oldValue,
        uint256 newValue
    );
    event PolicyUpdated(string policyName, bool enabled);
    event ConsensusPercentageUpdated(uint256 oldValue, uint256 newValue);

    // ==================== Constructor ====================

    constructor() Ownable(msg.sender) {
        criticalThreshold = 5000; // 5000 ppm
        warningThreshold = 3000; // 3000 ppm
        sameEventWindow = 30; // 30 seconds
        minCrewSize = 4; // 4 agents (sensor, aggregator, decision, coordinator)
        consensusPercentage = 51; // 51% = simple majority
        weightedVotingEnabled = false; // Start with simple voting
        minReputationScore = 0; // No minimum initially
    }

    // ==================== View Functions ====================

    /**
     * @notice Check if methane level is critical
     * @param methanePpm Methane concentration in ppm
     */
    function isCritical(uint256 methanePpm) external view returns (bool) {
        return methanePpm >= criticalThreshold;
    }

    /**
     * @notice Check if methane level requires warning
     * @param methanePpm Methane concentration in ppm
     */
    function isWarning(uint256 methanePpm) external view returns (bool) {
        return methanePpm >= warningThreshold && methanePpm < criticalThreshold;
    }

    /**
     * @notice Check if two timestamps are within same event window
     * @param timestamp1 First timestamp
     * @param timestamp2 Second timestamp
     */
    function isSameEventWindow(
        uint256 timestamp1,
        uint256 timestamp2
    ) external view returns (bool) {
        uint256 diff = timestamp1 > timestamp2
            ? timestamp1 - timestamp2
            : timestamp2 - timestamp1;
        return diff <= sameEventWindow;
    }

    /**
     * @notice Calculate required consensus count
     * @param totalVoters Total number of voters
     */
    function getRequiredConsensus(
        uint256 totalVoters
    ) external view returns (uint256) {
        // Ceiling division: (totalVoters * consensusPercentage + 99) / 100
        return (totalVoters * consensusPercentage + 99) / 100;
    }

    // ==================== Admin Functions ====================

    /**
     * @notice Update critical threshold
     * @param newThreshold New critical threshold in ppm
     */
    function updateCriticalThreshold(uint256 newThreshold) external onlyOwner {
        require(newThreshold > warningThreshold, "Critical must be > warning");
        uint256 oldValue = criticalThreshold;
        criticalThreshold = newThreshold;
        emit ThresholdUpdated("critical", oldValue, newThreshold);
    }

    /**
     * @notice Update warning threshold
     * @param newThreshold New warning threshold in ppm
     */
    function updateWarningThreshold(uint256 newThreshold) external onlyOwner {
        require(newThreshold < criticalThreshold, "Warning must be < critical");
        uint256 oldValue = warningThreshold;
        warningThreshold = newThreshold;
        emit ThresholdUpdated("warning", oldValue, newThreshold);
    }

    /**
     * @notice Update same event time window
     * @param newWindow New time window in seconds
     */
    function updateSameEventWindow(uint256 newWindow) external onlyOwner {
        require(
            newWindow > 0 && newWindow <= 300,
            "Window must be 1-300 seconds"
        );
        uint256 oldValue = sameEventWindow;
        sameEventWindow = newWindow;
        emit ThresholdUpdated("sameEventWindow", oldValue, newWindow);
    }

    /**
     * @notice Update minimum crew size
     * @param newSize New minimum crew size
     */
    function updateMinCrewSize(uint256 newSize) external onlyOwner {
        require(newSize >= 2, "Min crew size must be >= 2");
        uint256 oldValue = minCrewSize;
        minCrewSize = newSize;
        emit ThresholdUpdated("minCrewSize", oldValue, newSize);
    }

    /**
     * @notice Update consensus percentage
     * @param newPercentage New consensus percentage (1-100)
     */
    function updateConsensusPercentage(
        uint256 newPercentage
    ) external onlyOwner {
        require(newPercentage > 0 && newPercentage <= 100, "Must be 1-100");
        uint256 oldValue = consensusPercentage;
        consensusPercentage = newPercentage;
        emit ConsensusPercentageUpdated(oldValue, newPercentage);
    }

    /**
     * @notice Enable or disable weighted voting
     * @param enabled True to enable weighted voting
     */
    function setWeightedVoting(bool enabled) external onlyOwner {
        weightedVotingEnabled = enabled;
        emit PolicyUpdated("weightedVoting", enabled);
    }

    /**
     * @notice Update minimum reputation score
     * @param newScore New minimum reputation score
     */
    function updateMinReputationScore(uint256 newScore) external onlyOwner {
        uint256 oldValue = minReputationScore;
        minReputationScore = newScore;
        emit ThresholdUpdated("minReputationScore", oldValue, newScore);
    }
}
