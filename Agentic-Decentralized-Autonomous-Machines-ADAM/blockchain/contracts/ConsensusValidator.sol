// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./CrewRegistry.sol";
import "./GovernanceRules.sol";

/**
 * @title ConsensusValidator
 * @notice Validates crew decisions through consensus (simple majority or weighted)
 * @dev Byzantine fault tolerant consensus with reputation weighting option
 */
contract ConsensusValidator {
    // ==================== Structs ====================

    struct Vote {
        address voter;
        bool approved;
        uint256 weight; // Reputation weight (if weighted voting enabled)
        uint256 timestamp;
    }

    struct ConsensusRequest {
        uint256 requestId;
        uint256 crewId;
        bytes32 proposalHash;
        address[] eligibleVoters;
        Vote[] votes;
        bool finalized;
        bool passed;
        uint256 createdAt;
    }

    // ==================== State Variables ====================

    CrewRegistry public crewRegistry;
    GovernanceRules public governanceRules;

    /// @notice Mapping from request ID to ConsensusRequest
    mapping(uint256 => ConsensusRequest) public consensusRequests;

    /// @notice Request counter
    uint256 public requestCounter;

    /// @notice Track if voter has voted (requestId => voter => hasVoted)
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    // ==================== Events ====================

    event ConsensusRequested(
        uint256 indexed requestId,
        uint256 indexed crewId,
        bytes32 proposalHash,
        address[] eligibleVoters,
        uint256 timestamp
    );

    event VoteCast(
        uint256 indexed requestId,
        address indexed voter,
        bool approved,
        uint256 weight
    );

    event ConsensusReached(
        uint256 indexed requestId,
        bool passed,
        uint256 approvalVotes,
        uint256 totalVotes,
        uint256 timestamp
    );

    event ConsensusFailed(
        uint256 indexed requestId,
        uint256 approvalVotes,
        uint256 requiredVotes,
        uint256 timestamp
    );

    // ==================== Constructor ====================

    constructor(address _crewRegistry, address _governanceRules) {
        crewRegistry = CrewRegistry(_crewRegistry);
        governanceRules = GovernanceRules(_governanceRules);
        requestCounter = 1;
    }

    // ==================== Core Functions ====================

    /**
     * @notice Request consensus validation from crew
     * @param crewId ID of crew to validate
     * @param proposalHash Hash of proposal to validate
     * @return requestId The ID of the consensus request
     */
    function requestConsensus(
        uint256 crewId,
        bytes32 proposalHash
    ) external returns (uint256) {
        address[] memory members = crewRegistry.getCrewMembers(crewId);
        require(members.length > 0, "Invalid crew");

        uint256 requestId = requestCounter++;

        consensusRequests[requestId].requestId = requestId;
        consensusRequests[requestId].crewId = crewId;
        consensusRequests[requestId].proposalHash = proposalHash;
        consensusRequests[requestId].eligibleVoters = members;
        consensusRequests[requestId].finalized = false;
        consensusRequests[requestId].passed = false;
        consensusRequests[requestId].createdAt = block.timestamp;

        emit ConsensusRequested(
            requestId,
            crewId,
            proposalHash,
            members,
            block.timestamp
        );

        return requestId;
    }

    /**
     * @notice Cast vote on consensus request
     * @param requestId ID of consensus request
     * @param approved Whether voter approves
     */
    function castVote(uint256 requestId, bool approved) external {
        ConsensusRequest storage request = consensusRequests[requestId];

        require(!request.finalized, "Consensus already finalized");
        require(
            _isEligibleVoter(msg.sender, request.eligibleVoters),
            "Not eligible voter"
        );
        require(!hasVoted[requestId][msg.sender], "Already voted");
        require(crewRegistry.isActiveAgent(msg.sender), "Agent not active");

        // Get voter's weight (reputation score or 1 if simple voting)
        uint256 weight = governanceRules.weightedVotingEnabled()
            ? _getVoterWeight(msg.sender)
            : 1;

        // Record vote
        request.votes.push(
            Vote({
                voter: msg.sender,
                approved: approved,
                weight: weight,
                timestamp: block.timestamp
            })
        );

        hasVoted[requestId][msg.sender] = true;

        emit VoteCast(requestId, msg.sender, approved, weight);

        // Check if consensus reached
        _checkConsensus(requestId);
    }

    /**
     * @notice Check if consensus has been reached
     * @param requestId ID of consensus request
     */
    function _checkConsensus(uint256 requestId) internal {
        ConsensusRequest storage request = consensusRequests[requestId];

        if (request.finalized) return;

        // Calculate votes
        uint256 totalWeight = 0;
        uint256 approvalWeight = 0;

        for (uint256 i = 0; i < request.votes.length; i++) {
            totalWeight += request.votes[i].weight;
            if (request.votes[i].approved) {
                approvalWeight += request.votes[i].weight;
            }
        }

        // Get required consensus
        uint256 requiredWeight = governanceRules.weightedVotingEnabled()
            ? _calculateWeightedConsensus(request.eligibleVoters)
            : governanceRules.getRequiredConsensus(
                request.eligibleVoters.length
            );

        // Check if all voted or consensus reached
        bool allVoted = request.votes.length == request.eligibleVoters.length;
        bool consensusReached = approvalWeight >= requiredWeight;

        if (allVoted || consensusReached) {
            request.finalized = true;
            request.passed = consensusReached;

            if (consensusReached) {
                emit ConsensusReached(
                    requestId,
                    true,
                    approvalWeight,
                    totalWeight,
                    block.timestamp
                );
            } else {
                emit ConsensusFailed(
                    requestId,
                    approvalWeight,
                    requiredWeight,
                    block.timestamp
                );
            }
        }
    }

    /**
     * @notice Manually finalize consensus (if voting period expired)
     * @param requestId ID of consensus request
     */
    function finalizeConsensus(uint256 requestId) external {
        ConsensusRequest storage request = consensusRequests[requestId];

        require(!request.finalized, "Already finalized");
        require(
            block.timestamp > request.createdAt + 5 minutes,
            "Voting period not expired"
        );

        _checkConsensus(requestId);

        // Force finalize if still not finalized
        if (!request.finalized) {
            request.finalized = true;
            request.passed = false;

            emit ConsensusFailed(
                requestId,
                0,
                governanceRules.getRequiredConsensus(
                    request.eligibleVoters.length
                ),
                block.timestamp
            );
        }
    }

    // ==================== Helper Functions ====================

    /**
     * @notice Check if address is eligible voter
     */
    function _isEligibleVoter(
        address voter,
        address[] memory eligibleVoters
    ) internal pure returns (bool) {
        for (uint256 i = 0; i < eligibleVoters.length; i++) {
            if (eligibleVoters[i] == voter) return true;
        }
        return false;
    }

    /**
     * @notice Get voter weight based on reputation
     */
    function _getVoterWeight(address voter) internal view returns (uint256) {
        (, , , uint256 reputation, , , ) = crewRegistry.agents(voter);

        // Reputation is 0-1000, weight is 1-10
        // 0-100 reputation = weight 1
        // 900-1000 reputation = weight 10
        return 1 + (reputation / 100);
    }

    /**
     * @notice Calculate required consensus weight for weighted voting
     */
    function _calculateWeightedConsensus(
        address[] memory voters
    ) internal view returns (uint256) {
        uint256 totalWeight = 0;
        for (uint256 i = 0; i < voters.length; i++) {
            totalWeight += _getVoterWeight(voters[i]);
        }

        // Apply consensus percentage
        return (totalWeight * governanceRules.consensusPercentage() + 99) / 100;
    }

    // ==================== View Functions ====================

    /**
     * @notice Get consensus request details
     * @param requestId ID of request
     * @return ConsensusRequest struct
     */
    function getConsensusRequest(
        uint256 requestId
    )
        external
        view
        returns (
            uint256,
            uint256,
            bytes32,
            address[] memory,
            bool,
            bool,
            uint256
        )
    {
        ConsensusRequest storage request = consensusRequests[requestId];
        return (
            request.requestId,
            request.crewId,
            request.proposalHash,
            request.eligibleVoters,
            request.finalized,
            request.passed,
            request.createdAt
        );
    }

    /**
     * @notice Get all votes for a request
     * @param requestId ID of request
     * @return Array of Vote structs
     */
    function getVotes(uint256 requestId) external view returns (Vote[] memory) {
        return consensusRequests[requestId].votes;
    }

    /**
     * @notice Get current vote count
     * @param requestId ID of request
     * @return approvalCount, rejectionCount, totalWeight
     */
    function getVoteCount(
        uint256 requestId
    )
        external
        view
        returns (
            uint256 approvalCount,
            uint256 rejectionCount,
            uint256 totalWeight
        )
    {
        Vote[] storage votes = consensusRequests[requestId].votes;

        for (uint256 i = 0; i < votes.length; i++) {
            totalWeight += votes[i].weight;
            if (votes[i].approved) {
                approvalCount += votes[i].weight;
            } else {
                rejectionCount += votes[i].weight;
            }
        }
    }

    /**
     * @notice Check if consensus has passed
     * @param requestId ID of request
     * @return Whether consensus passed
     */
    function hasConsensusPassed(
        uint256 requestId
    ) external view returns (bool) {
        return consensusRequests[requestId].passed;
    }
}
