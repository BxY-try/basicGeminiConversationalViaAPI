import os
import json
from google import genai
from google.genai import types
from tools.available_tools import available_tools, get_weather, get_news, get_current_date_and_time
from typing import Tuple, Optional

# --- Persona Loading ---
def load_system_prompt(persona_name: str = "aria") -> Optional[str]:
    """Loads the system prompt from a text file."""
    persona_path = os.path.join(os.path.dirname(__file__), '..', 'personas', f'{persona_name}.txt')
    if os.path.exists(persona_path):
        with open(persona_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

# Initialize the Generative AI client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Manually define the tool declarations using uppercase string literals as required by the validator.
tool_declarations = [
    {
        "name": "get_weather",
        "description": "Gets the current weather for a given location using the OpenWeatherMap API.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "The city name, e.g., 'San Francisco', 'Tokyo'."
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_news",
        "description": "Gets the top 5 recent news headlines for a given topic from the NewsAPI.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {
                    "type": "STRING",
                    "description": "The keyword or topic to search for in the news, e.g., 'Tesla', 'AI development', 'latest on Mars rovers'."
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_current_date_and_time",
        "description": "Returns the current date and time in a human-readable format.",
        "parameters": {"type": "OBJECT", "properties": {}}
    }
]

# Configure the tools for the model
gemini_tools = types.Tool(function_declarations=tool_declarations)
tool_config = types.ToolConfig(
    function_calling_config=types.FunctionCallingConfig(
        mode="AUTO"  # Default mode: let the model decide between chatting and tool use.
    )
)

def process_content_with_tools(contents: list, system_prompt: Optional[str] = None) -> Tuple[str, list]:
    """
    Processes a list of content parts using the Gemini model, with a tool-calling loop.

    This function handles the interaction with the model, including:
    1. Sending the complete conversation history and prompt with available tools.
    2. Checking if the model wants to call a function.
    3. Executing the function if requested.
    4. Sending the function's result back to the model.
    5. Returning the final, user-facing text response and the updated history.

    Args:
        contents (list): The complete list of conversation history and the current prompt.

    Returns:
        tuple[str, list]: A tuple containing the final text response and the updated
                          conversation history.
    """
    # Create a mutable copy of the history to avoid modifying the original list
    history = list(contents)

    # Define the generation config, including the system prompt
    generation_config = genai.types.GenerateContentConfig(
        tools=[gemini_tools],
        tool_config=tool_config,
        system_instruction=system_prompt
    )

    # First call to the model
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=history,
        config=generation_config,
    )

    model_response_content = response.candidates[0].content
    history.append(model_response_content)

    # Check if there are any function calls to execute
    if not any(part.function_call for part in model_response_content.parts):
        # No function calls, return the text response
        final_text = "".join(part.text for part in model_response_content.parts if part.text)
        return final_text, history

    # Process all function calls found in the first response
    tool_results = []
    for part in model_response_content.parts:
        if part.function_call:
            function_call = part.function_call
            tool_name = function_call.name
            tool_args = dict(function_call.args)

            if tool_name not in available_tools:
                raise ValueError(f"Tool '{tool_name}' not found.")

            print(f"Executing tool: {tool_name} with args: {tool_args}")
            function_to_call = available_tools[tool_name]
            tool_response_data = function_to_call(**tool_args)
            
            tool_results.append(types.Part.from_function_response(
                name=tool_name,
                response={"result": tool_response_data},
            ))

    # If tools were called, send their results back to the model for a final answer
    if tool_results:
        # Add the tool results to the history
        history.append(types.Content(role="tool", parts=tool_results))
        
        # Add an explicit instructional prompt to guide the model's final response
        instructional_prompt = types.Content(
            role="user",
            parts=[types.Part.from_text(
                "You have been provided with a series of tool outputs. "
                "Synthesize these results into a single, coherent, and user-friendly text response. "
                "Directly answer the user's original query based on the information gathered. Do not ask for the same tools again."
            )]
        )
        history.append(instructional_prompt)
        
        # Second and final call to the model
        final_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=generation_config,
        )
        history.append(final_response.candidates[0].content)
        final_text = "".join(part.text for part in final_response.candidates[0].content.parts if part.text)
        return final_text, history

    # Fallback in case something unexpected happens
    return "I'm sorry, I couldn't process that request after attempting to use tools.", history