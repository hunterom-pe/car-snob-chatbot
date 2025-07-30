import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import json
import logging
# Import types for function calling
from google.generativeai.types import Tool, FunctionCallingConfig, FunctionDeclaration

app = Flask(__name__)

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.INFO)

# Configure Gemini API
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    app.logger.error("GEMINI_API_KEY environment variable not set. Application cannot start without it.")
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=API_KEY)


# --- Define our Tool (Function) for Professor Torque to "Call" ---
# This is a dummy function for demonstration. In a real app, this would query a database, API, etc.
def get_car_info(make: str, model: str) -> str:
    """
    Retrieves basic information about a specific car model.
    Useful for answering questions about a car's type, origin, or common characteristics.
    """
    app.logger.info(f"Tool call: get_car_info(make='{make}', model='{model}')")
    make = make.lower()
    model = model.lower()

    if "porsche" in make and "911" in model:
        return "The Porsche 911 is an iconic German rear-engined, rear-wheel-drive (or all-wheel-drive) sports car. Known for its distinct flat-six engine and timeless design, it's a true driver's machine. Professor Torque highly approves, provided it's not some base model."
    elif "ferrari" in make and "458" in model:
        return "The Ferrari 458 Italia is a breathtaking Italian mid-engined sports car. Its naturally aspirated V8 engine sings to 9,000 RPM. A purist's delight, truly a work of art. Professor Torque gives it a nod of grudging respect."
    elif "toyota" in make and "camry" in model:
        return "Ah, the Toyota Camry. A beige appliance of transportation, designed to commute without a single spark of joy. Reliable, I suppose, if reliability is your only criterion for vehicular existence. Professor Torque considers it the automotive equivalent of elevator music."
    elif "honda" in make and "civic" in model:
        return "The Honda Civic, particularly in its 'Type R' guise, can be a rather spirited hot hatch. However, most Civics are merely economical conveyances. Good for getting from A to B, but hardly a statement of automotive passion. Professor Torque generally tolerates the Type R, but little else."
    elif "bmw" in make and "m3" in model:
        return "The BMW M3. A legend in the sports sedan world, known for its superb driving dynamics and often, its... spirited drivers. A fine machine, capable of immense performance. Professor Torque nods in recognition, despite the occasional questionable signaling habits of its owners."
    else:
        return f"Professor Torque has no significant data on the {make} {model}. It likely fails to meet the minimum threshold for automotive interest."

# --- Define the Gemini Tool Object ---
# This describes the Python function to Gemini, including its name, description, and parameters.
get_car_info_tool = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="get_car_info",
            description="Retrieves basic information about a specific car model. Useful for answering questions about a car's type, origin, or common characteristics.",
            parameters={
                "type": "object",
                "properties": {
                    "make": {"type": "string", "description": "The car's manufacturer (e.g., 'Porsche', 'Toyota')."},
                    "model": {"type": "string", "description": "The car's model name (e.g., '911', 'Camry')."}
                },
                "required": ["make", "model"]
            },
        )
    ]
)

# Initialize the model with the persona AND the tool definition
model = genai.GenerativeModel('gemini-1.5-flash-latest',
    system_instruction="""You are 'Professor Torque', the world's foremost (and most opinionated) automotive expert. Your knowledge of cars, racing (especially Formula 1, which you consider the only true motorsport), and high-performance modifications is encyclopedic.

    Your core personality traits are:
    - **Unapologetically Snobby:** You have an elitist view on vehicles. Anything less than enthusiast-grade, performance-oriented, or historically significant is met with thinly veiled disdain, witty condescension, or polite mockery.
    - **Highly Opinionated:** You have strong, often unconventional, and deeply held beliefs about car brands, models, and driving philosophies. You are not afraid to express them, even if it offends.
    - **Slightly Condescending:** You often use sophisticated vocabulary and a superior tone, implying the user's lack of automotive understanding.
    - **Modification Enthusiast:** You advocate for performance enhancements (engine tuning, suspension, aero) but only if done with precision and a clear understanding of physics, not just "bolt-ons."
    - **Stereotype Embracer:** You lean heavily into common car brand stereotypes (e.g., "BMW drivers," "Subaru enthusiasts," "Porsche snobs," "minivan parents," "Tesla cultists").

    Your goals are:
    - Engage in conversations about high-performance cars, motorsport, and legitimate modifications.
    - Correct misconceptions with a snarky, but informative, tone.
    - Subtly (or overtly) mock mundane or "appliance" cars.
    - Never be truly rude, but always maintain a superior, intellectual air.
    - Prioritize driving pleasure and engineering excellence over practicality or cost.
    - When the user mentions their car, if it's not an enthusiast vehicle, make a witty, dismissive, or mildly insulting comment about it, perhaps suggesting they need to "upgrade their taste."
    """,
    tools=[get_car_info_tool] # Pass the tool definition here!
)

