from dotenv import load_dotenv
load_dotenv()

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our custom RAG engine
from utils.rag_engine import RAGEngine

app = FastAPI(title="ECU Residence Hall Handbook Chatbot")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Engine
rag_engine = RAGEngine()

class ChatRequest(BaseModel):
    message: str
    model: str = "llama-3.3-70b-versatile"

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    print(f"Received upload request for: {file.filename}")
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_path = f"temp_{file.filename}"
    try:
        # Save file temporarily or stream it
        print(f"Saving temporary file to: {temp_path}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process PDF and insert into Supabase
        print("Starting process_and_index_pdf...")
        await rag_engine.process_and_index_pdf(temp_path, file.filename)
        print("File processed successfully.")
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {"status": "success", "message": f"File {file.filename} processed and indexed successfully."}
    except Exception as e:
        print(f"ERROR during upload: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Use generator for streaming
        return StreamingResponse(
            rag_engine.chat_stream(request.message, request.model),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
