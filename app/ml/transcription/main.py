import sys
import time
import re
import uuid
from io import BytesIO

sys.path.insert(0, "/app")

import modal
from fastapi import FastAPI, UploadFile, File
from config import config, image, logger
from faster_whisper_agent import FasterWhisperAgent

app = modal.App(config['app_name'])

########################################################
# Faster Whisper Agent
########################################################
@app.cls(
    image=image,
    cpu=config['whisper']['cpu'],
    memory=config['whisper']['memory'],
    max_containers=config['whisper']['max_containers'],
    min_containers=config['whisper']['min_containers'],
    scaledown_window=config['whisper']['scaledown_window'],
    timeout=config['whisper']['timeout'],  
)
@modal.concurrent(max_inputs=config['whisper']['concurrency'])
class TranscriptionAgent:
    @modal.enter()
    def setup(self):
        self.agent = FasterWhisperAgent(config['whisper']['model'])
        self.agent.startup()

    @modal.method()
    def transcribe_chunk(self, audio_file):
        return self.agent.transcribe_chunk(audio_file)

########################################################
# FastAPI app
########################################################
web_app = FastAPI(title=config['app_name'])

@web_app.post('/run')
async def transcribe(file: UploadFile = File(...)):
    start_time = time.time()
    request_id = str(uuid.uuid4())

    logger.info(f"[{request_id}] Received file: {file.filename} ({file.content_type})")

    # Step 1: Read file bytes and wrap in BytesIO
    audio_bytes = await file.read()
    audio_file = BytesIO(audio_bytes)
    logger.info(f"[{request_id}] File read into memory and wrapped in BytesIO")

    # TODO: Instead of passing entire audio file. Chunk audio file for faster processing.

    # Step 2: Instantiate Faster Whisper Agent
    whisper_agent = TranscriptionAgent()
    logger.info(f"[{request_id}] Initialized TranscriptionAgent")

    # Step 3: Transcribe audio chunks asynchronously
    task_results = []
    async for result in whisper_agent.transcribe_chunk.starmap([(audio_file, )]):
        task_results.append(result)
    logger.info(f"[{request_id}] Completed transcription of {len(task_results)} chunks")

    # Step 4: Combine transcriptions
    transcriptions = []
    for result in task_results:
        transcription = result.strip()  # result is a string
        if transcription:
            transcriptions.append(transcription)

    full_transcription = " ".join(transcriptions)
    full_transcription = re.sub(r'\s+', ' ', full_transcription).strip()
    logger.info(f"[{request_id}] Combined transcription length: {len(full_transcription)} characters")

    # Step 5: Compute e2e latency
    e2e_latency = time.time() - start_time
    logger.info(f"[{request_id}] End-to-end latency: {e2e_latency:.2f} seconds")

    return {
        "request_id": request_id,
        "transcription": full_transcription,
        "e2e_latency_seconds": e2e_latency
    }

########################################################
# FastAPI Worker
########################################################
@app.function(
    image=image,
    cpu=config['api']['cpu'],
    memory=config['api']['memory'],
    max_containers=config['api']['max_containers'],
    min_containers=config['api']['min_containers'],
    scaledown_window=config['api']['scaledown_window'],
    timeout=config['api']['timeout'], 
)
@modal.concurrent(max_inputs=config['api']['concurrency'])
@modal.asgi_app()
def API():
    return web_app
