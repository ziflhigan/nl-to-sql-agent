# Real-time Streaming NL-to-SQL Agent

This project is a sophisticated, full-stack application that features a powerful Natural Language to SQL (NL-to-SQL) agent. It is designed to bridge the gap between human language and structured databases, enabling users to gain insights from complex data through an intuitive, real-time conversational interface.

The core vision is to democratize data access, allowing non-technical users to ask complex questions—involving multi-table joins and aggregations—and receive answers in plain, understandable English or Multi-Lingual. The application's frontend is built with React and TypeScript, while the robust backend leverages Python, Flask, and the powerful Google Gemini LLM, orchestrated by LangChain.

## Project Highlights

  * **Natural Language to SQL:** Translates plain English or Multi-Lingual questions into executable SQL queries.
  * **Real-time Streaming:** The agent's thought process is streamed to the user in real-time using Server-Sent Events (SSE), offering a transparent and engaging user experience.
  * **ReAct Framework:** The AI core employs a ReAct (Reasoning and Acting) loop, allowing users to see the agent's step-by-step reasoning as it explores the database, formulates queries, and synthesizes answers.
  * **Decoupled, Professional Architecture:** The system is built on professional software engineering principles, including a strictly decoupled three-tier architecture (React Frontend, Flask Backend API, AI Service). This modular design ensures the system is scalable, maintainable, and flexible.
  * **Interactive & Animated UI:** A modern frontend built with React, TypeScript, and Tailwind CSS provides a highly interactive and visually appealing user experience, with animations managed by Framer Motion.
  * **Robust Backend Services:** The backend is not a monolithic script but a collection of well-defined services for LLM interaction, database management, and agent orchestration, featuring comprehensive logging and error handling.

