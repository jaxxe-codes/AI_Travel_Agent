## Travel Agent Project
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import AsyncOpenAI
from agents.exceptions import InputGuardrailTripwireTriggered
from agents import set_default_openai_client
from agents import Agent, Runner, function_tool, WebSearchTool, handoff, RunContextWrapper, ItemHelpers, MessageOutputItem, Runner, trace, GuardrailFunctionOutput,TResponseInputItem, input_guardrail, InputGuardrailTripwireTriggered, SQLiteSession
import requests
import asyncio
import streamlit as st
import pandas as pd

load_dotenv()
custom_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1", # Replace with your custom base URL
    api_key="OPENROUTER_API_KEY" # Your API key
)
set_default_openai_client(custom_client)

budget_agent = Agent(
    name="Budget Agent",
    model="gpt-4.1-mini",
    handoff_description="Specialist agent for Budget Planning",
    instructions="You are a budget planner, you will search the internet and provide the average event cost as well as daily cost for mentioned activities or dining in the given country, minimize the expense while ensuring the total cost of all activities is within the defined budget at all times, include flight cost and transport cost in the total budget planning.",
    tools=[WebSearchTool()]
)

planner_agent = Agent(
    name="Planner Agent",
    model="gpt-4.1-mini",
    handoff_description="Specialist agent for activity scheduling",
    instructions="You are a trip planner, you will search the internet and provide the approximate duration spend for mentioned activities or dining in the given country, ensure that the total time spend is within the depicted number of days, ensure to allocate sufficient time for rest or unexpected changes.",
    tools=[WebSearchTool()]
)

guide_agent = Agent(
    name="Local Guide Agent",
    model="gpt-4.1-mini",
    handoff_description="Specialist agent for identifying and providing the ratings for the most highly rated attractions or dining recommendations",
    instructions="You are a Guide Specialist, you will search the internet for the best rated tourist attraction activities or dining recommendations in the mentioned country.",
    tools=[WebSearchTool()]
)

travel_agent = Agent(
    name="Travel Agent",
    instructions=(
        """You are a helpful orchestrator agent. Your role is to analyze the user's question and determine which specialist agent (budget, planner, or guide) is best equipped to provide an answer.
         You must use the appropriate tool to ask the relevant specialist agent. If the question does not fit into these categories,
         provide a general helpful response. You should always aim to use one of the tutor tools if applicable.
         include the ratings for each activity in the itinerary.
         include the total daily expenses for each day in the itinerary.
         include each activity expenses in the itinerary.
         include the total time spend for each day in the itinerary.
         include the each activity time spend in the itinerary.
         assume the country of origin is Singapore.
         calculate all cost in SGD.
         """
    ),
    tools=[
        budget_agent.as_tool(
            tool_name="ask_budget_specialist",
            tool_description=budget_agent.handoff_description,
        ),
        planner_agent.as_tool(
            tool_name="ask_planner_specialist",
            tool_description=planner_agent.handoff_description,
        ),
        guide_agent.as_tool(
            tool_name="ask_activity_specialist",
            tool_description=guide_agent.handoff_description,
        ),
    ],
)
# session = SQLiteSession("conversation_123")
# topic = "Plan a 5-day trip to Tokyo under $2,000 with food recommendations"

# async def get_response():
#     itinerary = await Runner.run(travel_agent, topic, session=session)
#     return itinerary

# loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)
# itinerary = loop.run_until_complete(get_response())
# print(itinerary.final_output)


# application code

# Page config must be the first Streamlit command
st.set_page_config(
    page_title="AI Trip Planner", 
    page_icon="🤖", 
    layout="wide")

## init session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []

st.title("🤖 AI Trip Planner",False,text_alignment="left")
st.subheader("The only Travel Agent you will need!",False,text_alignment="left")

with st.form(key="Itinerary Generator Parameters", clear_on_submit=True, enter_to_submit=False, width="stretch"):
    with st.container(border=True, width="stretch"):
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            loc_input = st.selectbox(
                "Destination:",
                ["Tokyo"],
                index=None,
                placeholder="Where are you going?",
                accept_new_options=True,
                key="loc_input",
                width="stretch"
            )
            time_input = st.selectbox(
                "Duration of Travel (in Days):",
                [str(i) for i in range(1, 32)],
                index=None,
                placeholder="How long will the trip be?",
                accept_new_options=False,
                key="time_input",
                width="stretch"
            )
            budget_input = st.text_input("Total Trip Budget (SGD):", key="budget_input", width="stretch", placeholder="What is your trip budget limit?")
        preference_input = st.text_input("Special Preference:", key="preference_input", width="stretch", placeholder="Others...")
    with st.container(horizontal=True, horizontal_alignment="left"):
        submit_button = st.form_submit_button(label="Generate")
        new_chat_button = st.form_submit_button(label="New Chat")

## load chat history
if st.session_state.history != []:
    with st.expander(label="History", expanded=False):
        for message in st.session_state.history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

if st.session_state.messages != []:
    with st.expander(label="Results", expanded=True):
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

if submit_button and loc_input and time_input and budget_input:
    with st.spinner("Your dream itinerary is being generated..."):
        topic = "Plan a " + time_input + "-day trip to " + loc_input +" under $"+budget_input
        if preference_input:
            topic = topic + " with " + preference_input
        if len(st.session_state.messages) == 2:
            st.session_state.history.extend(st.session_state.messages)
            st.session_state.messages = []
        st.session_state.messages.append({"role": "user", "content": topic})
        async def get_response():
            result = await Runner.run(travel_agent, input=st.session_state.messages)
            return result
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_response())

        assistant_response = result.final_output
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        st.rerun()
    
if new_chat_button:
    st.write("Starting a new chat...")
    st.session_state.messages = []

    st.rerun()


