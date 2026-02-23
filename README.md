# Contemplative AI
Buddhist's texts based AI solution for everyone

## Quick Start

This project includes both Python backend and React frontend components. See [SETUP.md](SETUP.md) for detailed installation instructions.

### Prerequisites
- Python 3.8+
- Node.js and npm (for React frontend)

### Audio Player
- Simple HTML version: Open `web-ui/index.html` in your browser
- React version: Coming soon (see SETUP.md for instructions)

### Qdrant
- tu run qdrant, execute this command in terminal while placed in the pc root folder(this has to me moved to the project folder):

docker run -p 6333:6333 -p 6334:6334   -v "$(pwd)/qdrant_storage:/qdrant/storage:z"   qdrant/qdrant

### uvicorn

- tu run uvicorn, execute this command in terminal while placed in the Backend folder:

uvicorn api_generate_meditation:app --reload

### ollama
to run ollama, execute this command in terminal(not sure if this is needed):

ollama run llama3.1


### Frontend
- tu run frontend, execute this command in terminal while placed in the web-ui folder:

npm start

After all those are running, you can access the application at http://localhost:3000
