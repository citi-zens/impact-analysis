# Model Card

## 1. Model Details
This project utilizes two primary distinct models to handle different aspects of the RAG (Retrieval Augmented Generation) pipeline: one for reasoning/generation and one for semantic embedding.

### Primary LLM (Reasoning & Generation)
* *Model Name:* Qwen 2.5 7B (Instruct)
* *Developer:* Qwen Team (Alibaba Cloud)
* *Model Type:* Causal Language Model (Transformer-based)
* *Parameters:* 7.61 Billion
* *Context Window:* up to 128k tokens
* *License:* Apache 2.0
* *Input:* Text (Source Code, Functional Requirements)
* *Output:* Text (Summaries, Impact Analysis Reports, Cypher Queries)

### Embedding Model (Vectorization)
* *Model Name:* nomic-embed-text-v1.5
* *Developer:* Nomic AI
* *Model Type:* Text Embedding (Matryoshka Representation Learning)
* *Context Window:* 8192 tokens
* *License:* Apache 2.0
* *Dimensions:* 768 (variable/resizable)

---

## 2. Intended Use
These models are intended to be used as the core engine for the *CodeGraph RAG* system, specifically for:

* *Source Code Analysis:* Parsing Python files to understand logic flow.
* *Requirement Summarization:* Condensing lengthy Functional Requirement Documents (FRDs) into actionable technical summaries.
* *Graph Query Generation:* Converting natural language questions into Cypher queries to traverse the Neo4j database.
* *Impact Prediction:* Identifying which code components (functions, classes) will be affected by a proposed change.

*Out-of-Scope Use Cases:*
* These models are not designed for generating production-ready code without human review.
* They should not be used for automated refactoring of critical safety systems without "human-in-the-loop" verification.

---

## 3. Why We Chose These Models

### Why Qwen 2.5 7B?
We selected Qwen 2.5 7B over alternatives (like Llama 3 8B or Mistral 7B) for three specific reasons relevant to this hackathon:
1.  *Coding Proficiency:* Qwen 2.5 achieves state-of-the-art performance on coding benchmarks (e.g., HumanEval, MBPP), significantly outperforming other models in the 7B weight class.
2.  *Structured Output:* It has superior capabilities in following complex instructions to generate structured data (like JSON or Cypher queries), which is critical for interacting with our Neo4j database.
3.  *Long Context:* The 128k context window allows us to feed entire file contents or large call graphs into the prompt without truncation.

### Why nomic-embed-text?
We chose nomic-embed-text instead of the standard OpenAI text-embedding-3 for:
1.  *Long Context Support:* It supports an 8192-token context window (vs. the standard 512 or 2048 of many BERT-based models). This allows us to embed entire function bodies rather than just snippets.
2.  *Performance:* It outperforms OpenAI's ada-002 on the MTEB (Massive Text Embedding Benchmark) leaderboard for retrieval tasks.
3.  *Open Source:* It allows for fully local execution, ensuring code privacy.

---

## 4. Known Limitations & Biases

### Qwen 2.5 7B
* *Hallucination:* Like all LLMs, Qwen can confidently generate incorrect information. In the context of code, it might invent function names or libraries that do not exist ("hallucinated dependencies").
* *Language Bias:* While multilingual, the model works best in English and Chinese. Performance on code comments written in other languages may be degraded.
* *Safety Guardrails:* As a "base instruct" model, it has fewer safety refusals than chat-specific models (like ChatGPT). It assumes the user is a developer and will attempt to execute instructions even if they result in "unsafe" code patterns if not explicitly prompted otherwise.

### nomic-embed-text
* *Prefix Sensitivity:* This model is highly sensitive to usage prefixes. It must be prompted with search_query: for questions and search_document: for indexing. Omitting these prefixes results in significantly degraded retrieval quality.
* *Code vs. Natural Language:* While excellent for text, it is a general-purpose embedding model. It may struggle to capture purely syntactic code similarities (e.g., two functions that look different but do the same thing) compared to specialized code-embedding models like CodeBERT.

---

## 5. Ethical Considerations
* *Privacy:* All inference is run locally via Ollama, ensuring that proprietary source code and sensitive functional requirements never leave the user's machine.
* *Automation Risk:* This tool provides recommendations for code changes. Over-reliance on its impact analysis without manual verification could lead to missed regression bugs.