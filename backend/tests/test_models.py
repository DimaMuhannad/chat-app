from app.models import (
    ChatMessage,
    ChatRequest,
    ChatSession,
    ChatStreamChunk,
    ChatResponseType,
    MessageRole,
    ToolCallInfo,
    ToolResultInfo,
    AgentConfig,
    AgentStatus,
    AgentTask,
    AgentType,
    Artifact,
    ArtifactType,
)


def test_chat_models():
    session = ChatSession(title="Test Session", model="gemini-2.5-pro")
    assert session.id is not None
    assert session.title == "Test Session"

    msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content="Hello Agent!",
    )
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello Agent!"

    tool_call = ToolCallInfo(tool_name="bash", arguments={"command": "ls -la"})
    tool_msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="Listing directory",
        tool_calls=[tool_call],
    )
    assert tool_msg.tool_calls[0].tool_name == "bash"

    chunk = ChatStreamChunk(
        session_id=session.id,
        message_id=msg.id,
        type=ChatResponseType.TOKEN,
        content="Chunk data",
    )
    assert chunk.type == ChatResponseType.TOKEN


def test_agent_models():
    agent = AgentConfig(
        name="CodeAssistant",
        role="Developer",
        agent_type=AgentType.DEVELOPER,
        enabled_tools=["bash", "read_file", "write_file"],
    )
    assert agent.name == "CodeAssistant"
    assert agent.status is None or hasattr(agent, "model")

    task = AgentTask(
        agent_id=agent.id,
        title="Setup backend",
        description="Create basic FastAPI skeleton",
        status=AgentStatus.RUNNING,
    )
    assert task.status == AgentStatus.RUNNING

    artifact = Artifact(
        session_id="s1",
        name="test.py",
        artifact_type=ArtifactType.FILE,
        content="print('hello')",
    )
    assert artifact.artifact_type == ArtifactType.FILE
