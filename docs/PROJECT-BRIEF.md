# CostPilot – Agentic AI Cloud Cost Management Platform

> This is the project owner's original brief, kept unchanged for reference. Where it differs from what we build, the [development plan](plan/DEVELOPMENT-PLAN.md) and [decisions](decisions/) explain why.

## 1. Project Overview and Purpose

CostPilot is an AI-powered cloud cost management platform designed to help developers, DevOps engineers, and cloud users understand, monitor, and optimize their cloud infrastructure expenditure. The main purpose of the system is to provide a simple and user-friendly environment where users can upload their cloud billing documents, securely store their financial data, explore historical spending information, identify unusual cost increases, and receive intelligent cost optimization recommendations through an AI-powered chat assistant.

Instead of requiring users to manually analyze large billing reports or navigate complicated cloud management dashboards, CostPilot provides a centralized workspace where users can interact with their own historical billing information using natural language. The platform initially focuses on AWS billing data, with the possibility of supporting other cloud providers in the future.

## 2. User Interface and Main Features

The application will have a clean, minimal, and user-friendly interface with a consistent muted green colour theme. The objective is to avoid complicated navigation and unnecessary features, allowing users to access important information and interact with the AI assistant easily. The main interface will contain four primary sections.

**Overview:** This is the main dashboard that provides a summary of the user's cloud expenditure. It displays total spending, current and previous monthly expenditure, spending changes, historical cost trends, and the most expensive cloud services. It also displays recently uploaded billing documents and important AI-generated optimization recommendations. All financial information will be calculated using the application's deterministic analytics engine rather than relying on AI-generated calculations.

**Documents:** This section allows users to upload and manage their cloud billing documents, including AWS billing CSV files and Cost and Usage Reports. The system validates uploaded documents, processes the billing information, and stores the original documents securely together with their extracted and normalized billing records. Users can view previous uploads, processing statuses, billing periods, and document details. They can also delete documents or reprocess them when necessary.

**Analytics:** This section provides access to historical cloud expenditure and detailed financial analysis. Users can explore monthly and historical spending trends, compare different billing periods, identify expensive cloud services, and investigate unusual expenditure patterns. The system generates these summaries from previously uploaded and stored billing records, allowing users to analyze their historical information without uploading the same documents repeatedly.

**AI Assistant:** This is the main intelligent interaction feature of CostPilot. Users can ask natural-language questions about their cloud expenditure, historical billing information, cost increases, expensive services, and optimization opportunities. The AI assistant automatically accesses the user's authorized historical data, invokes the required analysis tools, retrieves relevant AWS documentation through RAG, and generates evidence-based explanations and recommendations. Users can also ask general cloud cost optimization questions without navigating different sections of the application.

The application will additionally provide a simple settings area for account management, security preferences, and data management.

## 3. Technology Stack and Architecture

CostPilot will follow a modular monolithic backend architecture with a separate frontend application. Instead of creating multiple independent microservices, the backend will contain logically separated modules for document management, billing analytics, AI agents, RAG, security, and reporting. This approach keeps the architecture manageable while maintaining clear separation of responsibilities and allowing individual modules to be extracted into services in the future if necessary.

**Frontend:** Next.js, React, TypeScript, and Tailwind CSS will be used to develop the user interface. Shadcn/UI will provide reusable interface components, while Recharts will be used for financial charts and historical spending visualizations. TanStack Query can manage API data fetching and caching, and React Hook Form with Zod will handle form validation.

**Backend:** Python and FastAPI will be used to develop the backend application. FastAPI will provide REST APIs for authentication, document uploads, billing data management, analytics, and communication with the AI system. Pydantic will handle request validation and structured data validation.

**Database and Storage:** PostgreSQL will be used as the primary relational database to store user accounts, workspaces, billing records, historical summaries, conversations, recommendations, and audit information. AWS S3 will be used for private storage of original billing documents. The system will maintain relationships between users, workspaces, documents, and billing records to ensure that each user can access only their own information.

**Data Processing:** Pandas and NumPy will be used to process uploaded billing information, calculate expenditure, generate service-wise cost breakdowns, compare billing periods, and detect unusual spending patterns. These deterministic calculations will act as the financial source of truth for the AI assistant.

## 4. Agentic AI Architecture

