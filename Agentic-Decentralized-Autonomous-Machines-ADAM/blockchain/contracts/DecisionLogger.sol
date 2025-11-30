// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./CrewRegistry.sol";
import "./GovernanceRules.sol";

/**
 * @title DecisionLogger
 * @notice Immutable audit trail for crew decisions with conflict resolution
 * @dev Stores decision hashes, handles same-event detection and severity escalation
 */
contract DecisionLogger {
    // ==================== Enums ====================

    enum DecisionType {
        CrewFormation,
        AnomalyDetection,
        ActionExecution
    }
    enum SeverityLevel {
        Safe,
        Warning,
        Critical
    }

    // ==================== Structs ====================

    struct Decision {
        uint256 decisionId; // Unique decision ID
        uint256 crewId; // Crew that made decision
        bytes32 decisionHash; // Hash of decision data (off-chain)
        DecisionType decisionType; // Type of decision
        SeverityLevel severity; // Severity assessment
        uint256 methanePpm; // Methane reading
        uint256 timestamp; // Decision timestamp
        address[] voters; // Agents who voted
        bool executed; // Whether action was executed
        uint256 executedAt; // Execution timestamp
        string notes; // Optional notes/explanation
    }

    struct ConflictResolution {
        uint256[] conflictingDecisions; // Decision IDs in conflict
        uint256 resolvedDecisionId; // Final decision chosen
        SeverityLevel finalSeverity; // Resolved severity
        uint256 resolvedAt; // Resolution timestamp
        string resolutionReason; // Explanation
    }

    // ==================== State Variables ====================

    CrewRegistry public crewRegistry;
    GovernanceRules public governanceRules;

    /// @notice Mapping from decision ID to Decision
    mapping(uint256 => Decision) public decisions;

    /// @notice Decision counter
    uint256 public decisionCounter;

    /// @notice Mapping from event hash to decision IDs (detect conflicts)
    mapping(bytes32 => uint256[]) public eventDecisions;

    /// @notice Mapping from decision ID to conflict resolution
    mapping(uint256 => ConflictResolution) public conflicts;

    /// @notice Nonce for each agent (prevents replay attacks)
    mapping(address => uint256) public agentNonces;

    // ==================== Events ====================

    event DecisionLogged(
        uint256 indexed decisionId,
        uint256 indexed crewId,
        bytes32 decisionHash,
        DecisionType decisionType,
        SeverityLevel severity,
        uint256 methanePpm,
        uint256 timestamp
    );

    event DecisionExecuted(uint256 indexed decisionId, uint256 executedAt);

    event ConflictDetected(
        bytes32 indexed eventHash,
        uint256[] conflictingDecisions,
        uint256 timestamp
    );

    event ConflictResolved(
        bytes32 indexed eventHash,
        uint256 resolvedDecisionId,
        SeverityLevel finalSeverity,
        string reason
    );

    // ==================== Constructor ====================

    constructor(address _crewRegistry, address _governanceRules) {
        crewRegistry = CrewRegistry(_crewRegistry);
        governanceRules = GovernanceRules(_governanceRules);
        decisionCounter = 1;
    }

    // ==================== Core Functions ====================

    /**
     * @notice Log a new decision with replay protection
     * @param crewId ID of crew making decision
     * @param decisionHash Hash of off-chain decision data
     * @param decisionType Type of decision
     * @param severity Severity assessment
     * @param methanePpm Methane reading
     * @param voters Array of agent addresses who voted
     * @param signatures Array of signatures from voters (anti-replay)
     * @param notes Optional explanation
     * @return decisionId The ID of the logged decision
     */
    function logDecision(
        uint256 crewId,
        bytes32 decisionHash,
        DecisionType decisionType,
        SeverityLevel severity,
        uint256 methanePpm,
        address[] calldata voters,
        bytes[] calldata signatures,
        string calldata notes
    ) external returns (uint256) {
        require(
            voters.length == signatures.length,
            "Voters/signatures mismatch"
        );
        require(voters.length >= 4, "Need at least 4 voters");

        // Verify all voters are active agents in this crew
        address[] memory crewMembers = crewRegistry.getCrewMembers(crewId);
        for (uint256 i = 0; i < voters.length; i++) {
            require(crewRegistry.isActiveAgent(voters[i]), "Inactive agent");
            require(_isInCrew(voters[i], crewMembers), "Agent not in crew");

            // Verify signature and increment nonce (prevents replay)
            _verifySignatureAndIncrementNonce(
                voters[i],
                decisionHash,
                signatures[i]
            );
        }

        uint256 decisionId = decisionCounter++;

        decisions[decisionId] = Decision({
            decisionId: decisionId,
            crewId: crewId,
            decisionHash: decisionHash,
            decisionType: decisionType,
            severity: severity,
            methanePpm: methanePpm,
            timestamp: block.timestamp,
            voters: voters,
            executed: false,
            executedAt: 0,
            notes: notes
        });

        // Generate event hash for conflict detection
        bytes32 eventHash = _generateEventHash(methanePpm, block.timestamp);
        eventDecisions[eventHash].push(decisionId);

        emit DecisionLogged(
            decisionId,
            crewId,
            decisionHash,
            decisionType,
            severity,
            methanePpm,
            block.timestamp
        );

        // Check for conflicts with other crews
        if (eventDecisions[eventHash].length > 1) {
            _handleConflict(eventHash);
        }

        return decisionId;
    }

    /**
     * @notice Mark decision as executed
     * @param decisionId ID of decision to mark as executed
     */
    function markExecuted(uint256 decisionId) external {
        require(decisions[decisionId].timestamp > 0, "Decision not found");
        require(!decisions[decisionId].executed, "Already executed");

        decisions[decisionId].executed = true;
        decisions[decisionId].executedAt = block.timestamp;

        emit DecisionExecuted(decisionId, block.timestamp);
    }

    // ==================== Conflict Resolution ====================

    /**
     * @notice Handle conflict between multiple crews detecting same event
     * @param eventHash Hash identifying the event
     */
    function _handleConflict(bytes32 eventHash) internal {
        uint256[] storage conflictingIds = eventDecisions[eventHash];

        emit ConflictDetected(eventHash, conflictingIds, block.timestamp);

        // Resolution strategy:
        // 1. Escalate to highest severity
        // 2. If same severity, use first timestamp

        SeverityLevel highestSeverity = SeverityLevel.Safe;
        uint256 earliestDecision = conflictingIds[0];
        uint256 earliestTimestamp = decisions[conflictingIds[0]].timestamp;

        for (uint256 i = 0; i < conflictingIds.length; i++) {
            Decision storage dec = decisions[conflictingIds[i]];

            // Update highest severity
            if (uint8(dec.severity) > uint8(highestSeverity)) {
                highestSeverity = dec.severity;
                earliestDecision = conflictingIds[i];
                earliestTimestamp = dec.timestamp;
            } else if (
                dec.severity == highestSeverity &&
                dec.timestamp < earliestTimestamp
            ) {
                // Same severity, use earlier timestamp
                earliestDecision = conflictingIds[i];
                earliestTimestamp = dec.timestamp;
            }
        }

        // Store conflict resolution
        conflicts[earliestDecision] = ConflictResolution({
            conflictingDecisions: conflictingIds,
            resolvedDecisionId: earliestDecision,
            finalSeverity: highestSeverity,
            resolvedAt: block.timestamp,
            resolutionReason: "Escalated to highest severity; first timestamp wins"
        });

        emit ConflictResolved(
            eventHash,
            earliestDecision,
            highestSeverity,
            "Escalated to highest severity; first timestamp wins"
        );
    }

    /**
     * @notice Generate event hash for detecting same events
     * @param methanePpm Methane reading
     * @param timestamp Event timestamp
     * @return Hash identifying the event window
     */
    function _generateEventHash(
        uint256 methanePpm,
        uint256 timestamp
    ) internal view returns (bytes32) {
        // Round timestamp to event window (e.g., 30-second buckets)
        uint256 window = governanceRules.sameEventWindow();
        uint256 roundedTimestamp = (timestamp / window) * window;

        // Events with similar timestamps and readings are considered "same"
        return keccak256(abi.encodePacked(roundedTimestamp));
    }

    // ==================== Helper Functions ====================

    /**
     * @notice Check if agent is in crew
     */
    function _isInCrew(
        address agent,
        address[] memory crewMembers
    ) internal pure returns (bool) {
        for (uint256 i = 0; i < crewMembers.length; i++) {
            if (crewMembers[i] == agent) return true;
        }
        return false;
    }

    /**
     * @notice Verify signature and increment nonce (anti-replay)
     * @param signer Expected signer address
     * @param messageHash Hash of message
     * @param signature Signature bytes
     */
    function _verifySignatureAndIncrementNonce(
        address signer,
        bytes32 messageHash,
        bytes memory signature
    ) internal {
        uint256 nonce = agentNonces[signer];

        // Create message with nonce
        bytes32 ethSignedHash = keccak256(
            abi.encodePacked(
                "\x19Ethereum Signed Message:\n32",
                keccak256(abi.encodePacked(messageHash, nonce))
            )
        );

        // Recover signer
        address recovered = _recoverSigner(ethSignedHash, signature);
        require(recovered == signer, "Invalid signature");

        // Increment nonce (prevents replay)
        agentNonces[signer]++;
    }

    /**
     * @notice Recover signer from signature
     */
    function _recoverSigner(
        bytes32 ethSignedHash,
        bytes memory signature
    ) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        return ecrecover(ethSignedHash, v, r, s);
    }

    // ==================== View Functions ====================

    /**
     * @notice Get decision details
     * @param decisionId ID of decision
     * @return Decision struct
     */
    function getDecision(
        uint256 decisionId
    ) external view returns (Decision memory) {
        return decisions[decisionId];
    }

    /**
     * @notice Get all decisions for an event
     * @param eventHash Hash of event
     * @return Array of decision IDs
     */
    function getEventDecisions(
        bytes32 eventHash
    ) external view returns (uint256[] memory) {
        return eventDecisions[eventHash];
    }

    /**
     * @notice Get conflict resolution for a decision
     * @param decisionId ID of decision
     * @return ConflictResolution struct
     */
    function getConflictResolution(
        uint256 decisionId
    ) external view returns (ConflictResolution memory) {
        return conflicts[decisionId];
    }

    /**
     * @notice Get current nonce for agent (for signing)
     * @param agent Address of agent
     * @return Current nonce
     */
    function getNonce(address agent) external view returns (uint256) {
        return agentNonces[agent];
    }
}
