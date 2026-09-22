---
title: 'Product Guide: PyLabPraxis'
---

# Product Guide: PyLabPraxis

## Vision
PyLabPraxis is a scalable, multi-tiered laboratory automation platform designed to democratize access to advanced robotic workflows. It bridges the gap between high-level ease of use and deep, low-level control, enabling everything from routine sample transfers to complex, optimized experimental designs. By leveraging PyLabRobot, Python, and a modern web stack, PyLabPraxis moves lab automation beyond rigid industrial processes into a flexible, experimental paradigm.

## Target Audience
PyLabPraxis serves a diverse ecosystem of users through a unified but tailored interface:
*   **Wet Lab Scientists:** Focus on execution and basic operations. They benefit from a simple, cognitive-load-reducing UI for tasks like sample transfers, without needing to understand the underlying code.
*   **Automation Engineers:** Focus on creation and optimization. They utilize the full power of Python and PyLabRobot to fine-tune protocols, integrate new instruments, and audit networks.
*   **System Administrators / Maintenance Specialists:** Focus on reliability and uptime. They have visibility into system health, failure points, and network audits.

## Core Features
*   **Unified Protocol Management:** Sophisticated management of protocols as Directed Acyclic Graphs (DAGs), allowing for visual inspection and Python-based editing.
*   **Intelligent Scheduling & Optimization:** An advanced engine that schedules tasks across arbitrary workcells, optimizing for time and cross-contamination constraints.
*   **Role-Based Access Control (RBAC):** Comprehensive identity management that adapts the UI and permissions to the user's role (Researcher vs. Engineer vs. Admin).
*   **Data-Driven Optimization:** Granular data collection from primitive hardware calls to high-level flows, enabling the creation of surrogate Gaussian process models to optimize experimental design automatically.
*   **Real-Time Orchestration:** Direct interface with hardware via PyLabRobot, providing immediate feedback and control.
*   **Enterprise-Grade Data Foundation:** Robust storage, maintenance, and access patterns for all data using PostgreSQL, Redis, and Celery to ensure scalability and auditability.

## Success Metrics
*   **Seamless Orchestration & Simulation (Ultimate Metric):** The seamless optimization, scheduling, and user guidance for executing protocols across a busy set of workcells. This will initially be validated purely through simulation to perfect the scheduling logic and user guidance systems.
*   **Experimental Flexibility:** Reducing the overhead for ad-hoc experiments, treating automation as a tool for discovery.
*   **System Robustness:** Enterprise-quality reliability for data and hardware interactions.
*   **Cognitive Load Reduction:** Abstracting complex actuations into simple UI interactions.