CostPilot will use Google Gemini as its primary large language model, LangChain for LLM integration and tool development, and LangGraph for agent orchestration and workflow management.

LangChain will be responsible for connecting the language model with Python functions, creating agent tools, managing prompts, integrating retrieval systems, and producing structured responses. LangGraph will manage the overall agent workflow, including agent coordination, shared state, conditional routing, and execution of different analysis tasks.

The system will contain a supervisor agent that understands the user's question and determines which analysis operations are required. Specialized agents will handle different responsibilities, such as cost analysis, anomaly investigation, and optimization recommendations. These agents will use controlled Python tools to access historical billing information and perform calculations.

For example, when a user asks why their EC2 expenditure increased, the supervisor agent can route the request to the anomaly investigation workflow. The relevant tools will compare historical EC2 spending, identify unusual increases, and retrieve supporting AWS optimization documentation. The system will then combine the actual financial results and retrieved knowledge to generate a meaningful explanation.

The AI agents will not directly access unrestricted databases or execute arbitrary system commands. They will interact with the application through predefined and permission-controlled tools.

## 5. RAG – Retrieval-Augmented Generation

CostPilot will implement Retrieval-Augmented Generation (RAG) to provide recommendations based on reliable cloud documentation instead of depending entirely on the language model's existing knowledge.

LangChain will be used to implement the RAG pipeline, including document loading, text splitting, embedding generation, and retrieval. AWS documentation, EC2 optimization guides, S3 storage recommendations, RDS optimization information, and the AWS Well-Architected Framework will form the initial knowledge base.

Google embedding models will convert documentation into vector embeddings, which will be stored in ChromaDB. When a user asks a cloud optimization question, the system retrieves relevant documentation from the vector database and supplies the retrieved information as context to the AI agent.

The agent will combine retrieved documentation with the user's actual billing information to generate relevant recommendations. The RAG knowledge base will primarily contain trusted cloud documentation rather than unrestricted access to users' private billing information. User-specific billing data will be retrieved through authenticated analytics tools.

## 6. AI Hallucination Prevention, Guardrails, and Trust Layer

An important requirement of CostPilot is to reduce incorrect AI-generated financial information and prevent unsupported optimization recommendations. The system will implement multiple validation layers rather than relying only on the language model to produce accurate answers.

First, all financial calculations will be performed using deterministic Python functions and Pandas. The AI model will not independently calculate or invent expenditure totals, percentages, or historical cost differences. It will receive verified calculation results from the analytics engine.

Second, RAG will provide supporting AWS documentation for cloud optimization recommendations. The system will validate whether retrieved information is relevant to the user's question and use the available documentation as supporting evidence.

Third, Pydantic and custom Python validation rules will validate AI-generated structured responses. Recommendations will be checked against available billing information, retrieved documentation, and application policies. Unsupported savings estimates will be rejected or marked as unavailable when the system does not have sufficient infrastructure utilization information.

The platform will also implement guardrails for input validation, prompt injection protection, restricted tool execution, output validation, and permission checking. Uploaded billing documents and retrieved documents will be treated as untrusted data rather than instructions to the AI agent.

An evidence-based confidence and grading mechanism will classify recommendations according to the availability and quality of their supporting information. This will be based on measurable evidence completeness and validation results rather than relying only on the AI model's self-reported confidence.

For more advanced AI evaluation, DeepEval or Ragas can be introduced to evaluate answer relevance, retrieval quality, and whether generated recommendations are supported by retrieved information. An LLM-as-a-Judge approach can also be used as an additional evaluation mechanism, supported by deterministic validation and human-reviewed test cases.

The system will maintain audit records of agent activities, including the tools executed, relevant evidence retrieved, validation outcomes, and final recommendations. This allows users to understand how the system generated its results without exposing internal model reasoning.

## 7. Data Security, Encryption, and Privacy

Security and privacy will be important design considerations because CostPilot handles users' cloud billing information and potentially sensitive infrastructure expenditure details.

All communication between the frontend and backend will be protected using HTTPS and TLS. PostgreSQL and document storage will use encryption at rest. For stronger document protection, the system can implement AES-256-GCM encryption with envelope encryption, where document encryption keys are protected using AWS Key Management Service (KMS).

