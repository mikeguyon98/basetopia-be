from dotenv import load_dotenv
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from app.ml.highlight_tool import (
    is_valid_team,
    get_team_names,
    get_similar_players,
    is_valid_player,
    get_player_id,
    get_team_id
)
from app.ml.output_schema import TagResponse

load_dotenv()

# Define our agent state.
# In this case our state will have the conversation history under "messages"
# and the final structured output under "structured_response".
class AgentState(MessagesState):
    structured_response: TagResponse

# Initialize our base model.
base_model = ChatOpenAI(model="o3-mini")  # Replace 'gpt-4o' with your model identifier

prompt = '''You are tasked with tagging a post with the most relevant players and teams.
You will be given a post and should use the tools to find the most relevant players and teams. If there are no players or teams in the post, return an empty list.
You should return the player ids and the team ids not their names.

Remember to only return the player ids and team ids, not their names.

Only include the player ids and team ids that you were able to verify and find ids for. If you are not able to find an id, do not include it.
'''

# Define our tools.
tools = [is_valid_team, get_team_names, get_similar_players, is_valid_player, get_player_id, get_team_id]

# Create the ReAct agent with structured output.
# Here, response_format is set to AgentResponse so that a second LLM call will produce
# a structured response conforming to that schema.
graph_agent = create_react_agent(
    model=base_model,
    tools=tools,
    prompt=prompt,
    response_format=TagResponse,
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
    response = {'title': 'LA Angels Video Highlights', 'highlights': [{'video_url': 'https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/03/02fd2609-775bd74a-064d9423-csvm-diamondx64-asset_1280x720_59_4000K.mp4', 'description': "Angels vs. A's Highlights"}, {'video_url': 'https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/21/54e0f24c-8f67ef55-0cd52191-csvm-diamondx64-asset_1280x720_59_4000K.mp4', 'description': "Angels vs. A's Highlights"}, {'video_url': 'https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/04/0e94165c-e313b348-e46d33e7-csvm-diamondx64-asset_1280x720_59_4000K.mp4', 'description': "Angels vs. A's Highlights"}, {'video_url': 'https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/02/cbc02c7b-7ea8720e-783b9afb-csvm-diamondx64-asset_1280x720_59_4000K.mp4', 'description': "Angels vs. A's Highlights"}, {'video_url': 'https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/19/9b3455fb-99238209-3424ac1b-csvm-diamondx64-asset_1280x720_59_4000K.mp4', 'description': "Angels vs. A's Highlights"}], 'content': "Here are the latest highlights featuring the LA Angels. Enjoy the most exciting moments from their recent games:\n\n1. **[Angels vs. A's Highlights](https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/03/02fd2609-775bd74a-064d9423-csvm-diamondx64-asset_1280x720_59_4000K.mp4)** \n2. **[Angels vs. A's Highlights](https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/21/54e0f24c-8f67ef55-0cd52191-csvm-diamondx64-asset_1280x720_59_4000K.mp4)**\n3. **[Angels vs. A's Highlights](https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/04/0e94165c-e313b348-e46d33e7-csvm-diamondx64-asset_1280x720_59_4000K.mp4)**\n4. **[Angels vs. A's Highlights](https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/02/cbc02c7b-7ea8720e-783b9afb-csvm-diamondx64-asset_1280x720_59_4000K.mp4)**\n5. **[Angels vs. A's Highlights](https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-07/19/9b3455fb-99238209-3424ac1b-csvm-diamondx64-asset_1280x720_59_4000K.mp4)** \n\nDive into the action and witness the skill and passion of the LA Angels!"}

    user_query = f"{response}"
    response = run_agent(user_query)
    print("RESPONSE:\n")
    print(response)