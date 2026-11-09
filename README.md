GrantAI -- AI-Powered Grant and Funding Finder for Startups
GrantAI is an AI-powered, multi-agent platform designed to help startups
discover relevant grants and funding opportunities, understand
eligibility requirements, track application deadlines, and prepare
customized proposal drafts.

The project is designed around IBM Granite, IBM watsonx.ai, and
IBM Cloud Lite services. A Retrieval-Augmented Generation (RAG)
pipeline retrieves relevant information from configured funding sources
to help ground AI-generated responses.
Project status: Update this README to reflect what is actually
implemented. Do not describe planned features as completed
functionality.

Problem Statement
Funding information is spread across government portals, private funding
platforms, and official scheme documents. Startup founders may need to
manually compare eligibility rules, funding amounts, deadlines, and
document requirements. GrantAI aims to simplify this process through a
centralized funding assistant.
Key Features
- Funding discovery: Find grants, startup schemes, and funding
  opportunities from configured sources.
- Eligibility matching: Compare startup details such as domain,
  stage, location, and funding requirement with opportunity criteria.
- Deadline and compliance assistance: Extract application
  deadlines, required documents, and submission guidelines.
- AI proposal drafting: Generate a customized first draft for a
  selected funding opportunity.
- RAG-based retrieval: Retrieve relevant passages from stored
  funding documents before generating answers.
- Funding dashboard: Display recommended opportunities,
  eligibility information, deadlines, and proposal drafts.
- Human review: Allow users to verify information and edit drafts
  before applying.
Multi-Agent Architecture
  Agent                               Responsibility
  Funding Discovery Agent             Searches configured sources and
collects funding opportunities.

  Eligibility Matching Agent          Compares startup details with each
opportunity's eligibility
conditions.

  Deadline and Compliance Agent       Extracts deadlines, required
documents, and application
guidelines.
AI Proposal Generation Agent        Prepares a customized proposal
draft for user review.
The agents are coordinated by a Python backend and can use IBM Granite
through IBM watsonx.ai for language understanding, reasoning,
extraction, summarization, and generation.
Technology Stack
  Technology                          Purpose
  IBM Granite                         Core language model for AI analysis
and generation.

  IBM watsonx.ai                      Access to supported Granite models.

  IBM Cloud Lite services             Cloud infrastructure and storage,
subject to service availability and
plan limits.

  Python                              Agent logic, data processing, and
RAG pipeline.

  FastAPI                             Backend APIs and agent
coordination.

  Streamlit or React                  User interface and funding
dashboard; specify the one used.

  ChromaDB or FAISS                   Vector storage and semantic
retrieval; specify the one used.
RAG                                 Retrieves relevant funding
information to ground AI responses.
Confirm the exact IBM service names, model ID, and Lite-plan
entitlements in your IBM Cloud account.
System Workflow
1. The user enters startup details, including domain, stage, location,
   and funding requirement.
2. The backend validates the profile and coordinates the agents.
3. The Funding Discovery Agent searches configured funding sources.
4. The RAG pipeline retrieves relevant information from the funding
   knowledge base.
5. The Eligibility Matching Agent compares opportunity criteria with
   the startup profile.
6. The Deadline and Compliance Agent extracts important dates and
   application requirements.
7. The AI Proposal Generation Agent creates a draft for the selected
   opportunity.
8. The dashboard displays the results for user review.
Suggested Project Structure
Adapt this structure to match your actual repository:
GrantAI/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── agents/
│   │   ├── funding_discovery.py
│   │   ├── eligibility_matching.py
│   │   ├── deadline_compliance.py
│   │   └── proposal_generation.py
│   ├── rag/
│   │   ├── ingestion.py
│   │   ├── retrieval.py
│   │   └── vector_store.py
│   ├── services/
│   │   └── granite_service.py
│   └── models/
│       └── schemas.py
├── frontend/
│   └── streamlit_app.py
├── data/
│   └── README.md
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
Prerequisites
- Python 3.10 or a version supported by your dependencies.
- Git.
- An IBM Cloud account with access to the required watsonx.ai service
  and a supported Granite model.
- The credentials and project/endpoint details required by your IBM
  watsonx.ai deployment.
- ChromaDB or FAISS, depending on your implementation.
Setup and Installation
1. Clone the repository
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd GrantAI
2. Create and activate a virtual environment
Windows:
python -m venv .venv
.venv\\Scripts\\activate
macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables
Create a .env file based on .env.example.

Example placeholders (use the exact variable names expected by your
code):
IBM_WATSONX_API_KEY=your_api_key
IBM_WATSONX_URL=your_watsonx_endpoint
IBM_WATSONX_PROJECT_ID=your_project_id
IBM_GRANITE_MODEL_ID=your_supported_granite_model_id
Never publish real API keys, access tokens, passwords, or private
project identifiers.
5. Add funding data
Add only permitted public funding documents or data to the configured
ingestion location. Prefer official government and funding-organization
sources. Store each source URL and retrieval date so users can verify
whether information is current.
6. Run the application
Use the entry points present in your repository. For example:

FastAPI backend:
uvicorn app.main:app --reload
Streamlit frontend:
streamlit run frontend/streamlit_app.py
Replace these example commands if your project uses different file names
or entry points.
IBM Granite Integration
GrantAI uses IBM Granite through IBM watsonx.ai. The application sends
prompts and relevant retrieved funding context to the configured Granite
model for tasks such as summarizing funding opportunities, extracting
eligibility requirements and deadlines, comparing startup profiles, and
drafting application content.

The model ID and endpoint must match the deployment available in your
watsonx.ai account.
RAG Pipeline
1. Collect permitted grant documents and official funding information.
2. Extract and clean document text.
3. Split text into manageable chunks.
4. Generate embeddings using the embedding model configured in the
   project.
5. Store embeddings and metadata in ChromaDB or FAISS.
6. Retrieve relevant chunks for a user's question.
7. Pass the retrieved context to IBM Granite to generate a grounded
   response.
Display source names, links, and retrieval dates where possible. If
information cannot be verified from retrieved material, the application
should say so rather than inventing an answer.
Responsible Use and Limitations
- Funding information can change. Users must verify eligibility,
  deadlines, amounts, and conditions on the official funding portal.
- Eligibility matches are decision-support suggestions, not official
  approval.
- AI-generated proposals are drafts and must be checked and edited by
  the startup.
- Do not automatically submit applications through confidential,
  restricted, or login-protected portals.
- Respect website terms, API conditions, copyright, and applicable
  laws when collecting information.
- Protect startup profiles and uploaded documents; collect only
  information needed for the service.
- Never commit .env files, API keys, private documents, or personal
  data to GitHub.
Testing
Test profile validation, funding source retrieval, eligibility matching,
deadline extraction, RAG relevance, IBM Granite API error handling,
proposal generation, and protection of credentials and user data.
Future Enhancements
- Integration with additional government and private funding APIs.
- Voice assistance and multilingual support.
- Improved proposal generation using approved templates and verified
  examples.
- Notifications for new grants and approaching deadlines.
- Expanded coverage of accelerators, competitions, and international
  funding.
Contributors
- Asad Sheikh -- Project development
Add other team members and their contributions if applicable.