User authentication and authorization will ensure that each user can access only their own workspace and associated billing records. Backend authorization checks and PostgreSQL Row-Level Security can provide additional protection against unauthorized cross-user data access.

Uploaded documents will be validated before processing, and API credentials and encryption keys will never be stored directly in source code. Sensitive configuration will be managed using environment variables and appropriate secrets management services.

It is important to distinguish encryption at rest from true end-to-end encryption. Since the backend AI system needs to process decrypted billing information to perform analytics and generate recommendations, the initial architecture will use strong encryption in transit and at rest with controlled backend access, rather than claiming strict end-to-end encryption. A future client-side encryption architecture could be considered if strict end-to-end confidentiality becomes a requirement.

The system will also provide secure data deletion, encrypted backups, access logging, and appropriate data retention controls.

## 8. DevOps and DevSecOps Practices

CostPilot will incorporate modern DevOps and DevSecOps practices throughout the development and deployment process.

Docker will be used to containerize the Next.js frontend and FastAPI backend, while Docker Compose will manage the initial application environment and its dependencies. Git and GitHub will be used for source code management and collaborative development.

GitHub Actions will implement the CI/CD pipeline. Whenever developers push code or create pull requests, automated workflows will execute code quality checks, security scans, automated tests, and Docker image builds.

Pytest will be used for backend testing, while Vitest can be used for frontend testing. Ruff will handle Python linting and formatting. Gitleaks will detect accidentally committed API keys and sensitive credentials, while Bandit will perform static security analysis of Python code.

Trivy will scan Docker images, operating system packages, dependencies, and infrastructure configurations for known vulnerabilities. Checkov will be introduced to validate Terraform infrastructure configurations and identify insecure cloud resource settings.

GitHub Container Registry (GHCR) can store the successfully built and scanned Docker images. Terraform will be used as Infrastructure as Code to provision cloud resources such as EC2 instances, networking, security groups, and storage configurations.

For application monitoring and observability, Prometheus and Grafana can be introduced to monitor backend performance, resource utilization, and application health. OpenTelemetry can provide distributed tracing and help investigate requests across the frontend, backend, and AI execution workflow.

These practices will help ensure that CostPilot is not only functional but also maintainable, secure, and deployable using modern software engineering and DevOps practices.

## 9. Overall Application Workflow

The application follows a straightforward workflow from document upload to AI-powered analysis.

First, users register and authenticate themselves to access their personal CostPilot workspace. They upload cloud billing documents through the Documents section. The backend validates the files, processes their contents using Pandas, normalizes the billing records, and stores the original documents securely in private object storage. The extracted billing records and associated metadata are stored in PostgreSQL.

After processing, the system automatically updates historical expenditure summaries, service-wise spending information, and cost trends. Users can access this information through the Overview and Analytics sections without repeatedly uploading previous billing documents.

When users interact with the AI Assistant, the backend identifies the authenticated workspace and provides access to the relevant historical billing information through controlled analysis tools. LangGraph coordinates the appropriate agent workflow, while LangChain manages the LLM integrations, tools, and RAG retrieval process. ChromaDB retrieves relevant AWS documentation, and Gemini generates a response based on the available financial evidence and retrieved knowledge.

Before the response is displayed, the system performs structured output validation, evidence checks, and policy-based guardrail checks. The final response includes the findings, supporting information, recommendations, and limitations where necessary. Agent activities and relevant results are recorded in the audit system.

Through this process, users can continuously upload new billing documents, build a historical record of cloud expenditure, investigate financial changes, and receive increasingly useful cost optimization insights from their own stored information.

## 10. Overall Project Objective

The ultimate objective of CostPilot is to create a secure, intelligent, and user-friendly cloud cost management assistant that combines traditional financial analytics with Agentic AI and Retrieval-Augmented Generation.

By integrating LangChain, LangGraph, Gemini, RAG, ChromaDB, deterministic analytics, AI guardrails, and modern DevSecOps practices, the platform aims to provide more than a conventional cloud cost dashboard. It will allow users to understand their cloud expenditure through natural-language interaction while ensuring that financial calculations remain deterministic, recommendations are evidence-based, and user data is protected through appropriate security controls.

The project will demonstrate practical applications of Agentic AI, RAG, FinOps, secure data management, CI/CD automation, containerization, Infrastructure as Code, DevSecOps, and application observability within one integrated software engineering platform.
