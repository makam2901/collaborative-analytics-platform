import google.generativeai as genai
from config import GOOGLE_API_KEY
from database.models import QueryLanguage

# Configure the generative AI client
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_code(question: str, tables_context: list, language: QueryLanguage) -> str:
    """
    Generates code from a natural language question using the context of multiple tables.
    """
    
    context_str = ""
    for table in tables_context:
        context_str += f"- DataFrame variable name: `{table['variable_name']}` (represents the table `{table['table_name']}`)\n"
        context_str += f"  Description: {table['description']}\n"
        context_str += f"  Columns: {', '.join(table['columns'])}\n\n"

    # Select the prompt based on the chosen language
    if language == QueryLanguage.python:
        prompt = f"""
        You are an expert Python data analyst. Your task is to write Python code to answer a question by analyzing one or more pandas DataFrames.
        
        You have access to the following DataFrames:
        {context_str}

        The user's question is: "{question}"

        Your response MUST follow these rules:
        1. You MUST write code that operates on the existing DataFrames listed above.
        2. You MUST NOT include any code to read data (e.g., NO `pd.read_csv`).
        3. You MUST provide ONLY the raw Python code. No comments, no explanations, no markdown formatting.
        4. The code should be a single expression or a short script that produces the answer. The final line must be the result.

        Example Question: "Show me the names of all the races"
        Example Output:
        races_df['name']
        """
    elif language == QueryLanguage.sql:
        # For SQL, we use the clean table name, not the variable name
        sql_context_str = ""
        for table in tables_context:
            sql_context_str += f"- Table name: `{table['table_name']}`\n"
            sql_context_str += f"  Description: {table['description']}\n"
            sql_context_str += f"  Columns: {', '.join(table['columns'])}\n\n"
            
        prompt = f"""
        You are an expert SQL data analyst. Your task is to write a single SQL query to answer a question by analyzing one or more tables.
        
        You have access to the following tables:
        {sql_context_str}

        The user's question is: "{question}"
        
        Your response MUST follow these rules:
        1. Your query MUST operate on the tables listed above.
        2. Provide ONLY the raw SQL query, with no explanation or markdown.
        """
    else:
        return "print('Invalid language specified.')"

    try:
        response = model.generate_content(prompt)
        # Clean up the response to remove markdown backticks
        generated_code = response.text.strip().replace("```python", "").replace("```sql", "").replace("```", "").strip()
        return generated_code
    except Exception as e:
        print(f"An error occurred with the LLM API: {e}")
        return f"print('Error generating code: {e}')"