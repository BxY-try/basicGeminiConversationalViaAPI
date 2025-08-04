import os
import json
from google import genai
from google.genai import types
from tools.available_tools import available_tools, get_weather, get_news, get_current_date_and_time
from typing import Tuple

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
        mode="AUTO"  # Use uppercase string literal for the mode
    )
)

def process_content_with_tools(contents: list) -> Tuple[str, list]:
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

    # The loop can handle multiple tool calls in a sequence
    while True:
        # Send the prompt and tools to the model
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=genai.types.GenerateContentConfig(
                tools=[gemini_tools],
                tool_config=tool_config,
            ),
        )

        # The model's response is always appended to the history
        model_response_content = response.candidates[0].content
        history.append(model_response_content)

        # Check for a function call in the response
        part = model_response_content.parts[0]
        
        if part.function_call:
            function_call = part.function_call
            tool_name = function_call.name
            tool_args = function_call.args

            if tool_name not in available_tools:
                raise ValueError(f"Tool '{tool_name}' not found.")

            print(f"Executing tool: {tool_name} with args: {tool_args}")
            function_to_call = available_tools[tool_name]
            
            # The actual execution of the tool function
            tool_response_data = function_to_call(**tool_args)
            
            # Append the tool's result to the conversation history
            history.append(
                types.Content(
                    role="tool",
                    parts=[
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": tool_response_data},
                        )
                    ],
                )
            )
            # Continue the loop to get the final text response from the model
        elif part.text:
            # If there is no function call, we have our final answer.
            return part.text, history
        else:
            # Handle cases where the response is neither text nor a function call
            return "I'm sorry, I couldn't process that request.", history