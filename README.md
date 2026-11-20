\# Preflight-CI 🚀

\### AI-Assisted Risk Analysis for Banking \& FinTech CI/CD Pipelines



\*\*Identify potential software risks before they reach production.\*\*



Preflight-CI is an AI-assisted Continuous Integration (CI) risk analysis prototype designed for banking and financial technology applications. It analyses software changes during the GitHub Pull Request (PR) workflow to identify potentially breaking API changes, downstream service impact, and configured compliance-related risk signals.



Instead of waiting for problems to appear after deployment, Preflight-CI helps developers and reviewers understand potential risks before merging code.



\---



\## 💡 The Problem



Banking applications often consist of multiple interconnected microservices communicating through APIs.



A seemingly small code change can introduce unexpected problems:



\- Removing an API response field may break downstream services.

\- Changing an API contract may affect applications that depend on it.

\- Changes in one service may have consequences for other connected services.

\- Compliance-related risks may go unnoticed during manual code reviews.



Traditional code reviews depend heavily on developers identifying these risks manually.



\*\*The challenge:\*\* How can development teams identify and understand potential risks earlier in the software development lifecycle?



\## 🎯 Our Solution



Preflight-CI introduces an automated risk-analysis layer into the GitHub Pull Request workflow.



When a developer submits a pull request, Preflight-CI analyses the relevant changes, generates structured findings, and provides feedback to help reviewers investigate potential issues before merging.



\### Core Capabilities



| Capability | What it does |

|---|---|

| API Contract Analysis | Compares API specifications and identifies potentially breaking changes, such as removed response fields. |

| Dependency Impact Analysis | Identifies potentially affected downstream services based on available dependency information. |

| Compliance Checks | Detects configured compliance-related risk signals in the analysed code. |

| RAG-Based Policy Retrieval | Retrieves relevant policy context from an indexed knowledge base to support risk explanations. |

| AI-Assisted Explanations | Helps explain identified technical findings using available evidence and retrieved context. |

| GitHub Integration | Runs analysis through the pull request workflow and provides feedback through PR comments and JSON reports. |



\## ⚙️ How It Works



```mermaid

flowchart TD

&#x20;   A\["Developer creates a Pull Request"] --> B\["GitHub Actions Workflow"]

&#x20;   B --> C\["Detect relevant code changes"]

&#x20;   C --> D\["Preflight-CI Analysis Engine"]



&#x20;   D --> E\["API Contract Analysis"]

&#x20;   D --> F\["Dependency Impact Analysis"]

&#x20;   D --> G\["Compliance Checks"]



&#x20;   E --> H\["Structured Risk Findings"]

&#x20;   F --> H

&#x20;   G --> H



&#x20;   H --> I\["Policy Retrieval using RAG"]

&#x20;   I --> J\["AI-Assisted Risk Explanation"]

&#x20;   J --> K\["Structured Risk Report"]



&#x20;   K --> L\["GitHub Pull Request Comment"]

&#x20;   K --> M\["JSON Report Artifact"]

```



\### Step-by-Step Workflow



\*\*1. Pull Request Detection\*\*



A developer pushes code changes and creates or updates a GitHub Pull Request. The GitHub Actions workflow triggers Preflight-CI.



\*\*2. Technical Risk Analysis\*\*



The analysis engine examines relevant changes using specialised analysers:



\- API analyser: checks changes in API specifications.

\- Dependency analyser: examines available service dependency information.

\- Compliance analyser: checks configured compliance-related patterns.



\*\*3. Policy Retrieval (RAG)\*\*



The Retrieval-Augmented Generation (RAG) component retrieves relevant policy passages from the indexed knowledge base using semantic similarity search.



\*\*4. AI-Assisted Explanation\*\*



The retrieved context and structured analyser findings can be used to generate explanations of the identified risks.



\*\*5. Risk Reporting\*\*



Preflight-CI generates a structured JSON report and provides feedback through the GitHub Pull Request workflow.



\## 🔍 Example: API Contract Change Detection



Consider a payment API that previously returned:



\*\*Previous API response\*\*



```json

{

&#x20; "transaction\_id": "TX123",

&#x20; "amount": 500,

&#x20; "status": "SUCCESS"

}

```



A developer modifies the API specification and removes `transaction\_id`.



\*\*Updated API response\*\*



```json

{

&#x20; "amount": 500,

&#x20; "status": "SUCCESS"

}

```



Preflight-CI compares the previous and updated API specifications.



It identifies that `transaction\_id` existed in the previous response schema but is missing from the updated schema.



\*\*Example finding:\*\*



```text

Finding: RESPONSE\_FIELD\_REMOVED

Severity: HIGH

Endpoint: POST /payments

Removed Field: transaction\_id



Potential Impact:

Downstream services that depend on transaction\_id

may experience integration issues.



Suggested Action:

Review dependent services and verify API compatibility

before merging the change.

```



\*Note: This is a potential breaking change. Actual impact depends on whether downstream consumers rely on the removed field.\*



\## 🧠 Why RAG?



Traditional analysers identify technical changes, but developers may also need to understand the relevant organisational policies and engineering guidelines.



