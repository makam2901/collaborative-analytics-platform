import google.generativeai as genai
from config import GOOGLE_API_KEY
from database.models import QueryLanguage

# Configure the generative AI client
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_user_intent(question: str) -> str:
    """
    Uses the LLM to determine if the user wants a chart, a table, or a single fact.
    """
    prompt = f"""
    Analyze the user's question and determine the primary intent.
    The question is: "{question}"
    
    Possible intents are:
    - "chart": If the user explicitly asks for a 'chart', 'plot', 'graph', or 'visualization'.
    - "table": If the user asks a general question that would best be answered with a table of data (e.g., "who were the top 10 finishers?", "list all races in 2023").
    - "fact": If the user asks a question that can be answered with a single value (e.g., "how many races were there?", "who won the championship?").
    
    Respond with ONLY one word: 'chart', 'table', or 'fact'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().lower()
    except Exception:
        return "table" # Default to table on error

def generate_aggregation_code(question: str, tables_context: list, language: QueryLanguage) -> str:
    """
    Generates the Python or SQL code to get the raw data needed to answer a question.
    This is based on the high-quality prompt you provided.
    """
    context_str = ""
    for table in tables_context:
        name_to_use = table['variable_name'] if language == QueryLanguage.python else table['table_name']
        context_str += f"- Name: `{name_to_use}`\n"
        context_str += f"  Description: {table['description']}\n"
        context_str += f"  Columns: {', '.join(table['columns'])}\n\n"
        
    prompt = f"""
    You are an expert {language.value} data analyst. A user wants to answer the question: "{question}".
    You have access to the following data:
    {context_str}
    
    Your task is to write the {language.value} code to produce the data table required to answer the question.

    --- RESPONSE RULES ---
    1.  Provide ONLY the raw {language.value} code.
    2.  Do not include comments or explanations.
    3.  Do not define functions (e.g., no `def my_function():`).
    4.  Do not visualize the data.
    5.  The final line of your code must be the resulting DataFrame or data expression itself.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().replace("```python", "").replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        return f"print('Error: {e}')"

def generate_visualization_code(question: str, df_head_str: str) -> str:
    """
    Takes a data sample and generates Plotly code to visualize it based on the original question.
    """
    prompt = f"""
    You are a Python data visualization expert.
    A user has already aggregated a table of data. Here are the first 5 rows:
    {df_head_str}

    The user's original question was: "{question}"
    
    Your task is to write Python code using `plotly.express` to create a chart that answers the user's question.

    --- RESPONSE RULES ---
    1.  The aggregated data is in a pandas DataFrame named `agg_df`.
    2.  Your code should create a plotly figure object named `fig`.
    3.  The final line of your code MUST be `fig.to_json()`.
    4.  Do not include any other code, explanations, comments, or markdown formatting.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().replace("```python", "").replace("```", "").strip()
    except Exception as e:
        return f"print('Error: {e}')"