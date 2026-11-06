# Processing Utility Bills Using Box MCP Server

A Streamlit demo app that extracts structured data from utility bills stored in a Box folder, using Gemini and Box MCP Server

## What it does

1. Connects to a Box folder (via the Box MCP server) and lists its files.
2. Extracts text from each utility bill (PDF) using Box's text extraction tool.
3. Uses Gemini to pull structured fields from the bill text: `customer_name`, `bill_amount_euro`, `provider_name`, `due_date`, `kWh_usage`.
4. Displays the results in a table with a summary (total bills, total amount, breakdown by provider).
5. Lets you ask free-form questions about the extracted bill data.

## Project structure

```
2526-CT5230 Capstone AI for SW Project/
├── README.md                    Project overview and setup instructions
├── app.py                       Streamlit demo application (UI)
├── invoice_pipeline.py          Core extraction pipeline (MCP + Gemini orchestration)
├── notebook.ipynb               Exploratory / prototyping notebook
├── requirements.txt             Python dependencies
├── env.example                  Template for required environment variables
├── .env                         Local runtime configuration (not shared)
├── invoices_example/            Sample utility bill PDFs used for validation
│   └── *.pdf                    Six monthly utility bill samples (Jan–Jun 2026)
└── mcp-server-box-main/         Vendored Box MCP Server
    ├── src/
    │   ├── mcp_server_box.py    
    │   ├── server.py            
    │   ├── config.py            
    │   ├── tool_registry/       
    │   └── tools/                
    ├── docs/                    
    ├── tests/                   
    ├── pyproject.toml / uv.lock 
    └── README.md / LICENSE      
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure `uv` is installed in order to run the Box MCP server

3. Upload the utility bills inside a Box folder

4. Copy `env.example` to `.env` and fill in the values:

```bash
cp env.example .env
```

- `BOX_FOLDER_ID` — ID of the Box folder containing the utility bills
- `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, `BOX_SUBJECT_ID`, `BOX_SUBJECT_TYPE` — Box CCG app credentials
- `GEMINI_API_KEY` — Gemini API key

5. Make sure that the mcp-server-box-main directory is present alongside other files

## Running

```bash
streamlit run app.py
```

- The Streamlit app will be automatically opened in the browser. 
- Enter Box folder ID in the app, click **Extract bills** button and review the extracted data.
- Enter any question under Ask a question about these bills, click **Ask** button and review the generated answer.
