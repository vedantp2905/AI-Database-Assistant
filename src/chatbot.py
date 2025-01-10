from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
import pandas as pd
from sql_validator import SQLValidator

class DBChatbot:
    def __init__(self, schema_manager):
        self.schema_manager = schema_manager
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0.1
        )
        self.sql_validator = SQLValidator()
        
    def get_relevant_schema(self, query):
        """Get relevant schema information based on the query"""
        results = self.schema_manager.vector_store.similarity_search(query, k=3)
        return "\n".join([doc.page_content for doc in results])
    
    def generate_sql(self, user_query):
        """Generate SQL query from natural language"""
        relevant_schema = self.get_relevant_schema(user_query)
        
        # If no relevant schema found, return error
        if not relevant_schema:
            raise ValueError("No relevant tables found in the database schema for this query.")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL expert. Given the following database schema and user question, 
             first verify if the question can be answered using ONLY the provided schema tables.
             If not, respond with exactly 'INVALID_QUERY'.
             
             Schema information:
             {schema}
             
             Rules:
             1. Only use tables mentioned in the schema above
             2. Generate raw SQL without any formatting or code blocks
             3. If tables needed are not in schema, return 'INVALID_QUERY'"""),
            ("human", "{question}")
        ])
        
        chain = (
            {"schema": lambda x: relevant_schema, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | (lambda x: x.content)
        )
        
        sql_query = chain.invoke(user_query)
        
        # Clean any remaining markdown or whitespace
        sql_query = (sql_query.replace('```sql', '')
                         .replace('```', '')
                         .replace('`', '')
                         .strip())
        
        if sql_query == 'INVALID_QUERY' or 'student' in sql_query.lower():  # Example of checking for non-existent tables
            raise ValueError("This question cannot be answered using the available database schema.")
        
        return sql_query
    
    def generate_response(self, sql_result, user_question):
        """Generate natural language response from SQL results"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Given the following SQL query results and the original question, 
             generate a natural language response that answers the user's question in a clear 
             and concise way.
             
             Original question: {question}
             Results: {results}"""),
            ("human", "Please provide a natural language summary of these results.")
        ])
        
        chain = prompt | self.llm | (lambda x: x.content)
        return chain.invoke({"results": str(sql_result), "question": user_question})
    
    def query(self, user_question):
        """Main method to handle user queries"""
        try:
            # Generate SQL query
            sql_query = self.generate_sql(user_question)
            
            # Validate SQL query
            is_valid, validation_message = self.sql_validator.validate(sql_query)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"SQL validation failed: {validation_message}",
                    "sql_query": sql_query
                }
            
            # Execute query
            result = pd.read_sql(sql_query, self.schema_manager.engine)
            
            # Generate response with original question
            response = self.generate_response(result, user_question)
            
            return {
                "success": True,
                "response": response,
                "sql_query": sql_query,
                "raw_result": result.to_dict('records')
            }
        except ValueError as ve:
            return {
                "success": False,
                "error": str(ve),
                "sql_query": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql_query": sql_query if 'sql_query' in locals() else None
            } 