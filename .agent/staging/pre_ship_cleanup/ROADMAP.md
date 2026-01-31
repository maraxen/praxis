# Project Roadmap

For immediate post-release plans, see [POST_SHIP.md](./POST_SHIP.md). For known issues and smaller improvements, see [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md).

This document tracks high-level strategic goals, long-term features, and major architectural milestones for Praxis.

## Focus Areas

For detailed post-ship (v0.1-Alpha+) tasks and architectural refinements, see [POST_SHIP.md](./POST_SHIP.md).

## Long Term

1. **Plugin & Definition Marketplace**
    - **Goal**: Create a secure ecosystem for sharing functionality and hardware definitions.
    - **Description**: Enable third-party developers to add new capabilities (device drivers, protocol libraries, analysis tools) and hardware definitions without modifying the core codebase.
    - **Key Components**:
        - **Vetted Database**: A central, curated repository for verified Machine and Resource definitions to ensure reliability and safety.
        - **Marketplace**: A user-facing mechanism to discover, publish, and install both plugins (functionality) and definitions (hardware).
        - **Security**: robust sandboxing of third-party plugins to prevent malicious execution or accidental interference with the core system.
    - **Research Needed**: Investigation into architecture options, comparing approaches like:
        - Git-based registries (like Homebrew/Cargo)
        - Package manager integrations (PyPI/npm)
        - VSX-style extension host architecture

2. **Local NLP (FunctionGemma)**
    - **Goal**: Natural language processing for protocol generation running locally.
    - **Description**: Integrate local LLMs (like FunctionGemma) to interpret natural language requests and generate valid protocol definitions, ensuring data privacy and offline capability.

3. **DAG Optimization**
    - **Goal**: Computational graph representation of protocols for automatic optimization.
    - **Description**: Represent protocols as Directed Acyclic Graphs (DAGs) to analyze dependencies and automatically optimize execution through parallelization and batching of operations.
