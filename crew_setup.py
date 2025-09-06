from crewai import Agent, Task, Crew, LLM
import base64
# --- LLM Setup ---
# You can swap model string for "gpt-4o-mini", "gpt-4.1", or "gemini/gemini-2.0-flash"
llm = LLM(
    model="gemini/gemini-2.0-flash",
    temperature=0.0001,
)

# --- Agents ---
# Handles parsing both text and image inputs into structured JSON
parser_agent = Agent(
    role="Food Label Parser",
    goal="Extract clean structured text from food labels (ingredients + nutrients).",
    backstory="Specialist in reading food labels and producing normalized data for scoring.",
    llm=llm
)

# --- Functions ---
def analyze_input_with_image(image_file):
    """
    Takes an uploaded image (food label), extracts ingredients + nutrients,
    and returns structured JSON.
    """
    image_bytes = image_file.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    task = Task(
        description="Extract and parse ingredients and nutrients from the given food label image.",
        agent=parser_agent,
        expected_output="JSON {ingredients:[], nutrients:{}}",
        # CrewAI only supports primitive inputs
        inputs={"image_base64": image_b64}
    )
    crew = Crew(agents=[parser_agent], tasks=[task])
    return crew.kickoff()


def analyze_input(text: str):
    """
    Takes pasted raw text (ingredients/nutrition info),
    parses it, and returns structured JSON.
    """
    task = Task(
        description=(
            "You are given raw text from a food label. "
            "Extract ingredients and nutrition values. "
            "Output strictly in JSON with fields: "
            "{ingredients: [list of strings], nutrients: {nutrient_name: amount + unit}}."
        ),
        agent=parser_agent,
        expected_output="JSON {ingredients:[], nutrients:{}}",
    )

    crew = Crew(agents=[parser_agent], tasks=[task])
    result = crew.kickoff(inputs={"raw_text": text})
    return result
