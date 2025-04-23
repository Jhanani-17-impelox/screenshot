# socket_module.py

import asyncio
import socketio
import time
sio = socketio.AsyncClient()
is_connected = False
_gemini_response_future = None
_gemini_response_data = None
ping_interval = 5

@sio.event
async def connect():
    global is_connected
    print('connection established')
    is_connected = True

@sio.event
async def my_message(data):
    print('message received with ', data)
    await sio.emit('my response', {'response': 'my response from module'})

@sio.event
async def disconnect():
    global is_connected
    print('disconnected from server')
    is_connected = False

@sio.on('gemini_response')
async def on_response(data):
    global _gemini_response_future, _gemini_response_data
    print('Received gemini_response:', data)
    _gemini_response_data = data
    if _gemini_response_future and not _gemini_response_future.done():
        _gemini_response_future.set_result(data)

async def connect_handler():
    global is_connected
    print('Connection established')
    is_connected = True
    asyncio.create_task(start_periodic_ping())

async def disconnect_handler():
    global is_connected
    print('Disconnected from server')
    is_connected = False

async def connect_to_server(url):
    """Connect to the Socket.IO server."""
    global is_connected
    sio.on('connect', connect_handler)
    sio.on('disconnect', disconnect_handler)
    sio.on('ping', ping_handler)
    sio.on('pong', pong_handler)
    try:
        await sio.connect(url)
        is_connected = True
    except socketio.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def wait_for_connection():
    """Wait until the connection is established."""
    while not is_connected:
        await asyncio.sleep(0.1)

async def disconnect_from_server():
    """Disconnect from the Socket.IO server."""
    global is_connected
    if is_connected:
        await sio.disconnect()
        is_connected = False
    else:
        print("Not connected.")

async def send_message(data):
    """Send a message to the server."""
    if is_connected:
        print("Sending message to server:", data)
        await sio.emit("geminiRequest", data)
    else:
        print("Not connected. Cannot send message.")

async def receive_gemini_response(timeout=None):
    """Asynchronously wait for a 'gemini_response' from the server."""
    global _gemini_response_future, _gemini_response_data
    _gemini_response_future = asyncio.Future()
    try:
        return await asyncio.wait_for(_gemini_response_future, timeout=timeout)
    except asyncio.TimeoutError:
        print("Timeout waiting for gemini_response.")
        return None
    finally:
        _gemini_response_future = None
        _gemini_response_data = None

async def ping_handler(data):
    print(f"Received ping from server: {data}")
    await send_pong("Pong from client")

async def pong_handler(data):
    print(f"Received pong from server: {data}")
async def send_ping():
    if is_connected:
        print("Sending ping to server...")
        await sio.emit('ping', 'Ping from client')
    else:
        print("Not connected. Cannot send ping.")

async def send_pong(message):
    if is_connected:
        await sio.emit('pong', message)
        print(f"Sent pong to server: {message}")
    else:
       print("Not connected. Cannot send pong.")
async def start_periodic_ping():
    """Periodically send a ping message to the server."""
    while True:
        await send_ping()
        time.sleep(ping_interval)
    # You might want to track latency or other metrics here

# You might choose NOT to have this run automatically upon import
# if __name__ == '__main__':
#     asyncio.run(connect_to_server('http://localhost:5000'))
#     await sio.wait()