import os, json, base64, asyncio, websockets, audioop
from typing import Callable, Any

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from call_logic.models.transcripts import Transcript

_call_sid_to_phone: dict[str, str] = {}

LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created', 'response.text.start',     # ← ensure we catch text events *******************
    'response.text.partial',
    'response.text.end',
    'input.text.start',
    'input.text.partial',
    'input.text.end' # **********************************
]
SHOW_TIMING_MATH = False

def create_call_router(
        get_system_message,
        get_system_greeting,
        voice,
        on_call_complete: Callable[[Transcript], Any],
):

    router = APIRouter()

    @router.api_route("/incoming-call", methods=["GET", "POST"])
    async def handle_incoming_call(request: Request):
        form = await request.form()
        caller_number = form.get("From")
        call_sid = form.get("CallSid")
        if call_sid and caller_number:
            _call_sid_to_phone[call_sid] = caller_number
        response = VoiceResponse()
        response.pause(length=1)
        host = request.url.hostname
        connect = Connect()
        connect.stream(url=f'wss://{host}/media-stream')
        response.append(connect)
        return HTMLResponse(content=str(response), media_type="application/xml")

    @router.websocket("/media-stream")
    async def handle_media_stream(websocket: WebSocket):
        transcript = Transcript(phone_number="", call_text="")
        """Handle WebSocket connections between Twilio and OpenAI."""
        print("Client connected")
        await websocket.accept()

        async with (websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03',
            extra_headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws):
            await initialize_session(openai_ws)

            # Connection specific state
            stream_sid = None
            latest_media_timestamp = 0
            last_assistant_item = None
            mark_queue = []
            response_start_timestamp_twilio = None

            async def receive_from_twilio():
                """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
                nonlocal stream_sid, latest_media_timestamp
                try:
                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        if data['event'] == 'media' and openai_ws.open:
                            latest_media_timestamp = int(data['media']['timestamp'])
                            ulaw_bytes = base64.b64decode(data["media"]["payload"])
                            pcm16_8k = audioop.ulaw2lin(ulaw_bytes, 2)
                            pcm16_16k, _ = audioop.ratecv(
                                pcm16_8k,
                                2,  # width=2 bytes per sample
                                1,  # mono
                                8000,  # source sample rate
                                16000,  # target sample rate
                                None  # no prior state
                            )
                            pcm16_b64 = base64.b64encode(pcm16_16k).decode("utf-8")
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": pcm16_b64
                            }
                            await openai_ws.send(json.dumps(audio_append))
                        elif data['event'] == 'start':
                            stream_sid = data['start']['streamSid']
                            call_sid = data['start']['callSid']
                            print(_call_sid_to_phone[call_sid])
                            transcript.phone_number = _call_sid_to_phone[call_sid]
                            print(f"Incoming stream has started {stream_sid}")
                            nonlocal response_start_timestamp_twilio, last_assistant_item
                            response_start_timestamp_twilio = None
                            latest_media_timestamp = 0
                            last_assistant_item = None
                        elif data['event'] == 'mark':
                            if mark_queue:
                                mark_queue.pop(0)
                        elif data['event'] == 'stop':
                            print(f"sending to middleware: {transcript}")
                            await on_call_complete(transcript)
                except WebSocketDisconnect:
                    print("Client disconnected.")
                    await on_call_complete(transcript)
                    if openai_ws.open:
                        await openai_ws.close()

            async def send_to_twilio():
                """Receive OpenAI events, write one-shot user transcripts, and send incremental assistant audio back."""
                nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio, transcript
                try:
                    async for openai_message in openai_ws:
                        response = json.loads(openai_message)

                        # ─── ONE-SHOT USER “WHISPER” ─────────────────────────────────
                        if response.get("type") == "conversation.item.input_audio_transcription.completed":
                            transcript.call_text += f"User: {response.get('transcript')}"
                            print(transcript.call_text)

                        elif response.get("type") == "response.audio_transcript.done":
                            # End‐of-assistant turn: newline
                            transcript.call_text += f"Assistant: {response.get('transcript')}\n"
                            print(transcript.call_text)

                        # ─── ASSISTANT AUDIO ⇒ TWILIO (G711 u-law chunks) ──────────────
                        if response.get("type") == "response.audio.delta" and "delta" in response:
                            audio_payload = base64.b64encode(
                                base64.b64decode(response["delta"])
                            ).decode("utf-8")

                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": audio_payload}
                            }
                            await websocket.send_json(audio_delta)

                            if response_start_timestamp_twilio is None:
                                response_start_timestamp_twilio = latest_media_timestamp
                            if response.get("item_id"):
                                last_assistant_item = response["item_id"]

                            await send_mark(websocket, stream_sid)

                        # ─── INTERRUPTION (server-VAD) LOGIC ──────────────────────────
                        if response.get('type') == 'input_audio_buffer.speech_started':
                            if last_assistant_item:
                                await handle_speech_started_event()

                except Exception as e:
                    print(f"Error in send_to_twilio: {e}")

            async def handle_speech_started_event():
                """Handle interruption when the caller's speech starts."""
                nonlocal response_start_timestamp_twilio, last_assistant_item
                if mark_queue and response_start_timestamp_twilio is not None:
                    elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                    if SHOW_TIMING_MATH:
                        print(f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp_twilio} = {elapsed_time}ms")

                    if last_assistant_item:
                        if SHOW_TIMING_MATH:
                            print(f"Truncating item with ID: {last_assistant_item}, Truncated at: {elapsed_time}ms")

                        truncate_event = {
                            "type": "conversation.item.truncate",
                            "item_id": last_assistant_item,
                            "content_index": 0,
                            "audio_end_ms": elapsed_time
                        }
                        await openai_ws.send(json.dumps(truncate_event))

                    await websocket.send_json({
                        "event": "clear",
                        "streamSid": stream_sid
                    })

                    mark_queue.clear()
                    last_assistant_item = None
                    response_start_timestamp_twilio = None

            async def send_mark(connection, stream_sid):
                if stream_sid:
                    mark_event = {
                        "event": "mark",
                        "streamSid": stream_sid,
                        "mark": {"name": "responsePart"}
                    }
                    await connection.send_json(mark_event)
                    mark_queue.append('responsePart')

            await asyncio.gather(receive_from_twilio(), send_to_twilio())

    async def send_initial_conversation_item(openai_ws):
        """Send initial conversation item if AI talks first."""
        initial_conversation_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Greet the user with '{get_system_greeting()}'"
                    }
                ]
            }
        }
        await openai_ws.send(json.dumps(initial_conversation_item))
        await openai_ws.send(json.dumps({"type": "response.create"}))

    async def initialize_session(openai_ws):
        """Control initial session with OpenAI."""
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad", "threshold": 0.7},
                "input_audio_format": "pcm16",
                "output_audio_format": "g711_ulaw",
                "voice": voice,
                "instructions": get_system_message(),
                "modalities": ["text", "audio"],
                "input_audio_transcription":  {"model": "whisper-1"},
                "temperature": 0.8,
            }
        }
        print('Sending session update:', json.dumps(session_update))
        await openai_ws.send(json.dumps(session_update))

        # Uncomment the next line to have the AI speak first
        await send_initial_conversation_item(openai_ws)

    return router