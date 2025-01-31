from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from app.ml.highlight_tool import (
    get_highlight_docs,
    get_team_highlights,
    is_valid_team,
)
from app.ml.output_schema import AgentResponse
from langgraph.graph import MessagesState
from dotenv import load_dotenv

load_dotenv()
# Define the agent's state
class AgentState(MessagesState):
    # Final structured response from the agent
    final_response: AgentResponse

# Initialize the base model
base_model = ChatOpenAI(model="gpt-4o")  # Replace 'gpt-4' with your model

# Define tools
tools = [get_highlight_docs, get_team_highlights, is_valid_team]

# Initialize the models
# Model for reasoning and tool calling
model_with_tools = base_model.bind_tools(tools)

# Model for structured output
model_with_structured_output = base_model.with_structured_output(AgentResponse)

# Define graph node functions
def call_model(state: AgentState) -> dict:
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def respond(state: AgentState) -> dict:
    # Use the model with structured output on the last tool's output
    # Find the last ToolMessage content
    last_tool_message_content = None
    for message in reversed(state["messages"]):
        if message.type == "tool":
            last_tool_message_content = message.content
            break

    if last_tool_message_content is None:
        raise ValueError("No ToolMessage found in the messages.")

    # Use the content of the last ToolMessage as input
    response = model_with_structured_output.invoke(
        [HumanMessage(content=last_tool_message_content)]
    )
    return {"final_response": response}

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    else:
        return "respond"

def build_graph():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("respond", respond)
    workflow.add_node("tools", ToolNode(tools))

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "respond": "respond",
        },
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("respond", END)

    # Compile the graph
    highlight_agent = workflow.compile()
    return highlight_agent

# Function to run the agent
def run_agent(user_query: str) -> dict:
    # Initialize messages
    messages = [("user", user_query)]

    # Invoke the agent
    try:
        highlight_agent = build_graph()
        result = highlight_agent.invoke({"messages": messages})

        # Get the final structured response
        structured_response = result["final_response"]

        # Convert to dictionary
        response_dict = structured_response.model_dump()

        return response_dict
    except Exception as e:
        # Handle exceptions (e.g., validation errors)
        print(f"Error: {e}")
        return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    load_dotenv()
    # user_query = "Show me the latest highlights for the LA Angels"
    user_query = "I would like to see Kyle Hendricks highlights"
    response = run_agent(user_query)
    print("RESPONSE: \n\n\n")
    print(response)