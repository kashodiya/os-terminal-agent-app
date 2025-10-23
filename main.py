from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import json
import asyncio
from cli_agent import CLIAgent

app = FastAPI()
cli_agent = CLIAgent(safe_mode=True)

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            await call_agent(user_message, websocket)
            await websocket.send_text(json.dumps({"type": "complete"}))
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({"type": "chunk", "content": f"Error: {str(e)}"}))
        await websocket.send_text(json.dumps({"type": "complete"}))
    finally:
        await websocket.close()

async def call_agent(user_message: str, websocket):
    try:
        await websocket.send_text(json.dumps({"type": "chunk", "content": "🤔 Processing your request..."}))
        
        # Use the strands-based CLI agent
        result = await asyncio.to_thread(cli_agent.answer_question, user_message)
        
        if result['success']:
            await websocket.send_text(json.dumps({"type": "chunk", "content": f"\n💡 Command: {result['command_used']}"}))
            await websocket.send_text(json.dumps({"type": "chunk", "content": f"\n📝 Answer: {result['answer']}"}))
        else:
            await websocket.send_text(json.dumps({"type": "chunk", "content": f"\n❌ {result['answer']}"}))
            
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "chunk", "content": f"Error: {str(e)}"}))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)