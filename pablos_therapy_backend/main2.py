from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import speech_recognition as sr
import openai
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
from pymongo import MongoClient
import json
from datetime import datetime, timezone
import base64
from io import BytesIO

nest_asyncio.apply()

app = FastAPI()
recognizer = sr.Recognizer()
client = MongoClient("mongodb://localhost:27017/")

db = client["pablos_therapy"]
users_collection = db["users"]
sessions_collection = db["sessions"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific origins in production, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the input data model
class TextInput(BaseModel):
    prompt: str

# Initialize OpenAI and ElevenLabs clients
client = openai.OpenAI(api_key='')
elevenlabs_client = ElevenLabs(api_key="")

# async def voice_to_text(audio_file=None):
#     if audio_file is None:
#         with sr.Microphone() as source:
#             print("Listening...")
#             audio = recognizer.listen(source)
#     else:
#         with sr.AudioFile(audio_file) as source:
#             audio = recognizer.record(source)
#     try:
#         print("Recognizing...")
#         text = recognizer.recognize_google(audio)
#         print(f"Text: {text}")
#         return text
#     except sr.UnknownValueError:
#         print("Google Speech Recognition could not understand audio")
#     except sr.RequestError as e:
#         print(f"Could not request results from Google Speech Recognition service; {e}")

def find_or_create_user(username, email, user_id):
    user = users_collection.find_one({"email": email, "user_id": user_id})
    if not user:
        user_id = users_collection.insert_one({
            "username": username,
            "email": email,
            "sessions": [],
            "user_id": user_id,
        }).inserted_id
    return user_id


async def transcribe_audio(audio_data):
    # Convert audio to WAV format (assuming input is webm or ogg)
    audio = AudioSegment.from_file(audio_data, format="webm")  # or "ogg" if that's the format
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    # Use the converted WAV data with speech_recognition
    with sr.AudioFile(wav_io) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Sorry, I could not understand the audio."
        except sr.RequestError as e:
            return f"Speech Recognition service error: {e}"


# async def transcribe_audio(audio_data):
#     with sr.AudioFile(io.BytesIO(audio_data)) as source:
#         audio = recognizer.record(source)
#         try:
#             text = recognizer.recognize_google(audio)
#             return text
#         except sr.UnknownValueError:
#             return "Sorry, I could not understand the audio."
#         except sr.RequestError as e:
#             return f"Speech Recognition service error: {e}"

client = openai.OpenAI(api_key='')


async def chat_with_gpt(prompt, context, language="en"):
    if isinstance(context, list):
        peng = """You are a healthcare information assistant focused on providing health education and information. Follow these guidelines:

BEHAVIOR:
- Provide direct, clear responses to health questions
- Skip self-introductions or role statements
- Only mention being a healthcare assistant if specifically asked
- Start responses with relevant information immediately

SCOPE OF EXPERTISE:
- Respond to questions related to healthcare, medical information, therapy, wellness, and general health topics
- Maintain professional and respectful communication
- You are expert in giving quick first aid or very effective remedies
- Decline to engage with inappropriate content, including:
  * Explicit sexual content
  * Harmful or unethical practices
  * Religious or spiritual healing claims
  * Hate speech or discriminatory content

AVOID:
- Starting responses with "I am a healthcare assistant"
- Dont introduce yourself everytime response
- Repeating disclaimers unnecessarily
- Overly formal or robotic language
- Excessive introductions or explanations
- numbering the list and providing answers with index number before sentences

CORE PRINCIPLES:
- Provide evidence-based health information
- Respect medical ethics and professional boundaries
- Maintain clear, professional communication

RESPONSE STRUCTURE:
1. For health-related questions:
   - Provide clear, factual information
   - Include relevant context when needed
   - Add brief disclaimer for medical topics
   - Suggest professional consultation when appropriate

2. For out-of-scope or inappropriate content:
   - Politely decline to engage
   - Redirect to appropriate health-related discussion
   - Maintain professional tone


Example natural responses:

User: "What helps with a headache?"
Assistant: "Common headache remedies include: 
- Over-the-counter pain relievers
- Staying hydrated
- Getting adequate rest
- Reducing screen time
- Managing stress

For frequent or severe headaches, consult a healthcare provider."

User: "Why is the sky blue?"
Assistant: "I focus on health-related topics. Feel free to ask me any questions about health, wellness, or medical information."

User: "How can I sleep better?"
Assistant: "Try these evidence-based sleep tips:
- Stick to a consistent sleep schedule
- Keep your bedroom cool and dark
- Avoid screens before bedtime
- Limit caffeine after noon
- Exercise regularly, but not close to bedtime"

Example response to inappropriate content:
Human: [inappropriate or out-of-scope question]
Assistant: "I maintain a focus on providing health-related information in a professional manner. I'd be happy to discuss any health-related questions you may have."""

    context = " ".join(str(item) for item in context)
    GPT_MODEL = "gpt-3.5-turbo-1106"
    messages=[
            {"role": "system", "content": "I'm a multilingual therapy bot. be kind"},
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=0.9
        )
        response_dict = response.model_dump()
        return response_dict["choices"][0]["message"]["content"]
    except Exception as e:
            print(f"Error with OpenAI API: {e}")
            return "There was an error with the GPT response."

# async def chat_with_gpt(prompt, language="en"):
#     GPT_MODEL = "gpt-3.5-turbo-1106"
#     messages = [
#         {"role": "system", "content": "You are a multilingual therapy chatbot."},
#         {"role": "user", "content": prompt}
#     ]
#     try:
#         response = client.chat.completions.create(
#             model=GPT_MODEL,
#             messages=messages,
#             max_tokens=150,
#             temperature=0.9
#         )
#         response_dict = response.model_dump()
#         return response_dict["choices"][0]["message"]["content"]
#     except Exception as e:
#         print(f"Error with OpenAI API: {e}")
#         return "There was an error with the GPT response."


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

def start_session(session_id, user_id, description):
    created_at = datetime.now(timezone.utc).isoformat()
    sessions_collection.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "created_at": created_at,
        "messages": [],
        "description": description
    })
    push_to_session(session_id, user_id)
    return session_id

