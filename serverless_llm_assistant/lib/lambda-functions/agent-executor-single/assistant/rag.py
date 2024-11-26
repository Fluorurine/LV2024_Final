# from langchain.chains import RetrievalQA
# from langchain_community.chains import RetrievalQA
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_core.prompts import ChatPromptTemplate

def get_rag_chain(config, llm, bedrock_runtime):
    """Prepare a RAG question answering chain.

      Note: Must use the same embedding model used for creating the semantic search index
      to be used for real-time semantic search.
    """
    embedding_model = BedrockEmbeddings(
        model_id=config.embedding_model_id, client=bedrock_runtime
    )

    vector_store = PGVector.from_existing_index(
        embedding=embedding_model,
        collection_name=config.collection_name,
        connection_string=config.postgres_connection_string,
    )
    # system_prompt = (
    #     "Use the given context to answer the question. "
    #     "If you don't know the answer, say you don't know. "
    #     "Context: {context}"
    # )
    # prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", system_prompt),
    #         ("human", "{input}"),
    #     ]
    # )
    # # question_answer_chain = create_stuff_documents_chain(llm, prompt)
    

    # return RetrievalQA.from_chain_type(
    #     llm=llm,
    #     chain_type="stuff",
    #     retriever=vector_store.as_retriever(k=5, fetch_k=50),
    #     return_source_documents=False,
    #     input_key="question",
    # )
    return vector_store.as_retriever(search_kwargs={"k": 1})