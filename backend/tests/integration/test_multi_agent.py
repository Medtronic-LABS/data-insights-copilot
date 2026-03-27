import pytest
import asyncio
from backend.database.db import get_db_service
from backend.services.agent_service import get_agent_service, AgentService
from backend.models.schemas import ChatRequest, User

# Mark as async test
@pytest.mark.asyncio
async def test_multi_agent_flow():
    """
    Test the complete multi-agent flow:
    1. Create a new Agent in the DB.
    2. Assign a user to that Agent (RBAC).
    3. Instantiate AgentService for that Agent.
    4. Verify the agent has the correct config.
    """
    print("\n--- Starting Multi-Agent Integration Test ---")
    
    db = get_db_service()
    
    # 1. Create a Test User
    test_user = "test_agent_user"
    try:
        user = db.create_user(username=test_user, password="password123", role="user")
        user_id = user['id']
        print(f"✅ Created test user: {test_user} (ID: {user_id})")
    except ValueError:
        # User might already exist from previous runs
        user_rec = db.get_user_by_username(test_user)
        user_id = user_rec['id']
        print(f"ℹ️ User {test_user} already exists (ID: {user_id})")

    # 2. Create a Test Agent
    agent_name = "Test Sales Agent"
    try:
        agent = db.create_agent(
            name=agent_name,
            description="Agent for sales data",
            agent_type="sql",
            db_connection_uri="sqlite:///sales_test.db", # Mock URI
            system_prompt="You are a sales expert.",
            created_by=user_id
        )
        agent_id = agent['id']
        print(f"✅ Created test agent: {agent_name} (ID: {agent_id})")
    except ValueError:
        # Agent might exist
        # Need to find it - db.get_agents_for_user might work if we have access
        # For now, let's just assume we can't easily find it without a name search
        print(f"⚠️ Agent {agent_name} already exists. Skipping creation.")
        # We need the ID. Let's list agents for the user.
        agents = db.get_agents_for_user(user_id)
        target = next((a for a in agents if a['name'] == agent_name), None)
        if target:
            agent_id = target['id']
            print(f"ℹ️ Found existing agent ID: {agent_id}")
        else:
            raise Exception("Could not find existing agent ID")

    # 3. Verify RBAC (Creator should be Admin)
    has_access = db.check_user_access(user_id, agent_id, required_role='admin')
    assert has_access == True
    print(f"✅ RBAC Check Passed: User {user_id} is Admin of Agent {agent_id}")

    # 4. Instantiate AgentService
    try:
        service = get_agent_service(agent_id=agent_id, user_id=user_id)
        print(f"✅ Instantiated AgentService for Agent {agent_id}")
        
        # Verify config was loaded
        assert service.agent_config['id'] == agent_id
        assert service.fixed_system_prompt == "You are a sales expert."
        print(f"✅ AgentService Config Verified: System Prompt matches")
        
    except Exception as e:
        print(f"❌ Failed to instantiate AgentService: {e}")
        raise

    # 5. Test Access Denial
    other_user = "unauthorized_user"
    try:
        u2 = db.create_user(username=other_user, password="password123")
        u2_id = u2['id']
    except ValueError:
        u2_rec = db.get_user_by_username(other_user)
        u2_id = u2_rec['id']
        
    try:
        get_agent_service(agent_id=agent_id, user_id=u2_id)
        print("❌ RBAC Failed: Unauthorized user was able to get agent service")
    except PermissionError:
        print(f"✅ RBAC Check Passed: Unauthorized user {u2_id} was correctly denied access")

    # 6. Test Listing Agents (mimicking API)
    user_agents = db.get_agents_for_user(user_id)
    print(f"✅ Found {len(user_agents)} agents for user {user_id}")
    assert len(user_agents) >= 1
    found_agent = next((a for a in user_agents if a['id'] == agent_id), None)
    assert found_agent is not None
    assert found_agent['name'] == agent_name
    print(f"✅ Verified agent '{agent_name}' is in user's list")

    print("\n--- Test Completed Successfully ---")

if __name__ == "__main__":
    asyncio.run(test_multi_agent_flow())
