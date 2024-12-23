from langchain.prompts.prompt import PromptTemplate
from langchain.chains import create_sql_query_chain
from .config import AgenticAssistantConfig
# from .sql_chain import create_sql_query_generation_chain

config = AgenticAssistantConfig()
def get_sql_chain(llm):
    """Prepare a RAG question answering chain.

      Note: Must use the same embedding model used for creating the semantic search index
      to be used for real-time semantic search.
    """
    # sqlalchemy_connection_url: str = sqlalchemy.URL.create(
    #         "postgresql+psycopg",
    #         username="AgentDBAdmin",
    #         password="fU8n-2II^b,3FF^7WO1r_tcbNl-^BE",
    #         host="serverlessllmassistantstack-agentdbd4c116e7-xubdinqf6rxf.cxgcu4uco018.us-east-1.rds.amazonaws.com",
    #         database="AgentSQLDBandVectorStore",
    #     )

    # sql_engine= sqlalchemy.create_engine(sqlalchemy_connection_url)
    # SQL_TABLE_NAMES="extracted_entities"
    # entities_db = SQLDatabase(
    #                 engine=sql_engine,
    #                 include_tables=["extracted_entities"],
    #                 sample_rows_in_table_info=2,
    #             )
    template = '''Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and only return the SQL querry statement without explaination.
    Always have LIMIT at the end of SQL querry and value of it take from <limit> XML tag below.
    Only use the following tables:
    limit:
    <limit>{top_k}</limit>
    {table_info}.
    
    Question: {input}'''
    prompt = PromptTemplate.from_template(template)
    chain = create_sql_query_chain(llm, config.entities_db, prompt)
    # response = chain.invoke({"question": "How many employees are there"})
    return chain

def get_sql_qa_tool(user_question, text_to_sql_chain,initial_context=""):
    sql_query = text_to_sql_chain.invoke(
        {
            "question": user_question,
            # "initial_context": initial_context,
            # "tables_content_description": prepare_tables_description(
            #     sql_tables_content_description
            # ),
        }
    )
    sql_query = sql_query.strip()

    # Typically sql queries end with a semicolon ";", some DBs such as SQLite
    # fail without it, therefore, we ensure it is there.
    if not sql_query.endswith(";"):
        sql_query += ";"

    print(sql_query)

    # fixed_query = sqlfluff.fix(sql=sql_query, dialect="postgres")
    try:
        result = config.entities_db.run(sql_query)
    except Exception as e:
        result = (
            f"Failed to run the SQL query {sql_query} with error {e}"
            " Appologize, ask the user for further specifications,"
            " or to try again later."
        )

    return result

# sql_tables_content_description = {
#     "extracted_entities": (
#         "Contains extracted information from multiple financial reports of companies."
#         " The information includes revenue, number of employees and risks per company per year."
#     )
# }

# ============================================================================
# Prompt construction for SQL QA.
# ============================================================================
# _SQL_TEMPLATE = """
# \nHuman: Given the input question inside the <input></input> XML tags, write a syntactically correct {dialect} query that will be executed against a SQL database.
# You must follow the rules within the <rules></rules> XML tags below:

# <rules>
# 1. Only generate the SQL query without explanation.
# 2. You must only use column names that exist in the table schema below.
# 3. Only use relevant columns to the input question and pay attention to use the correct data types when filtering with WHERE.
# 4. Consider the information inside the <metadata></metadata> XML tags as intitial context when writing the SQL query.
# 7. End the SQL with a LIMIT clause. The limit value is inside the <limit></limit> XML tags below.
# 8. When using GROUP BY, ensure that every column in the SELECT clause appears in the GROUP BY clause or that it is aggregated with an aggregation function such as AVG or SUM.
# 9. Write the least complex SQL query that answers the questions and abides by the rules.
# </rules>

# Use the following format:

# Question: "Question here"
# Initial context: "Initial context here"
# SQLQuery: "SQL Query to run"

# Consider the table descriptions inside the <description></description> XML tags to choose which table(s) to use:
# <description>
# {tables_content_description}
# </description>

# Only use the following table schema between the XML tags <table></table>:
# <table>
# {table_info}
# </table>

# limit:
# <limit>{top_k}</limit>

# Assistant:
# Question: {input}
# Initial Context:
# <metadata>
# {initial_context}
# </metadata>
# SQLQuery: """

# LLM_SQL_PROMPT = PromptTemplate(
#     input_variables=[
#         "input",
#         "table_info",
#         "top_k",
#         "dialect",
#         "initial_context",
#         "tables_content_description",
#     ],
#     template=_SQL_TEMPLATE,
# )


# def prepare_tables_description(table_descriptions):
#     table_description = ""
#     for table, description in table_descriptions.items():
#         table_description += "\n" + table + ": " + description
#     table_description += "\n"
#     return table_description


# def get_text_to_sql_chain(config, llm):
#     """Create an LLM chain to convert text input to SQL queries."""
#     return create_sql_query_generation_chain(
#         llm=llm,
#         db=config.entities_db,
#         prompt=LLM_SQL_PROMPT,
#         # Value to use with LIMIT clause
#         k=5,
#     )


# def get_sql_qa_tool(user_question, text_to_sql_chain, initial_context=""):
#     sql_query = text_to_sql_chain.invoke(
#         {
#             "question": user_question,
#             "initial_context": initial_context,
#             "tables_content_description": prepare_tables_description(
#                 sql_tables_content_description
#             ),
#         }
#     )
    sql_query = sql_query.strip()

    # Typically sql queries end with a semicolon ";", some DBs such as SQLite
    # fail without it, therefore, we ensure it is there.
    if not sql_query.endswith(";"):
        sql_query += ";"

    print(sql_query)

    # fixed_query = sqlfluff.fix(sql=sql_query, dialect="postgres")
    try:
        result = config.entities_db.run(sql_query)
    except Exception as e:
        result = (
            f"Failed to run the SQL query {sql_query} with error {e}"
            " Appologize, ask the user for further specifications,"
            " or to try again later."
        )

    return result