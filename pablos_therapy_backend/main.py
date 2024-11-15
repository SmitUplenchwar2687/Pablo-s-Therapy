from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import speech_recognition as sr
import openai
from pymongo import MongoClient
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import nest_asyncio
import uvicorn
import os
import io
from pydub import AudioSegment
from fastapi.responses import StreamingResponse
import wave
import asyncio


nest_asyncio.apply()

app = FastAPI()
recognizer = sr.Recognizer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb://localhost:27017") 
db = client["pablos_therapy"]
users_collection = db["Users"]

class TextInput(BaseModel):
    prompt: str
    
class User(BaseModel):
    name: str
    email: str
    age: int

client = openai.OpenAI(api_key='')
elevenlabs_client = ElevenLabs(api_key="")

@app.post("/add_user")
async def add_user(user: User):
    user_dict = user.model_dump()
    result = users_collection.insert_one(user_dict)
    # user_dict["id"] = str(result.inserted_id)
    return {"message": "User added successfully"}


@app.get("/user/{user_id}")
async def get_user(user_id: str):
    try:
        user = users_collection.find_one(
            # {"_id": ObjectId(user_id)}
            {"name": user_id}
            )
        if user:
            user["_id"] = str(user["_id"])
            return user
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def transcribe_audio(audio_data):
    audio = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")  
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    with sr.AudioFile(wav_io) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Sorry, I could not understand the audio."
        except sr.RequestError as e:
            return f"Speech Recognition service error: {e}"


client = openai.OpenAI(api_key='')

async def chat_with_gpt(prompt, language="en"):
    GPT_MODEL = "gpt-3.5-turbo-1106"
    messages = [
        {"role": "system", "content": "You are a multilingual therapy chatbot."},
        {"role": "user", "content": prompt}
    ]
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0.9
        )
        response_dict = response.model_dump()
        return response_dict["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return "There was an error with the GPT response."


async def generate_audio(text):
    try:
        audio = elevenlabs_client.generate(
            text=text,
            voice="George",
            model="eleven_multilingual_v2"
        )
        return b"".join(audio)
        # with open("out.wav", "wb") as fp:
        #     audio_bytes = b"".join(audio)
        #     fp.write(audio_bytes)
    except Exception as e:
        print(f"Error with ElevenLabs API: {e}")

@app.post("/process")
async def process_text(input_data: TextInput):
    user_prompt = input_data.prompt
    response_text = await chat_with_gpt(user_prompt)

    await generate_audio(response_text)

    return {"response": response_text}

@app.get("/stream_audio")
async def stream_audio():
    def iterfile():
        with open('out.wav', 'rb') as f:
            while chunk := f.read(1024):  
                yield chunk
    
    return StreamingResponse(iterfile(), media_type="audio/wav")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                user_text = message["text"]
                response_text = await chat_with_gpt(user_text)
                #await websocket.send_text(response_text)

                
                audio_bytes = await generate_audio(response_text)
                if audio_bytes:
                    await websocket.send_bytes(audio_bytes)
            
            elif "bytes" in message:
                audio_data = message["bytes"]
                transcribed_text = await transcribe_audio(audio_data)
                #await websocket.send_text(f"You said: {transcribed_text}")

                response_text = await chat_with_gpt(transcribed_text)
                #await websocket.send_text(response_text)

                audio_bytes = await generate_audio(response_text)
                if audio_bytes:
                    await websocket.send_bytes(audio_bytes)
    except WebSocketDisconnect:
        print("WebSocket disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
