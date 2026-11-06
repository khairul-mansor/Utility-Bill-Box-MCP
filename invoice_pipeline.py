
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

MODEL_NAME = "gemini-3.5-flash-lite"
BOX_MCP_SERVER_PATH = os.path.join(BASE_DIR, "mcp-server-box-main")
BOX_MCP_TOOLS = [
    "box_folder_items_list_tool",
    "box_file_text_extract_tool",
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="uv",
        args=[
            "--directory",
            BOX_MCP_SERVER_PATH,
            "run",
            "src/mcp_server_box.py",
            "--mcp-auth-type",
            "none",
            "--box-auth-type",
            "ccg",
        ],
    )


def parse_json(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return content


async def get_mcp_tools(session: ClientSession):
    mcp_tools = await session.list_tools()
    return [
        types.Tool(
            function_declarations=[
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {p: v for p, v in tool.inputSchema.items()},
                }
            ]
        )
        for tool in mcp_tools.tools
        if tool.name in BOX_MCP_TOOLS
    ]


async def generate(prompt: str, llm_client: genai.Client, session: ClientSession = None, tools: list = None):
    def parse_content(content):
        try:
            return parse_json(content.text)
        except json.JSONDecodeError:
            return content.text

    config = (
        types.GenerateContentConfig(temperature=0, tools=tools)
        if session is not None and tools is not None
        else None
    )

    response = llm_client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=config,
    )

    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        response = await session.call_tool(function_call.name, arguments=dict(function_call.args))
        return [parse_content(content) for content in response.content]

    return response.candidates[0].content.parts[0].text


async def extract_invoice_fields(invoice, llm_client, session, tools, progress_cb=None):
    if progress_cb:
        progress_cb(f'Extracting data from bill "{invoice["name"]}"...')

    text_response = await session.call_tool(
        "box_file_text_extract_tool", arguments={"file_id": invoice["id"]}
    )
    bill_text = parse_json(text_response.content[0].text)["content"]

    prompt = (
        "Extract the following fields from this utility bill text: "
        "customer_name, bill_amount_euro, provider_name, due_date, kWh_usage "
        "Return the bill_amount_euro as a float in euros currency. "
        "Return the due_date as it appears on the bill. "
        "Return the kWh_usage as a integer. "
        "Respond with only a JSON object containing these five fields.\n\n"
        f"Bill text:\n{bill_text}"
    )
    response = await generate(prompt, llm_client)
    result = parse_json(response)
    result["file"] = invoice["name"]
    return result


async def run_extraction(folder_id: str, progress_cb=None) -> list[dict]:
    """Connects to the Box MCP server, lists the folder, and extracts fields from every bill in it."""
    llm_client = genai.Client(api_key=GEMINI_API_KEY)
    bills = []

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await get_mcp_tools(session)

            folder_result = await generate(
                f"List the content of the folder with id {folder_id}",
                llm_client,
                session,
                tools,
            )
            invoices = folder_result[0]["folder_items"]

            for invoice in invoices:
                invoice_data = await extract_invoice_fields(
                    invoice, llm_client, session, tools, progress_cb=progress_cb
                )
                bills.append(invoice_data)

    return bills


async def ask_about_bills(question: str, bills: list[dict]) -> str:
    """Answers an open-ended question about already-extracted bill data. No MCP tools needed here."""
    llm_client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        "Here is a list of utility bills as JSON:\n\n"
        f"{json.dumps(bills, indent=2)}\n\n"
        f"Answer this question about the data above: {question}"
    )
    return await generate(prompt, llm_client)
