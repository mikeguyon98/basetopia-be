from dotenv import load_dotenv
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from app.ml.highlight_tool import (
    get_highlight_docs,
    get_team_highlights,
    is_valid_team,
    get_team_names
)
from app.ml.output_schema import AgentResponse

load_dotenv()

# Define our agent state.
# In this case our state will have the conversation history under "messages"
# and the final structured output under "structured_response".
class AgentState(MessagesState):
    structured_response: AgentResponse

# Initialize our base model.
base_model = ChatOpenAI(model="gpt-4o")  # Replace 'gpt-4o' with your model identifier

prompt = '''You are a helpful assistant with several tools at your disposal.
You can use the following tools to help you with your task:
- get_highlight_docs: This tool allows you to get highlights for a specific team.
- get_team_highlights: This tool allows you to get highlights for a specific team.
- is_valid_team: This tool allows you to check if a team is valid.
- get_team_names: This tool allows you to get a list of valid team names.

If a user is asking about highlights in general or player highlights use the get_highlight_docs tool.
If a user would like team highlights, first see what the list of teams are using the get_team_names tool.
Then find whichever team name is most similar and verify it is a valid team using the is_valid_team tool.
Then use the get_team_highlights tool to get the highlights for that team.
If at any point you encounter an error, default to the get_highlight_docs tool.
'''

# Define our tools.
tools = [get_highlight_docs, get_team_highlights, is_valid_team, get_team_names]

# Create the ReAct agent with structured output.
# Here, response_format is set to AgentResponse so that a second LLM call will produce
# a structured response conforming to that schema.
graph_agent = create_react_agent(
    model=base_model,
    tools=tools,
    prompt=prompt,
    response_format=AgentResponse,
)

def call_agent(state: AgentState) -> dict:
    """
    This node calls our prebuilt ReAct agent.
    
    We pass a dict with the key "messages" containing our conversation history.
    The ReAct agent returns a dict containing both an updated conversation history
    and a final structured output in the key "structured_response".
    """
    inputs = {"messages": state["messages"]}
    result = graph_agent.invoke(inputs)
    return result

def build_graph():
    """
    Build a minimal graph with a single node that calls our ReAct agent.
    """
    workflow = StateGraph(AgentState)
    # Add the node that calls our agent.
    workflow.add_node("agent", call_agent)
    # Set the entrypoint for the graph.
    workflow.set_entry_point("agent")
    # Connect our "agent" node to the END.
    workflow.add_edge("agent", END)
    compiled = workflow.compile()
    return compiled

def run_agent(user_query: str) -> dict:
    """
    Start with a conversation containing a single user message (as a tuple).
    Then invoke the workflow, and return the final structured output.
    """
    # Per the guide, we pass messages as a list of (role, text) tuples.
    messages = [("user", user_query)]
    state = {"messages": messages}

    try:
        graph_wf = build_graph()
        result = graph_wf.invoke(state)
        # The ReAct agent returns our structured output under "structured_response"
        final_output = result.get("structured_response")
        # If AgentResponse is a Pydantic model, dump to a dictionary.
        if hasattr(final_output, "model_dump"):
            return final_output.model_dump()
        return final_output
    except Exception as e:
        print("Error:", e)
        return {"error": str(e)}

if __name__ == "__main__":
    user_query = "I would like to see LA Angels highlights"
    response = run_agent(user_query)
    print("RESPONSE:\n")
    print(response)