def push_to_session(session_id, user_id):
    result = users_collection.update_one( {"user_id": user_id},
        {"$push": {"sessions": session_id}}
    )
    return result.modified_count > 0

def session_exists(user_id, session_id):
    return sessions_collection.find_one(
        {"user_id": user_id, "session_id": session_id}
    ) is not None

def get_session_history(user_id, session_id):
    session = sessions_collection.find_one({"session_id": session_id, "user_id": user_id})
    if session:
        return session["messages"]
    return []

def get_last_but_one_session_messages(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if user and len(user['sessions']) >= 1:
        session_ids = user['sessions']
        if len(session_ids)== 1 :
            last_but_one_session_id = session_ids[-1]
        else: 
            last_but_one_session_id = session_ids[-2]
        session = sessions_collection.find_one({"session_id": last_but_one_session_id, "user_id": user_id})
        if session:
            messages = session.get('messages', [])
            last_five_messages = messages[-5:]  
            print(last_five_messages)
            message_list = [f"User: {msg['userQuestion']}\nAssistant: {msg['response']}" for msg in last_five_messages]
            return message_list
    return None

def add_message_to_session(session_id, question, response, user_id):
    timestamp = datetime.now(timezone.utc).isoformat()
    sessions_collection.update_one(
        {"session_id": session_id, "user_id": user_id},
        {"$push": {"messages": {
            "userQuestion": question,
            "response": response,
            "timestamp": timestamp
        }}}
    )

def decode_base64_audio(base64_data):
    audio_data = base64.b64decode(base64_data)
    return BytesIO(audio_data)


# WebSocket endpoint for chat
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # session = "sdfjd" # this will come from db
        # if not session:
        #     response_text = "Hey Yash, welcome to Pablos. How are you doing?"
        #     audio_bytes = await generate_audio(response_text)
        #     if audio_bytes:
        #         await websocket.send_bytes(audio_bytes)
        # else:
        #     response_text = "Welcome back Yash. how have you been?"
        #     audio_bytes = await generate_audio(response_text)
        #     if audio_bytes:
        #         await websocket.send_bytes(audio_bytes)

        while True:
            message = await websocket.receive()
            data = json.loads(message["text"])

            audio_data = data.get('recorded_audio')
            email = data.get('email')
            user_id = data.get('user_id')
            find_or_create_user('sachin', email, user_id)
            session_id = data.get('session_id')

            if not session_exists(user_id, session_id):
                start_session(session_id, user_id, "")
            
            # Check if the received message is text or binary
            # if "text" in message:
            #     user_text = message["text"]
            #     response_text = await chat_with_gpt(user_text)
            #     audio_bytes = await generate_audio(response_text)
            #     if audio_bytes:
            #         await websocket.send_bytes(audio_bytes)
            #
            # elif "bytes" in message:
            if isinstance(audio_data, str):  
                audio_bytes = decode_base64_audio(audio_data)

            transcribed_text = await transcribe_audio(audio_bytes)
            userQuestion = transcribed_text
            context = get_session_history(user_id, session_id)
            prevContext = get_last_but_one_session_messages(user_id)
            context.append(prevContext)
            print(context)
            response_text = await chat_with_gpt(transcribed_text, context)
            add_message_to_session(session_id, userQuestion, response_text, user_id)
            audio_bytes = await generate_audio(response_text)
            if audio_bytes:
                await websocket.send_bytes(audio_bytes)
    except WebSocketDisconnect:
        print("WebSocket disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