## High-Level Overview
![High-Level-Overview](https://github.com/user-attachments/assets/befd338b-4e7f-4b6f-b418-453967619e35)

## Demo & Screenshots

### Live Application Demo

Watch the real-time streaming agent in action as it interprets a user's question, thinks through the problem, and delivers the final answer.

https://github.com/user-attachments/assets/ceb13379-93ff-4230-9aad-f1c2da7758ae

### Backend Logging

The backend features a robust, centralized logging system that separates informational logs from errors, with daily rotation. This is crucial for monitoring and debugging in both development and production environments.

**Info Logs**
![Screenshot 2025-06-22 211745](https://github.com/user-attachments/assets/8a368a7e-dc1d-44fa-86d8-699c40e32f13)
![Screenshot 2025-06-22 211802](https://github.com/user-attachments/assets/fddedaf0-9550-4713-b876-0e5041ddf5af)


## How to Set Up and Run the Project

Follow these steps to get the application running locally.

### Prerequisites

  * Python 3.10 or newer.
  * Node.js and npm (or a compatible package manager).

### Step 1: Clone the Repository

```bash
git clone https://github.com/ziflhigan/nl-to-sql-agent.git
cd nl-to-sql-project
```

### Step 2: Configure the Backend

1.  **Navigate to the backend directory.**

    ```bash
    cd backend
    ```

2.  **Create and activate a Python virtual environment.**

      * On macOS / Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
      * On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install the required Python packages.**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Download the Chinook Database.**

      * Download the `chinook.db` SQLite file from a public resource like [SQLite Tutorial](https://www.sqlitetutorial.net/sqlite-sample-database/).
      * Unzip the file and place `chinook.db` inside the `backend/data/` directory.

5.  **Set up your environment variables.**

      * Create a `.env` file in the `backend/` directory by copying the example file.
        ```bash
        cp .env.example .env
        ```
      * **Get your Google API Key:** Obtain an API key from [Google AI Studio](https://aistudio.google.com/apikey).
      * **Edit the `.env` file:** Open the newly created `.env` file and replace the placeholder values with your actual credentials and desired configuration.

    **`.env` file content:**

    ```env
    # =============================================================================
    # Environment Configuration Template
    # =============================================================================
    # Copy this file to .env and fill in your actual values
    # NEVER commit the actual .env file to version control

    # =============================================================================
    # Google Gemini API Configuration
    # =============================================================================
    # Get your API key from: https://makersuite.google.com/app/apikey
    GOOGLE_API_KEY="your_google_ai_api_key_here"

    # Gemini model to use for SQL agent
    # Options: gemini-1.5-flash-latest, gemini-1.5-pro-latest, gemini-pro
    GEMINI_MODEL_NAME="gemini-1.5-flash-latest"

    # =============================================================================
    # Database Configuration
    # =============================================================================
    # SQLite database connection string
    # For SQLite: sqlite:///path/to/database.db
    DATABASE_URI="sqlite:///data/chinook.db"

    # =============================================================================
    # Flask Application Configuration
    # =============================================================================
    # Flask secret key for session management (generate a random string)
    SECRET_KEY="your-secret-key-for-flask-sessions"

    # Flask environment: development, production, testing
    FLASK_ENV="development"

    # Flask debug mode: True for development, False for production
    FLASK_DEBUG="True"

    # Application host and port
    FLASK_HOST="0.0.0.0"
    FLASK_PORT="5000"

    # =============================================================================
    # CORS Configuration
    # =============================================================================
    # Frontend origin for CORS (React development server)
    CORS_ORIGINS="http://localhost:5173"

    # =============================================================================
    # Logging Configuration
    # =============================================================================
    # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL="INFO"

    # Enable/disable file logging
    LOG_TO_FILE="True"

    # Enable/disable console logging
    LOG_TO_CONSOLE="True"

    # =============================================================================
    # LangChain Agent Configuration
    # =============================================================================
    # Enable verbose mode for LangChain agent (shows ReAct loop)
    AGENT_VERBOSE="True"

    # Agent type for create_sql_agent. 'tool-calling' is recommended for Gemini.
    AGENT_TYPE="tool-calling"

    # Maximum iterations for agent execution
    AGENT_MAX_ITERATIONS="15"

    # LLM temperature (0.0 for deterministic, 1.0 for creative)
    LLM_TEMPERATURE="0.0"
    ```

### Step 3: Configure the Frontend

1.  **Navigate to the frontend directory.**

    ```bash
    cd ../frontend
    ```

2.  **Install the required Node.js packages.**

    ```bash
    npm install
    ```

### Step 4: Run the Application

1.  **Start the Backend Server:** Open a terminal, navigate to the `backend/` directory, and run:

    ```bash
    python app.py
    ```

    The Flask server will start on `http://localhost:5000`.

2.  **Start the Frontend Development Server:** Open a second terminal, navigate to the `frontend/` directory, and run:

    ```bash
    npm run dev
    ```

    The React application will be available at `http://localhost:5173`.

3.  **Open your browser** and navigate to `http://localhost:5173` to start interacting with the agent.

## Technology Stack & Architecture

This project adopts a professional, multi-layered architecture to ensure long-term viability, scalability, and maintainability. The strict decoupling of the frontend, backend web server, and core AI logic is a hallmark of robust software engineering.

| Component | Technology | Rationale                                                                                                                                                                                                                                                                                        |
| :--- | :--- |:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Frontend** | React, TypeScript, Vite, Tailwind CSS, Framer Motion | Provides a modern, type-safe, and highly interactive user interface with a fast development environment. Framer Motion is used for fluid animations that enhance the user experience.                                                                                                            |
| **Backend** | Python, Flask | Flask is chosen for its lightweight and extensible nature, making it ideal for creating a focused and performant API backend. The backend is structured using professional patterns like Application Factory and Blueprints to promote modularity.                                               |
| **AI Orchestration** | LangChain | LangChain is the canonical choice for building LLM-powered applications. Its `create_sql_agent` constructor provides a highly optimized and secure way to build a SQL agent, leveraging battle-tested prompt engineering to ensure reliability and safety.                                       |
| **Language Model** | Google Gemini | Access to Google's powerful and efficient generative models is handled via the official `langchain-google-genai` package, with `gemini-1.5-flash-latest` providing an excellent balance of speed and capability.                                                                                 |
| **Database** | SQLite (Chinook Sample) | The Chinook database is a well-known sample dataset modeling a digital music store. Its schema is complex enough (11 tables, multiple relationships) to robustly test the agent's reasoning abilities. SQLite is used for its simplicity and portability.                                        |
| **Database Toolkit** | SQLAlchemy | LangChain uses SQLAlchemy as its underlying engine to communicate with SQL databases, ensuring a consistent and powerful interface that is dialect-agnostic.                                                                                                                                     |

### Architectural Vision: The Value of Decoupling

A critical architectural decision was the strict separation of concerns:

1.  **React Frontend (UI Layer):** Solely responsible for presenting the user interface and managing user interactions. It communicates with the backend via a well-defined API contract.
2.  **Flask API (Web Layer):** Manages web-related tasks: receiving HTTP requests, parsing JSON, enforcing the API contract, and sending responses. It is intentionally ignorant of the complexities of the AI agent.
3.  **AgentService (Logic Layer):** Encapsulates all AI-driven logic, including LLM initialization, database connection, and LangChain agent invocation. It knows nothing about web protocols and can be reused in other applications (e.g., a CLI tool or a Slack bot) without modification.

This modularity ensures that changes in one part of the system have minimal impact on others and allows the application to be easily extended and maintained over time.

## Project Structure

The codebase is organized into distinct `backend` and `frontend` directories, each with a logical and scalable structure.

### Backend Structure

The backend follows established Flask best practices, using the Application Factory pattern and Blueprints to promote separation of concerns.

```
backend/
├── app/
│   ├── __init__.py          # Application factory (create_app) with streaming support
│   ├── api/                 # API blueprint module
│   │   ├── __init__.py      # Blueprint definition
│   │   └── routes.py        # API endpoints (including /chat/stream)
│   ├── services/            # Core business logic
│   │   ├── llm_service.py   # Manages Google Gemini LLM
│   │   ├── database_service.py # Manages SQLAlchemy database connection
│   │   ├── agent_service.py      # Traditional LangChain SQL agent logic
│   │   └── streaming_agent_service.py # Real-time streaming agent logic
│   ├── utils/               # Shared utilities
│   │   ├── logger.py        # Centralized logging system
│   │   └── react_loop_utils.py # Shared ReAct processing functions
│   └── config.py            # Configuration management from environment variables
├── data/
│   └── chinook.db           # SQLite database file
├── logs/                    # Directory for log files (info/ and error/)
├── .env.example             # Template for environment variables
├── app.py                   # Main application entry point to start the server
└── requirements.txt         # Python package dependencies
```

### Frontend Structure

The frontend is structured using a feature-based approach within the `components` directory, promoting modularity and reusability.

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat/            # Components for the overall chat experience
│   │   ├── ReActStream/     # Components for visualizing the real-time ReAct stream
│   │   ├── UI/              # Reusable UI elements (Button, Card, etc.)
│   │   └── Layout/          # Application layout (Header, Footer)
│   ├── context/
│   │   └── ChatContext.tsx  # Global state management for the chat
│   ├── hooks/
│   │   └── useChatController.ts # Logic for handling streaming events
│   ├── services/
│   │   ├── api.ts           # API client
│   │   └── types.ts         # TypeScript interfaces for data structures
│   ├── styles/              # Global styles and animations
│   └── App.tsx              # Root React component
├── .env.example
├── package.json
└── vite.config.ts           # Vite configuration with proxy to backend
```

## The Agent's Inner World: The ReAct Loop

The "magic" of the agent lies in the **ReAct (Reasoning and Acting)** loop, a process where the LLM iteratively thinks about a problem, decides on an action, executes it using a tool, and observes the result to inform its next thought. This project's streaming UI makes this entire process transparent to the user.

Consider the question: *"Which country's customers spent the most money?"*

Here is a breakdown of the agent's internal monologue and actions:

1.  **Thought:** The agent analyzes the user's question. It understands it needs to find the country with the highest total spending by customers. To do this, it must first understand the database's structure.
2.  **Action:** It decides to use the `sql_db_list_tables` tool to see all available tables. 
3.  **Observation:** The tool returns a list of table names, including `Customer`, `Invoice`, and `InvoiceLine`.
4.  **Thought:** The agent reasons that these tables are relevant. To construct a correct query, it needs to know their schemas and how they are related.
5.  **Action:** It uses the `sql_db_schema` tool to inspect the columns of the `Customer` and `Invoice` tables.
6.  **Observation:** The tool returns the table schemas, revealing that `Customer` has `CustomerId` and `Country`, and `Invoice` has `CustomerId` and `Total`. The agent now understands it can join these two tables on `CustomerId`.
7.  **Thought:** The agent formulates a plan: it will join the `Customer` and `Invoice` tables, group the results by `Country`, calculate the sum of the `Total` for each country, and order the results in descending order to find the highest value.
8.  **Action:** It uses the `sql_db_query` tool to execute the final, validated SQL query against the database.
9.  **Observation:** The database returns the raw result, for instance: `[('USA', 523.06), ...]`
10. **Thought:** The agent has the final data. It now needs to synthesize this raw result into a human-readable sentence.
11. **Final Answer:** The agent generates the final response: "The country whose customers spent the most is the USA, with a total spending of $523.06."

## Future Enhancements

While the current application is a fully functional and powerful utility, the following enhancements could further improve its capabilities:

  * **Implement Chat History:** Allow the agent to remember the context of the current conversation to answer follow-up questions (e.g., "Of those, which one is from the USA?"). This could be achieved using LangChain's `ChatMessageHistory`.
  * **Production Deployment:** For a production environment, the Flask development server should be replaced with a production-grade WSGI server like Gunicorn. The application can be containerized using Docker and deployed to a cloud service like Google Cloud Run for scalable, serverless execution.
  * **Strengthen Security:** For a multi-user application, security can be hardened by connecting to the database with a dedicated, read-only user to programmatically prevent any possibility of destructive DML statements. Implementing API rate-limiting and more rigorous input sanitization would also be critical.
  * **Enhanced UI/UX:** The frontend could be improved to include features like an "Educational Mode" that explains each step in more detail or a "Debug Mode" for developers that shows the raw tool inputs and outputs.

## Contributing

Contributions are welcome\! Please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---
<div align="center">
  <p>Developed by Fang Zhili</p>
</div>
