# This module will be edited in Lab 03 to add the agent tools.
import boto3
from langchain.agents import Tool
# from langchain_aws import BedrockLLM
from langchain_aws import ChatBedrock

from langchain_community.tools import DuckDuckGoSearchRun
# from .calculator import CustomCalculatorTool
from .config import AgenticAssistantConfig
from .rag import get_rag_chain
from .sqlqa import get_sql_qa_tool, get_sql_chain

config = AgenticAssistantConfig()
bedrock_runtime = boto3.client("bedrock-runtime", region_name=config.bedrock_region)

claude_llm = ChatBedrock(
    # model_id=config.llm_model_id,
    model_id="anthropic.claude-3-haiku-20240307-v1:0",

    client=bedrock_runtime,
    model_kwargs={
        "max_tokens": 1000,
        "temperature": 0.0,
        "top_p": 0.99
    },
)

claude_chat_llm = ChatBedrock(
    model_id=config.llm_model_id,
    # transitianthropic.claude-3-haiku-20240307-v1:0",
    client=bedrock_runtime,
    model_kwargs={
        "max_tokens": 1000,
        "temperature": 0.0,
        "top_p": 0.99
    },
)

search = DuckDuckGoSearchRun()
# custom_calculator = CustomCalculatorTool()
rag_qa_chain = get_rag_chain(config, claude_llm, bedrock_runtime)
sql_chain = get_sql_chain(claude_chat_llm)
#    Tool(
#         name="Calculator",
#         func=custom_calculator,
#         description=(
#             "Use this tool when you need to perform mathematical calculations. "
#             "The input to this tool should be a valid mathematical expression, such as '55/3' or '(10 + 20) * 5'."
#         ),
#     ),
# For more :https://python.langchain.com/api_reference/core/tools/langchain_core.tools.simple.Tool.html#langchain_core.tools.simple.Tool
LLM_AGENT_TOOLS = [
    Tool(
        name="WebSearch",
        func=search.invoke,
        description=(
            "Use this tool to search for information on current events, news, or general knowledge topics. "
            "For example, you can use this tool to find information about recent news events, famous people, or common facts,  do not use it for current US president."
        ),
        handle_tool_error="Sorry, I couldn't find any relevant information on that topic. Please try asking a different question.",
    ),
     Tool(
        name="CVEntitySearch",
        # func=lambda query: rag_qa_chain.invoke({"input": query}),
        func= rag_qa_chain.invoke,
        description=(
            "Use this tool when you need infomation about CV in local CV vector database. "
            "For example, you can use this tool for Candiate projects mention in CV, University that candidate attend to, who have which project."
        ),
        handle_tool_error="RAG ErrorSorry, I couldn't find any relevant information on that RAG. Please try asking a different question.",
    ), 
    Tool(
        name="AnalyticsQA",
        func=lambda question: get_sql_qa_tool(question, sql_chain),
        description=(
            "Use this tool to perform analytical queries and calculations on CV data."
            " This tool is suitable for questions that require aggregating, filtering number of CV related source_doc,gpa,number of project, work exprience."
            "The input should be a natural language question related to analyzing like number of CV, list source doc."
        ),
    )
]
