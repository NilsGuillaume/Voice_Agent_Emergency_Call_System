import asyncio
import base64
import json
import websockets
import os
from dotenv import load_dotenv

from db import new_call_sql
from db import get_emergency_description

from agent_functions import location_verifier
from agent_functions import note_emergency_description

from triage_system import main_call_update_esi
import os
import logging

import logging


load_dotenv()
DEEPGRAM_API = os.getenv("DEEPGRAM_API_KEY")

def sts_connect():
    #api_key = os.getenv("DEEPGRAM_API_KEY")
    api_key = DEEPGRAM_API
    if not api_key:
        raise Exception("DEEPGRAM API NOT FOUND")
    
    sts_ws = websockets.connect(
        "wss://agent.deepgram.com/v1/agent/converse",
        subprotocols=["token",api_key]
    )
    return sts_ws


def load_config():
    with open("config.json","r") as f:
        return json.load(f)
    
    
async def handle_barge_in(decoded, twilio_ws, streamsid):
    if decoded["type"] == "UserStartedSpeaking":
        clear_message = {
            "event": "clear",
            "streamSid": streamsid
        }
        
        await twilio_ws.send(json.dumps(clear_message))
   
    
async def eval_queue_manager(evaluation_queue):
    while True:
        streamsid = await evaluation_queue.get()
    
        try: 
            full_description = await asyncio.to_thread(
                get_emergency_description,
                streamsid
            )
            
            if full_description:
                await asyncio.to_thread(
                    main_call_update_esi,
                    streamsid,
                    full_description
                )
            
        except Exception as e:
            print(f"Eval. Queue Manager Error: {e}", flush = True)
            
        finally:
            evaluation_queue.task_done()

   
async def execute_function_call(func_name, arguments, streamsid, evaluation_queue):
    
    function_map = {
                "location_verifier": lambda address: location_verifier(streamsid, address),
                "note_emergency_description": lambda emergency_description: note_emergency_description(streamsid, emergency_description)
            }

    
    
    if func_name in function_map:
        
        result = await asyncio.to_thread(function_map[func_name], **arguments)        
        
        if func_name == 'note_emergency_description':
            evaluation_queue.put_nowait(streamsid)
        print(f"Function Call results {result}", flush = True)
        return result
    
    else: 
        result = {"error": f"Unkown function {func_name}"}
        return result
         
        
async def handle_function_call_request(decoded,sts_ws,streamsid, evaluation_queue):
    try:
        for function_call in decoded['functions']:
            func_name = function_call['name']
            func_id = function_call['id']
            arguments = json.loads(function_call['arguments'])
            
            print(f"function_call: {func_name}, ID: {func_id}", flush = True)
            
            result = await execute_function_call(func_name, arguments, streamsid, evaluation_queue)

            function_result = {
                "type": "FunctionCallResponse",
                "id": func_id,
                "name": func_name,
                "content": json.dumps(result)
            }
            
            await sts_ws.send(json.dumps(function_result))  
            print(f"Function call results has been sent to Deepgram. Result {function_result}", flush = True)           
                                             
    except Exception as e:
        print(f"Error function call: {e}", flush = True)  
        func_id_e = func_id if "func_id" in locals() else "unknown"
        func_name_e = func_name if "func_id" in locals() else "unknown"
        error = f"Function call failed with {str(e)}"
        
        error_result = {
            "type": "FunctionCallResponse",
            "id": func_id_e,
            "name": func_name_e,
            "content": json.dumps(error)
            
        } 
        
        await sts_ws.send(json.dumps(error_result))
        print(f"Function call error results has been sent to Deepgram. Result {error_result}", flush = True)           
    

async def handle_text_message(decoded, twilio_ws, sts_ws,streamsid, evaluation_queue):
    await handle_barge_in(decoded, twilio_ws, streamsid)
    
    if decoded['type'] == "FunctionCallRequest":
        await handle_function_call_request(decoded,sts_ws, streamsid, evaluation_queue)


async def sts_sender(sts_ws, audio_queue):
    print("sts_sender started", flush = True)
    while True:
        chunk = await audio_queue.get()
        await sts_ws.send(chunk)


async def sts_receiver(sts_ws, twilio_ws, streamsid_queue, evaluation_queue, caller_number_queue):
    print("sts_receiver started", flush = True)
    streamsid = await streamsid_queue.get()
    caller_number = await caller_number_queue.get()
    
    new_call_sql(streamsid, caller_number)
    
    async for message in sts_ws:
        if type(message) is str:
            print(message, flush = True)
            decoded = json.loads(message)
            await handle_text_message(decoded, twilio_ws, sts_ws, streamsid, evaluation_queue)
            continue
        
        raw_mulaw = message
        
        media_message = {
            "event":"media",
            "streamSid": streamsid,
            "media": {"payload": base64.b64encode(raw_mulaw).decode("ascii")}
        }
        
        await twilio_ws.send(json.dumps(media_message))
    

async def twilio_receiver(twilio_ws, audio_queue, streamsid_queue, caller_number_queue):
    BUFFER_SIZE = 20 * 160
    inbuffer = bytearray(b"")
    
    async for message in twilio_ws:
        try:
            data = json.loads(message)
            event = data['event']
            
            if event == "start":
                print("get our streamsid", flush = True)
                start = data['start']
                streamsid = start['streamSid']
                streamsid_queue.put_nowait(streamsid)
                caller_number = data["start"]["customParameters"]["From"]
                caller_number_queue.put_nowait(caller_number)

            elif event == "connected":
                continue
            elif event == "media":
                media = data['media']
                chunk = base64.b64decode(media['payload'])
                if media["track"] == "inbound":
                    inbuffer.extend(chunk)
            elif event == "stop":
                break
            
            while len(inbuffer) >= BUFFER_SIZE:
                chunk = inbuffer[:BUFFER_SIZE]
                audio_queue.put_nowait(chunk)
                inbuffer = inbuffer[BUFFER_SIZE:]
                
        except:
            break
        
        
async def twilio_handler(twilio_ws):
    audio_queue = asyncio.Queue()
    streamsid_queue = asyncio.Queue()
    evaluation_queue = asyncio.Queue()
    caller_number_queue = asyncio.Queue()
    
    eval_queue_manager_task = asyncio.create_task(eval_queue_manager(evaluation_queue))
    
    async with sts_connect() as sts_ws:
        config_message = load_config()
        await sts_ws.send(json.dumps(config_message))
        
        try:
            await asyncio.wait(
                [
                    asyncio.ensure_future(sts_sender(sts_ws, audio_queue)),
                    asyncio.ensure_future(sts_receiver(sts_ws, twilio_ws, streamsid_queue, evaluation_queue, caller_number_queue)),
                    asyncio.ensure_future(twilio_receiver(twilio_ws,audio_queue,streamsid_queue, caller_number_queue))
                ]  
            )
            
        finally:
            eval_queue_manager_task.cancel()
            await twilio_ws.close()



async def main():
    port = int(os.getenv("PORT","100000"))
    await websockets.serve(
        twilio_handler,
        host="0.0.0.0",
        port=port,
    )
    print(f"Started Server on 0.0.0.0: {port}", flush = True)
    await asyncio.Future()
    
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # websockets 14.0+? logs an error if a connection is opened and closed
    # before data is sent. e.g. when platforms send HEAD requests.
    # Suppress these warnings.
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)
    asyncio.run(main())