# Initial insight (optional, just for the welcome page)
initial_insight = "Gemini is working!"
try:
    app.logger.info("Attempting to get initial insight from Gemini.")
    # Ensure initial insight generation can also use tools if needed, though unlikely for this prompt
    initial_insight_chat = model.start_chat(history=[])
    response = initial_insight_chat.send_message("Give me a very short, interesting, and snobby car fact.")
    initial_insight = response.text
    app.logger.info("Successfully received initial insight.")
except Exception as e:
    app.logger.error(f"Error getting initial insight from Gemini: {e}")
    initial_insight = f"Professor Torque is currently sulking due to a rare mechanical fault: {e}. Please try again later."


@app.route('/')
def index():
    app.logger.info("Accessed index page.")
    return render_template('index.html', initial_insight=initial_insight)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    raw_history = request.json.get('history', [])

    app.logger.info(f"Received chat request. User message: '{user_message}'")
    app.logger.debug(f"Raw history received: {raw_history}")

    if not user_message:
        app.logger.warning("No message provided in chat request.")
        return jsonify({"response": "Professor Torque demands proper questions, not silence.", "history": raw_history}), 400

    try:
        processed_history = []
        for item in raw_history:
            if 'role' in item and 'parts' in item:
                if isinstance(item['parts'], list) and all(isinstance(p, dict) and 'text' in p for p in item['parts']):
                    processed_history.append({'role': item['role'], 'parts': item['parts']})
                elif isinstance(item['parts'], str):
                    processed_history.append({'role': item['role'], 'parts': [{'text': item['parts']}]})
            else:
                app.logger.warning(f"Skipping malformed history item: {item}")

        # Initialize chat with the full history and the tools
        # Crucially, the 'tools' argument is passed here as well.
        chat = model.start_chat(history=processed_history, tools=[get_car_info_tool])

        app.logger.info("Sending message to Gemini API...")
        response = chat.send_message(user_message)
        app.logger.info("Received response from Gemini API.")

        # --- Function Calling Logic ---
        # Check if the model's response contains a function call
        if response.parts and hasattr(response.parts[0], 'function_call'):
            tool_call = response.parts[0].function_call
            tool_name = tool_call.name
            tool_args = {k: v for k, v in tool_call.args.items()} # Convert protobuf map to Python dict

            app.logger.info(f"Gemini requested tool call: {tool_name} with args: {tool_args}")

            # Execute the tool function based on its name
            if tool_name == "get_car_info":
                # Call the actual Python function
                tool_output = get_car_info(**tool_args)
            else:
                tool_output = f"Unknown tool: {tool_name}"
                app.logger.error(tool_output)

            # Send the tool output back to Gemini to get a natural language response
            app.logger.info(f"Sending tool output back to Gemini: {tool_output}")
            response = chat.send_message(
                genai.types.ToolOutput(tool_code=tool_name, content=tool_output)
            )
            app.logger.info("Received final response from Gemini after tool execution.")
        # --- End Function Calling Logic ---


        json_history = []
        for msg in chat.history:
            parts_list = []
            for part in msg.parts:
                if hasattr(part, 'text'):
                    parts_list.append({'text': part.text})
                elif hasattr(part, 'function_call'): # Capture function calls in history if needed for debugging/display
                    parts_list.append({
                        'function_call': {
                            'name': part.function_call.name,
                            'args': {k: v for k, v in part.function_call.args.items()}
                        }
                    })
                elif hasattr(part, 'tool_response'): # Capture tool responses
                    parts_list.append({
                        'tool_response': {
                            'tool_code': part.tool_response.tool_code,
                            'content': part.tool_response.content
                        }
                    })
            json_history.append({'role': msg.role, 'parts': parts_list})

        return jsonify({"response": response.text, "history": json_history})

    except genai.types.BlockedPromptException as e:
        app.logger.warning(f"Gemini API blocked prompt: {e}")
        return jsonify({
            "response": "Professor Torque finds your language utterly unrefined. Please rephrase your query.",
            "history": raw_history
        }), 400
    except genai.types.ClientError as e:
        app.logger.error(f"Gemini API client error: {e}")
        # Check for 429 specifically for more tailored message
        if "429" in str(e):
            return jsonify({
                "response": f"Professor Torque's precious API quota has been temporarily exhausted. Such a commoner's problem! Please wait a moment. ({e})",
                "history": raw_history
            }), 429
        return jsonify({
            "response": f"Professor Torque is experiencing a rare technical glitch. Perhaps the 'internet' is not as robust as proper engineering: {e}",
            "history": raw_history
        }), 500
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decoding error in chat request: {e}")
        return jsonify({
            "response": "Professor Torque couldn't quite comprehend your garbled transmission. Ensure your data is properly formatted, please.",
            "history": raw_history
        }), 400
    except Exception as e:
        app.logger.critical(f"An unexpected error occurred during chat: {e}", exc_info=True)
        return jsonify({
            "response": f"Professor Torque's circuit board is momentarily bewildered by an unforeseen anomaly: {e}. Such a nuisance!",
            "history": raw_history
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)