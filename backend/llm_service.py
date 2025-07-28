import google.generativeai as genai
import ollama
from openai import OpenAI
from http import HTTPStatus
from config import (GOOGLE_API_KEY, OPENROUTER_API_KEY, OLLAMA_API_BASE)
from database.models import QueryLanguage


def _generate_response(prompt: str, provider: str, model: str) -> str:
    """Internal function to call the selected LLM provider and model."""
    try:
        if provider == 'gemini':
            genai.configure(api_key=GOOGLE_API_KEY)
            gemini_model = genai.GenerativeModel(model)
            response = gemini_model.generate_content(prompt)
            return response.text
        elif provider == 'ollama':
            ollama_client = ollama.Client(host=OLLAMA_API_BASE)
            response = ollama_client.generate(model=model, prompt=prompt)
            return response['response']
        elif provider == 'openrouter':
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
            )
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        else:
            raise ValueError(f"Invalid LLM provider specified: {provider}")
    except Exception as e:
        print(f"An error occurred with the {provider} API: {e}")
        error_message = str(e).replace("'", "\\'")
        return f"print('Error generating code: {error_message}')"


def _clean_response(text: str) -> str:
    """Cleans markdown and other formatting from the LLM response."""
    return text.strip().replace("```python", "").replace("```sql", "").replace("```", "").strip()


# def get_user_intent(question: str, provider: str, model: str) -> str:
#     """Determines if the user wants a chart, table, or single fact."""
#     prompt = f"""
#     Analyze the user's question: "{question}"
#     Respond with ONLY one word: 'chart', 'table', or 'fact'.
#     - 'chart': for explicit requests for a 'chart', 'plot', 'graph', or 'visualization'.
#     - 'table': for questions needing a list or table (e.g., "who are the top 10...?").
#     - 'fact': for questions needing a single value (e.g., "how many...?").
#     """
#     response_text = _generate_response(prompt, provider, model)
#     return _clean_response(response_text).lower()

def generate_aggregation_code(question: str, tables_context: list, language: QueryLanguage, provider: str, model: str) -> str:
    """Generates the code to produce the final data table, named ans_df."""
    context_str = ""
    for table in tables_context:
        name_to_use = table['variable_name'] if language == QueryLanguage.python else table['table_name']
        columns_info = ", ".join([f"{name} ({dtype})" for name, dtype in table['columns_with_types'].items()])
        
        context_str += f"- Name: `{name_to_use}`\n"
        context_str += f"  Description: {table['description']}\n"
        context_str += f"  Columns (with data types): {columns_info}\n\n"
        
    prompt = f"""
    You are an expert {language.value} data analyst. A user wants to answer the question: "{question}".
    You have access to the following dataframes/tables which are ALREADY LOADED into memory:
    {context_str}
    Your task is to write a short, clean {language.value} script to produce the final data table that answers the question.

    --- VERY STRICT RESPONSE RULES ---
    1.  Pay close attention to the data types. If a column is a string (object), you may need to convert it to a number before performing calculations.
    2.  Provide ONLY the raw {language.value} code.
    3.  You are strictly forbidden from writing `pd.read_csv` or creating your own DataFrames (e.g., NO `pd.DataFrame({{...}})`). You MUST use the provided dataframes.
    4.  Structure your code in logical steps. For each step (e.g., filtering, merging, grouping), assign the result to a new DataFrame with a descriptive name (e.g., `filtered_races_df`, `merged_results_df`).
    5.  The final variable containing the answer MUST be named `ans_df`.
    6.  DO NOT include comments, explanations, or function definitions (no `def my_function():`).
    7.  DO NOT visualize the data. Just produce the final `ans_df`.
    """
    response_text = _generate_response(prompt, provider, model)
    return _clean_response(response_text)

def generate_visualization_code(request_data: dict, provider: str, model: str) -> str:
    """
    Generates Plotly code based on user selections and a data preview.
    """
    prompt = f"""
    You are a Python data visualization expert.
    A user has a data table and wants to create a '{request_data['chart_type']}' chart.
    Their original question was: "{request_data['original_question']}"
    
    Here is a sample of their data table (in JSON format):
    {request_data['datatable_json'][:10]} 

    Your task is to write Python code using `plotly.express` to create this chart.

    --- VERY STRICT RESPONSE RULES ---
    1.  The data is in a pandas DataFrame named `ans_df`.
    2.  The user has selected:
        - X-Axis: '{request_data['x_axis']}'
        - Y-Axis: '{request_data['y_axis']}'
        - Chart Type: '{request_data['chart_type']}'
        - Legend (Color): '{request_data.get('legend')}' (if provided)
    3.  Create a plotly figure object named `fig`. Use the user's selections for the axes and chart type.
    4.  The final line of your code MUST be `fig.to_json()`.
    5.  Provide ONLY the Python code. No other text or explanations.
    """
    response_text = _generate_response(prompt, provider, model)
    return _clean_response(response_text)