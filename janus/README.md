# Janus Backend

The core intelligence of Janus, built with Python and FastAPI.

> **Note**: For the main project documentation, architecture, and roadmap, please refer to the [Root README](../README.md).

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt`

## Local Setup

1.  **Navigate to the backend directory**:
    ```bash
    cd janus
    ```

2.  **Create and activate a virtual environment (optional but recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    > *Note: If you encounter issues with `ag-ui-protocol`, remove it from requirements.txt temporarily.*

4.  **Configuration**:
    Ensure your `.env` file is set up with the necessary database and API keys.

5.  **Run the Server**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## Testing

To run tests, execute from the repository root:
```bash
PYTHONPATH=janus pytest tests/
```