Preflight-CI uses Retrieval-Augmented Generation (RAG) to connect technical findings with relevant policy context.



\*\*RAG workflow:\*\*



1\. Policy documents are processed and split into smaller text chunks.

2\. Embeddings are generated for the text chunks.

3\. The indexed content is stored in ChromaDB.

4\. A query based on an analyser finding is used to retrieve relevant policy passages.

5\. Retrieved context can support the AI-assisted explanation.



The analyser identifies the technical issue. RAG retrieves relevant context. The LLM helps explain the finding.



\## 🛠️ Technology Stack



| Technology | Purpose |

|---|---|

| Python | Core implementation and analysis logic |

| GitHub Actions | Pull Request automation |

| OpenAPI / YAML | API specification representation |

| ChromaDB | Vector storage and semantic retrieval |

| Embedding Functions | Convert text into vector representations |

| RAG | Retrieve relevant policy context |

| Large Language Models | AI-assisted risk explanations |

| JSON | Structured risk reporting |



\## 📊 Sample Output



Preflight-CI produces structured findings that can be used by developers and reviewers.



Example:



```json

{

&#x20; "finding": "RESPONSE\_FIELD\_REMOVED",

&#x20; "severity": "HIGH",

&#x20; "endpoint": "POST /payments",

&#x20; "field": "transaction\_id",

&#x20; "potential\_impact": "Dependent services may be affected",

&#x20; "recommended\_action": "Review API compatibility"

}

```



The actual report contains findings generated by the configured analysers.



\## 🚀 Getting Started



\### Prerequisites



\- Python 3.10 or later

\- Git

\- GitHub account

\- Access to a GitHub repository

\- GitHub Actions enabled for the repository



\### 1. Clone the Repository



```bash

git clone https://github.com/shanthidhaneswaran-rgb/preflightci.git

cd preflightci

```



\### 2. Create a Virtual Environment



\*\*Windows:\*\*



```cmd

python -m venv .venv

.venv\\Scripts\\activate

```



\### 3. Install Dependencies



If a `requirements.txt` file is available:



```cmd

pip install -r requirements.txt

```



\### 4. Run the Local Report Generator



```cmd

python -m src.ci\_report

```



Check the generated report:



```cmd

type reports\\preflight\_report.json

```



The local execution may use sample/demo input depending on the configured execution mode.



\### 5. GitHub Actions Integration



The repository includes a GitHub Actions workflow under:



```text

.github/workflows/

```



The workflow is designed to trigger on pull request events, execute the analysis, and publish the resulting report through the GitHub workflow.



For an actual pull request demonstration:



1\. Push a change to a feature branch.

2\. Create or update a pull request.

3\. Open the repository's Actions tab.

4\. Inspect the Preflight-CI workflow run.

5\. Review the automated pull request feedback.

6\. Download the generated JSON artifact when available.



\## 🏦 Real-World Use Case



Consider a banking platform containing:



\- Payment Service

\- Account Service

\- Fraud Detection Service

\- Transaction History Service



These services may depend on shared API contracts.



If a developer modifies a payment API, Preflight-CI can help identify potentially breaking changes and highlight available downstream dependency information.



This helps:



\- \*\*Developers:\*\* Understand potential risks introduced by their code changes.

\- \*\*Code reviewers:\*\* Review evidence-backed findings before approving changes.

\- \*\*DevOps teams:\*\* Integrate risk analysis into existing CI/CD workflows.

\- \*\*Banking organisations:\*\* Improve visibility into potential integration and compliance-related risks.



Preflight-CI is designed to support engineering decisions, not replace human review or existing security and compliance processes.



\## 🔐 Scope and Limitations



Preflight-CI is currently a prototype under development.



\- API analysis depends on the availability and accuracy of previous and updated API specifications.

\- Dependency analysis depends on the available service relationship information.

\- Compliance checks identify configured risk signals; they do not certify regulatory compliance.

\- RAG retrieval quality depends on the indexed documents and retrieval configuration.

\- AI-generated explanations require validation against the underlying findings and retrieved evidence.

\- Production adoption would require security validation, access controls, privacy safeguards, performance testing, and organisation-specific integration.



\## 🔮 Future Enhancements



\- Support for additional API specification formats and contract validation.

\- Improved service dependency discovery.

\- More comprehensive policy knowledge bases.

\- Retrieval evaluation and improved ranking.

\- Enhanced developer-facing menu-driven dashboard.

\- Integration with additional CI/CD platforms.

\- Historical risk trends and reporting.

\- Controlled enterprise deployment and governance.



\## 👥 Team



\*\*Project:\*\* Preflight-CI  

\*\*Domain:\*\* Artificial Intelligence | DevSecOps | CI/CD | FinTech



Developed as a project focused on identifying potential software risks earlier in the development lifecycle.



\## 🏆 Achievement



\*\*4th Prize – TEJAS 2026\*\*



Organised by \*\*Temenos\*\*.



The project was presented to industry judges from Temenos, providing valuable feedback on its technical approach and potential application in banking and financial technology development workflows.



\---



\## 📌 Repository



GitHub: https://github.com/shanthidhaneswaran-rgb/preflightci



\*\*Preflight-CI — Identify risks before they reach production.\*\*

