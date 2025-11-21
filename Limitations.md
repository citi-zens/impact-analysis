# Limitations & Roadmap

This document provides a transparent overview of the current state of the *CodeGraph RAG* system, acknowledging known technical limitations, bugs, and areas for future development.

## 1. Known Gaps & Functional Limitations

### Language Support
* *Current Status:* The system currently supports *Python (3.x)* exclusively.
* *Limitation:* The AST parser and Call Graph generator are strictly typed for Python syntax. Codebases in Java, JavaScript, or C++ cannot currently be ingested.

### Scope of Analysis
* *Local Scope Only:* The graph analysis only covers the code present within the cloned repository. It does not trace dependencies into external libraries (e.g., if a function calls pandas.read_csv, we stop at the call site and do not analyze the pandas library source code).
* *Static vs. Dynamic:* The system relies on *Static Analysis*. It cannot detect runtime-only dependencies, such as dynamic class loading or eval() statements.

### Graph Granularity
* *Data Flow:* While we capture Control Flow and Call Graphs, we do not currently implement full *Data Flow Analysis* (Taint Analysis). We can see that Function A calls Function B, but we cannot rigorously prove which variables are passed between them if the typing is dynamic.

---

## 2. Known Bugs & Technical Issues

### LLM Hallucinations
* *Issue:* Qwen 2.5 is generally accurate, but when generating Cypher queries for complex relationships (e.g., "Find all functions that call X indirectly through 3 hops"), it may occasionally hallucinate syntax or assume a relationship type that doesn't exist in our schema.
* *Mitigation:* We currently have a "retry" mechanism, but ~5% of complex queries may fail or return empty results.

### Parsing Edge Cases
* *Issue:* The AST parser struggles with complex Python Decorators and Metaclasses.
* *Result:* Functions heavily wrapped in custom decorators may appear as "disconnected" nodes in the graph, missing their inbound/outbound edges.

### Ingestion Latency
* *Issue:* The embedding process (using nomic-embed-text) is currently synchronous.
* *Impact:* Ingesting a repository with >500 files takes significant time (approx. 5-10 minutes).

---

## 3. Future Roadmap

If this project were to continue beyond the hackathon, we would prioritize the following:

### Short Term (v1.1)
* *VS Code Extension:* Build a sidebar plugin that highlights impacted code in real-time as the developer types a requirement.
* *Multi-Language Support:* Integrate tree-sitter to support JavaScript/TypeScript and Java ingestion.

### Medium Term (v2.0)
* *GitHub Actions Integration:* Create a CI/CD pipeline bot that automatically comments on Pull Requests with an "Impact Report" whenever a new feature branch is created.
* *Graph-Native RAG:* Move beyond simple vector similarity. Implement "Graph Traversal RAG" where the LLM is fed the topology of the graph (neighbors of neighbors) to understand architectural patterns, not just text similarity.

### Long Term
* *Auto-Refactoring:* Upgrade the system from identifying impact to applying the changes (e.g., automatically updating function signatures across the codebase).