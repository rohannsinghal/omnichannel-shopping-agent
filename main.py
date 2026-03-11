from fastapi import FastAPI

# Initialize the API
app = FastAPI(
    title="Omnichannel Shopping Agent API",
    description="The core backend for our AI orchestrator and retail microservices.",
    version="1.0.0"
)

# Create our very first API Endpoint (The Front Door)
@app.get("/")
def health_check():
    return {
        "status": "online", 
        "message": "Welcome to the Omnichannel Agent Backend! The server is running perfectly."
    }