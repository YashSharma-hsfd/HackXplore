# HackXplore
repo for hackathon, building solution using RAG's 
## Problem Statement 
Knowledge about two-stroke engines is highly fragmented and scattered across forums, manuals and individual experience. As a result, it is difficult to access, poorly structured and often cannot be used efficiently. We are looking for an AI-powered solution that centrally collects and structures this knowledge and makes it available in an intelligent way.
## Detailed Problem Statement
Two-stroke engines are still used in specialist applications such as motor sport, small appliances and classic cars. However, knowledge regarding maintenance, tuning and optimisation is highly fragmented and is often stored in unstructured sources such as forums, PDFs or personal experience.
This leads to inefficiencies, repeated mistakes and a continuous loss of valuable expert knowledge. At the same time, modern technologies – particularly artificial intelligence – offer new opportunities to structure this knowledge, link it together and make it more accessible.
The challenge lies in developing an AI-powered knowledge database that aggregates, structures and intelligently expands existing knowledge. Users should be able to find relevant information quickly, ask specific questions and, at the same time, contribute to expanding the knowledge base. The aim is to create a dynamic, intelligent system from scattered information that offers real added value to both beginners and experts.
## Expected Solution
We are looking for innovative, practical and scalable solutions that demonstrate how AI can be used to structure and utilise specialist knowledge.
Ideally, the solution should include:
A prototype knowledge database or platform
Integration of AI functions (e.g. semantic search, chatbot, recommendation system)
A concept for data collection, structuring and maintenance
An intuitive user interface for interacting with the content
Optional but valuable aspects:
Use of real-world data sources (e.g. forums, manuals, datasets)
Intelligent tagging, categorisation or knowledge graphs
Personalisation or machine learning systems
The focus is on creativity, technical feasibility and a clearly recognisable benefit for users. The solution should demonstrate how it can be implemented in practice and further developed in the long term.
## Suggested Solution
A enterprise-grade Retrieval-Augmented Generation (RAG) solution. This engine combines **GraphRAG** (for deep context and relationship mapping) with **Hybrid Search** to deliver exceptionally accurate, grounded, and context-aware responses from a centralized knowledge base.

---

## Architecture & Core Stack

###  Backend & AI Pipeline
* **Data Ingestion & OCR:** `Google Gemini 2.5 Flash` — Parses complex layouts, multi-column documents, tables, and images into structured data.
* **Embeddings & Retrieval:** `BGE-M3` — Executes native hybrid search by unifying dense semantic vector retrieval and sparse lexical matching.
* **Knowledge Base Architecture:** `Knowledge Graph + Vector Store` — Structures data points globally to surface interconnected concepts across separate documents.
* **Core Language Model (LLM):** `Mistral Small 3.2 (24B)` — Handles complex reasoning, synthesis, and final answer generation.
* **Guardrails & Evaluation:** `Gemini 3.1 Flash Lite (LLM Judge)` — Evaluates outputs in real-time for groundedness, context relevance, and hallucination prevention.

###  Frontend
* **UI Framework:** `React` with `Vite` — Provides a lightning-fast, reactive, and fluid user interface supporting streaming text responses.

---

##  Key Features

* **Multi-Format Ingestion:** Seamlessly process and extract data from multiple file types (PDFs, Images, DOCX, TXT, etc.) into the centralized knowledge base.
* **Graph-Powered Insights:** Beyond traditional chunk-based RAG, our GraphRAG layer maps entity relationships, allowing the system to answer complex "global" queries across the entire database.
* **Live Database Synchronization:** Features an active update pipeline to keep the underlying knowledge base completely in sync with your team's live developments.
* **Hybrid Web Grounding:** Dynamically fetches live web information when necessary to prevent data obsolescence, automatically flagging and separating web-sourced content in the UI for maximum transparency.
