from aiohttp import web
import socketio
import uuid

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

sids = []
rooms = {}

def find_interlocutor(sid):
    for room in rooms.values():
        if room.get('sender') == sid:
            return room.get('receiver')
        if room.get('receiver') == sid:
            return room.get('sender')

async def index(request):
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')

@sio.event
async def connect(sid, environ):
    sids.append(sid)
    print("connect", sid)
    await sio.emit("init")
    
@sio.on("sdp_offer")
async def sendOffer(sid, offer):
    interlocutor = find_interlocutor(sid)
    if interlocutor:
        await sio.emit("sdp_offer", offer, room=interlocutor)

@sio.on("sdp_answer")
async def sendAnswer(sid, answer):
    interlocutor = find_interlocutor(sid)
    if interlocutor:
        await sio.emit("sdp_answer", answer, room=interlocutor)

@sio.on("ice")
async def sendIce(sid, ice):
    interlocutor = find_interlocutor(sid)
    if interlocutor:
        print("the sid is:", sid, "the ice sent is:", ice)
        await sio.emit("ice", ice, room=interlocutor)

@sio.on("offer_got")
async def gotOffer(sid):
    interlocutor = find_interlocutor(sid)
    if interlocutor:
        await sio.emit("offer_got", room=interlocutor)

@sio.on("answer_got")
async def iceSend(sid):
    interlocutor = find_interlocutor(sid)
    if interlocutor:
        await sio.emit("answer_got", room=interlocutor)


@sio.on("init")
async def init(sid, data):
    print("data = ", data)
    if not data.get('roomNum'):
        print(1)
        roomCode = str(uuid.uuid4())
        
        rooms[roomCode] = {
            "sender": sid,
            "receiver": None
        }

        await sio.emit('init_ok', {'roomNum': roomCode}, room=sid)
    else:
        for roomId, room in rooms.items():
            if roomId == data['roomNum'] and not room.get('receiver'):
                await sio.emit('init_ok', room=sid)
                await sio.emit('partner_connected', room=room['sender'])

                room['receiver'] = sid
                break
        else:
            await sio.emit('init_error', room=sid)
    print("rooms right now: ", rooms)

@sio.on("file_info")
async def fileInfo(sid, info):
    name = info[0]
    size = info[1]
    interlocutor = find_interlocutor(sid)
    if interlocutor:
        await sio.emit("file_info", [name, size], room=interlocutor)


@sio.event
async def disconnect(sid):
    for roomId, room in rooms.items():
        if room.get('sender') == sid:
            if room.get('receiver'):
                await sio.emit('sender_disconnected', room=room['receiver'])
            del rooms[roomId]

        if room.get('receiver') == sid:
            if room.get('sender'):
                await sio.emit('receiver_disconnected', room=room['sender'])
            room['receiver'] = None

app.router.add_get('/{code}', index)
app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8000)