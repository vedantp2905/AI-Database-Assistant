from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
import pandas as pd
from sql_validator import SQLValidator
from llm_factory import LLMFactory

class DBChatbot:
    def __init__(self, schema_manager, llm_provider="gemini"):
        self.schema_manager = schema_manager
        self.llm = LLMFactory.create_llm(llm_provider)
        self.sql_validator = SQLValidator()
        self.context = []  # To store previous interactions
        
    def update_context(self, user_question, response):
        """Update the context with the latest question and response."""
        self.context.append({"question": user_question, "response": response})
        if len(self.context) > 10:  # Limit context size
            self.context.pop(0)
        
    def get_relevant_schema(self, query):
        """Get relevant schema information based on the query"""
        # Get both similar tables and direct matches
        table_matches = self.schema_manager.semantic_table_search(query, min_score=0.6)
        direct_matches = self.schema_manager.similarity_search(query, k=3, threshold=0.5)
        
        # Combine and deduplicate results
        schema_info = []
        seen_tables = set()
        
        # Add table matches first
        for match in table_matches:
            if match['table'] not in seen_tables:
                schema_info.append(match['description'])
                seen_tables.add(match['table'])
        
        # Add direct matches if they bring new information
        for match in direct_matches:
            table = match['metadata']['table']
            if table not in seen_tables:
                schema_info.append(match['content'])
                seen_tables.add(table)
        
        schema_text = "\n".join(schema_info)
        
        return f"""IMPORTANT: Below is the exact database schema with correct table and column names.
Use ONLY these exact names in your query:

{schema_text}

IMPORTANT RULES:
1. Use ONLY the exact table and column names shown above
2. Do not use aliases like 'e' or 'd' unless you define them in proper table aliases
3. Every column reference must exactly match a column from the schema
4. Do not guess or assume column names - use only what is explicitly shown"""
    
    def generate_sql(self, user_query):
        """Generate SQL query from natural language"""
        relevant_schema = self.get_relevant_schema(user_query)
        
        # If no relevant schema found, return error
        if not relevant_schema:
            raise ValueError("No relevant tables found in the database schema for this query.")
        
        # Include context in the prompt
        context_str = "\n".join([f"Q: {item['question']}\nA: {item['response']}" for item in self.context])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a SQL query generator. Your ONLY job is to convert natural language questions into SQL queries. 
            
Schema information:
{relevant_schema}

CRITICAL RULES:
1. ONLY output the exact SQL query - no explanations, no markdown, no additional text
2. ALWAYS use fully qualified column names (table_name.column_name)
3. ONLY use the exact join conditions shown in the schema examples
4. NEVER create column aliases that don't exist in the schema
5. For joins, copy the exact join syntax from the schema examples
6. If you can't find an exact column or join path in the schema, respond with 'INVALID_QUERY'
"""),
            ("human", "{question}")
        ])
        
        chain = (
            {"schema": lambda x: relevant_schema, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | (lambda x: x.content)
        )
        
        sql_query = chain.invoke(user_query).strip()
        
        if not sql_query.upper().startswith('SELECT'):
            raise ValueError("No valid SQL query found in the response")
        
        if sql_query == 'INVALID_QUERY':
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
            
            # Update context with the latest question and response
            self.update_context(user_question, response)
            
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