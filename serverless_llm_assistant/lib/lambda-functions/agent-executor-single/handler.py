import logging
import traceback

import boto3
from langchain.chains import ConversationChain
# from langchain_aws import BedrockLLM
from langchain_aws import ChatBedrock
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
import json
from assistant.config import AgenticAssistantConfig
from assistant.prompts import CLAUDE_PROMPT
from assistant.prompts import CLAUDE_AGENT_PROMPT
from assistant.prompts import CV_PROMPT
from assistant.utils import parse_markdown_content
## placeholder for lab 3, step 4.2, replace this with imports as instructed
from langchain.agents import AgentExecutor, create_xml_agent
from assistant.tools import LLM_AGENT_TOOLS
from langchain_community.embeddings import BedrockEmbeddings
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from langchain_aws import ChatBedrockConverse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client("ssm")
config = AgenticAssistantConfig()

bedrock_runtime = boto3.client("bedrock-runtime", region_name=config.bedrock_region)

claude_llm = ChatBedrock(
    model_id=config.llm_model_id,
    client=bedrock_runtime,
    model_kwargs={
        "max_tokens": 1000,
        "temperature": 0.0,
        "top_p": 0.99
    },
)

# claude_chat_llm = ChatBedrock(
#     # model_id=config.llm_model_id,
#     # transitioning to claude 3 with messages API
#     model_id="anthropic.claude-3-haiku-20240307-v1:0",
#     client=bedrock_runtime,
#     model_kwargs={
#         "max_tokens": 1000,
#         "temperature": 0.0,
#         "top_p": 0.99
#     },
# )
claude_chat_llm = ChatBedrockConverse(
    model="amazon.nova-lite-v1:0",
    temperature=0.99,
    client=bedrock_runtime,
    max_tokens=None,
    # other params...
    )

def get_basic_chatbot_conversation_chain(
    user_input, session_id, clean_history, verbose=False
):
    message_history = DynamoDBChatMessageHistory(
        table_name=config.chat_message_history_table_name, session_id=session_id
    )

    if clean_history:
        message_history.clear()

    memory = ConversationBufferMemory(
        memory_key="history",
        chat_memory=message_history,
        # Change the human_prefix from Human to something else
        # to not conflict with Human keyword in Anthropic Claude model.
        human_prefix="Hu",
        return_messages=False
    )

    conversation_chain = ConversationChain(
        prompt=CLAUDE_PROMPT, llm=claude_chat_llm, verbose=verbose, memory=memory
    )

    return conversation_chain

def get_basic_cv_conversation_chain():
    cv_llm  = ChatBedrockConverse(
    model="amazon.nova-lite-v1:0",
    temperature=0.99,
    client=bedrock_runtime,
    max_tokens=None,
    # other params...
    )
    return CV_PROMPT | cv_llm    


## placeholder for lab 3, step 4.3, replace this with the get_agentic_chatbot_conversation_chain helper.
def get_agentic_chatbot_conversation_chain(
    user_input, session_id, clean_history, verbose=False
):
    message_history = DynamoDBChatMessageHistory(
        table_name=config.chat_message_history_table_name, session_id=session_id
    )
    if clean_history:
        message_history.clear()

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        # Change the human_prefix from Human to something else
        # to not conflict with Human keyword in Anthropic Claude model.
        human_prefix="Hu",
        chat_memory=message_history,
        return_messages=False,
    )

    agent = create_xml_agent(
        llm=claude_chat_llm,
        tools=LLM_AGENT_TOOLS,
        prompt=CLAUDE_AGENT_PROMPT,
        stop_sequence=["</tool_input>", "</final_answer>"]
    )

    agent_chain = AgentExecutor(
        agent=agent,
        tools=LLM_AGENT_TOOLS,
        return_intermediate_steps=False,
        verbose=verbose,
        memory=memory,
        max_iterations=6,
        handle_parsing_errors="Check your output and make sure it conforms!"
    )
    return agent_chain

def get_rag_chain(user_input,k=5, verbose=False):
    embedding_model = BedrockEmbeddings(
        model_id=config.embedding_model_id, client=bedrock_runtime
    )

    vector_store = PGVector.from_existing_index(
        embedding=embedding_model,
        collection_name=config.collection_name,
        connection=config.postgres_connection_string,
    )
    results= vector_store.similarity_search_with_score(user_input,k=k)
    current_data = []
    for doc, score in results:
        data = {}
        data["score"]= score
        data["page_content"]=doc.page_content
        data["metadata"]=doc.metadata
        current_data.append(data)
    return current_data
def lambda_handler(event, context):
    logger.info(event)
    user_input = event["user_input"]
    session_id = event["session_id"]
    chatbot_type = event.get("chatbot_type", "basic")
    chatbot_types = ["basic", "agentic"]
    clean_history = event.get("clean_history", False)

    # new
    querry_k = event.get("querry_k", 5)

    if chatbot_type == "basic":
        conversation_chain = get_basic_chatbot_conversation_chain(
            user_input, session_id, clean_history
        ).invoke
    elif chatbot_type == "agentic":
        conversation_chain = get_agentic_chatbot_conversation_chain(
            user_input, session_id, clean_history
        ).invoke
    elif chatbot_type=="rag":
        a = 1+1
        # conversation_chain = get_rag_chain(
        #     user_input, k=querry_k
        
    elif chatbot_type=="chatcv":
        conversation_chain = get_basic_cv_conversation_chain().invoke
    else:
        return {
            "statusCode": 200,
            "response": (
                f"The chatbot_type {chatbot_type} is not supported."
                f" Please use one of the following types: {chatbot_types}"
            ),
        }

    try:

        if chatbot_type == "basic":
            response = conversation_chain({"input": user_input})
            response = response["response"]
            response = parse_markdown_content(response)
        elif chatbot_type == "agentic":
            response = conversation_chain({"input": user_input})
            response = response["output"]
        elif chatbot_type == "rag":
            # response = conversation_chain(user_input)
            response = json.dumps(get_rag_chain(user_input,querry_k))
        elif chatbot_type == "chatcv":
            page_content = event.get("page_content", "")
            if not page_content:
                return {
                    "statusCode": 200,
                    "response": (
                        "Please provide the page content for the CV."
                    ),
                }
            response = conversation_chain({"input": user_input, "content": page_content})
            response = response.content

    except Exception:
        response = (
            "Unable to respond due to an internal issue."
            " Please try again later"
        )
        print(traceback.format_exc())

    return {"statusCode": 200, "response": response}