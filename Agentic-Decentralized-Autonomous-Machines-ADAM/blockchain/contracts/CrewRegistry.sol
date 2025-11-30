// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CrewRegistry
 * @notice Manages agent registration, crew formation, and reputation
 * @dev Implements hybrid identity (node address + role) with anti-Sybil protection
 */
contract CrewRegistry is Ownable {
    // ==================== Enums ====================

    enum AgentRole {
        Sensor,
        Aggregator,
        Decision,
        Coordinator
    }
    enum AgentStatus {
        Inactive,
        Active,
        Suspended
    }

    // ==================== Structs ====================

    struct Agent {
        address nodeAddress; // Raspberry Pi Ethereum address
        AgentRole role; // Agent's role in crew
        AgentStatus status; // Current status
        uint256 reputationScore; // Reputation (0-1000)
        uint256 registeredAt; // Registration timestamp
        uint256 totalDecisions; // Total decisions participated in
        uint256 correctDecisions; // Correct decisions (updated post-validation)
    }

    struct Crew {
        uint256 crewId; // Unique crew identifier
        bytes32 eventId; // Event hash (for deduplication)
        uint256 timestamp; // Crew formation timestamp
        address[] members; // Agent addresses in crew
        bool active; // Whether crew is still active
        uint256 methanePpm; // Methane level that triggered formation
    }

    // ==================== State Variables ====================

    /// @notice Mapping from agent address to Agent struct
    mapping(address => Agent) public agents;

    /// @notice Array of all registered agent addresses
    address[] public agentList;

    /// @notice Mapping from crew ID to Crew struct
    mapping(uint256 => Crew) public crews;

    /// @notice Counter for crew IDs
    uint256 public crewCounter;

    /// @notice Mapping from node address to count of active agents (anti-Sybil)
    mapping(address => uint256) public nodeAgentCount;

    /// @notice Maximum agents per node (prevents Sybil attacks)
    uint256 public constant MAX_AGENTS_PER_NODE = 8; // 2 crews * 4 agents

    /// @notice Mapping to track active crews per node
    mapping(address => uint256) public nodeActiveCrews;

    // ==================== Events ====================

    event AgentRegistered(
        address indexed agentAddress,
        address indexed nodeAddress,
        AgentRole role
    );

    event AgentStatusUpdated(
        address indexed agentAddress,
        AgentStatus oldStatus,
        AgentStatus newStatus
    );

    event CrewFormed(
        uint256 indexed crewId,
        bytes32 indexed eventId,
        address[] members,
        uint256 methanePpm,
        uint256 timestamp
    );

    event CrewDissolved(uint256 indexed crewId, uint256 timestamp);

    event ReputationUpdated(
        address indexed agentAddress,
        uint256 oldScore,
        uint256 newScore
    );

    // ==================== Modifiers ====================

    modifier onlyRegistered(address agentAddress) {
        require(
            agents[agentAddress].status != AgentStatus.Inactive,
            "Agent not registered"
        );
        _;
    }

    modifier onlyActive(address agentAddress) {
        require(
            agents[agentAddress].status == AgentStatus.Active,
            "Agent not active"
        );
        _;
    }

    // ==================== Constructor ====================

    constructor() Ownable(msg.sender) {
        crewCounter = 1; // Start from 1
    }

    // ==================== Agent Management ====================

    /**
     * @notice Register a new agent (pre-registration by owner)
     * @param agentAddress Unique address for this agent instance
     * @param nodeAddress Address of the Raspberry Pi node
     * @param role Agent's role
     */
    function registerAgent(
        address agentAddress,
        address nodeAddress,
        AgentRole role
    ) external onlyOwner {
        require(
            agents[agentAddress].status == AgentStatus.Inactive,
            "Agent already registered"
        );
        require(
            nodeAgentCount[nodeAddress] < MAX_AGENTS_PER_NODE,
            "Node agent limit reached"
        );

        agents[agentAddress] = Agent({
            nodeAddress: nodeAddress,
            role: role,
            status: AgentStatus.Active,
            reputationScore: 500, // Start at middle reputation
            registeredAt: block.timestamp,
            totalDecisions: 0,
            correctDecisions: 0
        });

        agentList.push(agentAddress);
        nodeAgentCount[nodeAddress]++;

        emit AgentRegistered(agentAddress, nodeAddress, role);
    }

    /**
     * @notice Batch register multiple agents (for initial setup)
     * @param agentAddresses Array of agent addresses
     * @param nodeAddresses Array of corresponding node addresses
     * @param roles Array of corresponding roles
     */
    function batchRegisterAgents(
        address[] calldata agentAddresses,
        address[] calldata nodeAddresses,
        AgentRole[] calldata roles
    ) external onlyOwner {
        require(
            agentAddresses.length == nodeAddresses.length &&
                agentAddresses.length == roles.length,
            "Array length mismatch"
        );

        for (uint256 i = 0; i < agentAddresses.length; i++) {
            if (
                agents[agentAddresses[i]].status == AgentStatus.Inactive &&
                nodeAgentCount[nodeAddresses[i]] < MAX_AGENTS_PER_NODE
            ) {
                agents[agentAddresses[i]] = Agent({
                    nodeAddress: nodeAddresses[i],
                    role: roles[i],
                    status: AgentStatus.Active,
                    reputationScore: 500,
                    registeredAt: block.timestamp,
                    totalDecisions: 0,
                    correctDecisions: 0
                });

                agentList.push(agentAddresses[i]);
                nodeAgentCount[nodeAddresses[i]]++;

                emit AgentRegistered(
                    agentAddresses[i],
                    nodeAddresses[i],
                    roles[i]
                );
            }
        }
    }

    /**
     * @notice Update agent status (for suspending malicious agents)
     * @param agentAddress Address of agent to update
     * @param newStatus New status
     */
    function updateAgentStatus(
        address agentAddress,
        AgentStatus newStatus
    ) external onlyOwner onlyRegistered(agentAddress) {
        AgentStatus oldStatus = agents[agentAddress].status;
        agents[agentAddress].status = newStatus;
        emit AgentStatusUpdated(agentAddress, oldStatus, newStatus);
    }

    // ==================== Crew Management ====================

    /**
     * @notice Form a new crew (called when anomaly detected)
     * @param eventId Hash of event (for deduplication)
     * @param members Array of agent addresses forming the crew
     * @param methanePpm Methane level that triggered formation
     * @return crewId The ID of the newly formed crew
     */
    function formCrew(
        bytes32 eventId,
        address[] calldata members,
        uint256 methanePpm
    ) external returns (uint256) {
        require(members.length >= 4, "Crew must have at least 4 agents");

        // Verify all members are active and check for duplicate roles
        bool[4] memory rolesPresent; // [Sensor, Aggregator, Decision, Coordinator]

        for (uint256 i = 0; i < members.length; i++) {
            require(
                agents[members[i]].status == AgentStatus.Active,
                "All members must be active"
            );

            uint256 roleIndex = uint256(agents[members[i]].role);
            rolesPresent[roleIndex] = true;
        }

        // Ensure all 4 roles are present
        require(
            rolesPresent[0] &&
                rolesPresent[1] &&
                rolesPresent[2] &&
                rolesPresent[3],
            "All 4 roles must be present"
        );

        uint256 crewId = crewCounter++;

        crews[crewId] = Crew({
            crewId: crewId,
            eventId: eventId,
            timestamp: block.timestamp,
            members: members,
            active: true,
            methanePpm: methanePpm
        });

        emit CrewFormed(crewId, eventId, members, methanePpm, block.timestamp);

        return crewId;
    }

    /**
     * @notice Dissolve a crew (after decision execution)
     * @param crewId ID of crew to dissolve
     */
    function dissolveCrew(uint256 crewId) external {
        require(crews[crewId].active, "Crew not active");
        crews[crewId].active = false;
        emit CrewDissolved(crewId, block.timestamp);
    }

    /**
     * @notice Get crew members
     * @param crewId ID of crew
     * @return Array of member addresses
     */
    function getCrewMembers(
        uint256 crewId
    ) external view returns (address[] memory) {
        return crews[crewId].members;
    }

    // ==================== Reputation Management ====================

    /**
     * @notice Update agent reputation after decision validation
     * @param agentAddress Address of agent
     * @param wasCorrect Whether the decision was correct
     */
    function updateReputation(
        address agentAddress,
        bool wasCorrect
    ) external onlyOwner onlyRegistered(agentAddress) {
        Agent storage agent = agents[agentAddress];
        uint256 oldScore = agent.reputationScore;

        agent.totalDecisions++;
        if (wasCorrect) {
            agent.correctDecisions++;
            // Increase reputation (max 1000)
            if (agent.reputationScore < 1000) {
                agent.reputationScore += (1000 - agent.reputationScore) / 10; // 10% of gap
            }
        } else {
            // Decrease reputation (min 0)
            if (agent.reputationScore > 0) {
                agent.reputationScore -= agent.reputationScore / 10; // 10% decrease
            }
        }

        emit ReputationUpdated(agentAddress, oldScore, agent.reputationScore);
    }

    /**
     * @notice Get agent accuracy percentage
     * @param agentAddress Address of agent
     * @return Accuracy as percentage (0-100)
     */
    function getAgentAccuracy(
        address agentAddress
    ) external view onlyRegistered(agentAddress) returns (uint256) {
        Agent memory agent = agents[agentAddress];
        if (agent.totalDecisions == 0) return 0;
        return (agent.correctDecisions * 100) / agent.totalDecisions;
    }

    /**
     * @notice Get all registered agents
     * @return Array of agent addresses
     */
    function getAllAgents() external view returns (address[] memory) {
        return agentList;
    }

    /**
     * @notice Check if address is registered and active
     * @param agentAddress Address to check
     * @return True if active agent
     */
    function isActiveAgent(address agentAddress) external view returns (bool) {
        return agents[agentAddress].status == AgentStatus.Active;
    }
}
