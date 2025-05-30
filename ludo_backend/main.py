import os
import uuid
from fastapi import FastAPI, HTTPException, Body, Path, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Set
import datetime
import json
import httpx 
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware # <--- BUNI QO'SHING

# --- Yangi importlar ---
from .game_logic import LudoGame, LudoPlayer, PieceColor # game_logic.py dan import

# --- Pydantic Modellar (avvalgi kabi, lekin LudoGame bilan sinxronlash uchun ba'zi o'zgarishlar bo'lishi mumkin) ---
# Hozircha Pydantic GameBase ni saqlab qolamiz, u API javoblari uchun ishlatiladi.
# LudoGame esa o'yinning ichki logikasini boshqaradi.


BOT_TOKEN = "8033028557:AAHWfw4fv9_8DJ5I0tJRqoV0FHjTWeywX5o"
MINI_APP_BASE_URL = "https://t.me/ludo_demo_bot/ludo/"

class BotNewGameRequest(BaseModel):
    chat_id: int
    host_user_id: int
    host_first_name: str
    # host_username: Optional[str] = None # Agar kerak bo'lsa

class BotNewGameResponse(BaseModel):
    game_id: str
    chat_id: int # Botga qaytarish uchun qulaylik
    host_id: int # Botga qaytarish uchun qulaylik

class BotSetMessageIdRequest(BaseModel):
    game_id: str
    message_id: int

class PlayerBase(BaseModel):
    user_id: int
    first_name: str
    username: Optional[str] = None

class PlayerCreate(PlayerBase):
    pass

class PlayerInGameAPI(PlayerBase): # API uchun Pydantic model
    is_host: bool = False
    is_active: bool = True # Bu LudoPlayer.is_active bilan sinxronlanishi kerak
    color: Optional[str] = None # O'yinchining rangi (API javobida ko'rsatish uchun)

class GameBaseAPI(BaseModel): # API javoblari uchun Pydantic model
    game_id: str
    status: str
    players: List[PlayerInGameAPI] = []
    max_players: int = 4
    host_id: Optional[int] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    current_turn_user_id: Optional[int] = None
    dice_value: Optional[int] = None
    player_order_api: List[int] = Field(default=[], alias="player_order") # LudoGame.player_order ni ko'rsatish uchun

    # model_config Pydantic v2 uchun
    class Config:
        populate_by_name = True # alias ishlatish uchun

class NewGameInfo(BaseModel):
    host_user_id: int
    host_first_name: str
    # host_username: Optional[str] = None # LudoPlayerga username kerak emas hozircha

# --- O'yin Ma'lumotlarini Saqlash ---
# active_games: Dict[str, GameBaseAPI] = {} # Endi bu kerak emas, LudoGame dan olamiz
active_ludo_games: Dict[str, LudoGame] = {} # Asosiy o'yin logikasi shu yerda

# --- WebSocket Ulanishlarini Boshqarish (avvalgi kabi) ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = set()
        self.active_connections[game_id].add(websocket)
        print(f"WebSocket ulandi: {websocket.client} o'yin {game_id} ga")

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
                print(f"WebSocket uzildi: {websocket.client} o'yin {game_id} dan")
            if not self.active_connections[game_id]: # Agar o'yinda hech kim qolmasa
                del self.active_connections[game_id]
        elif game_id in self.active_connections and not self.active_connections[game_id]:
             del self.active_connections[game_id]


    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
             print(f"Shaxsiy xabar yuborishda xatolik ({websocket.client}): {e}")


    async def broadcast_to_game(self, message: dict, game_id: str):
        if game_id in self.active_connections:
            connections_to_send = list(self.active_connections[game_id])
            for connection in connections_to_send:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_text(json.dumps(message))
                    else:
                        self.disconnect(connection, game_id)
                except Exception as e:
                    print(f"Xabar yuborishda xatolik ({connection.client} uchun, o'yin {game_id}): {e}")
                    self.disconnect(connection, game_id)

manager = ConnectionManager()

# --- FastAPI Ilovasi ---
app = FastAPI(
    title="LudoKing Game Backend API",
    description="Bu LudoKing o'yini uchun backend API.",
    version="0.1.0"
)

# === CORS SOZLAMALARI ===
origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Ruxsat etilgan originlar ro'yxati
    allow_credentials=True, # Cookie'lar bilan ishlash uchun (agar kerak bo'lsa)
    allow_methods=["*"],    # Barcha HTTP metodlariga ruxsat (GET, POST, PUT, DELETE, va hokazo)
    allow_headers=["*"],    # Barcha sarlavhalarga ruxsat
) # <--- BUNI QO'SHING (app = FastAPI(...) dan KEYIN)





# --- Helper funksiya: LudoGame obyektini API javobiga moslashtirish ---
def convert_ludo_game_to_api_response(ludo_game: LudoGame) -> GameBaseAPI:
    api_players = []
    for user_id, ludo_player_obj in ludo_game.players.items():
        api_players.append(PlayerInGameAPI(
            user_id=ludo_player_obj.user_id,
            first_name=ludo_player_obj.first_name,
            # username=... agar LudoPlayerda bo'lsa
            is_host=(ludo_game.host_id == user_id),
            is_active=not ludo_player_obj.is_sleeping,
            color=ludo_player_obj.color.value if ludo_player_obj.color else None
        ))
    
    return GameBaseAPI(
        game_id=ludo_game.game_id,
        status=ludo_game.game_status,
        players=api_players,
        max_players=ludo_game.max_players, # LudoGame da ham bo'lishi kerak
        host_id=ludo_game.host_id,
        created_at=ludo_game.created_at, # LudoGame da created_at bo'lishi kerak
        updated_at=ludo_game.updated_at, # LudoGame da updated_at bo'lishi kerak
        current_turn_user_id=ludo_game.get_current_player().user_id if ludo_game.get_current_player() else None,
        dice_value=ludo_game.current_dice_roll,
        player_order_api=ludo_game.player_order
    )

# --- API Endpointlar ---
@app.post("/games", response_model=GameBaseAPI, status_code=status.HTTP_201_CREATED, tags=["Games"])
async def create_new_game_endpoint(new_game_data: NewGameInfo = Body(...)):
    game_id = str(uuid.uuid4())
    
    # LudoGame obyektini yaratish
    ludo_game_instance = LudoGame(game_id=game_id, host_id=new_game_data.host_user_id)
    # Xostni LudoGame ga qo'shish
    ludo_game_instance.add_player(user_id=new_game_data.host_user_id, first_name=new_game_data.host_first_name)
    
    active_ludo_games[game_id] = ludo_game_instance
    print(f"Yangi Ludo o'yini (logika) yaratildi: {game_id}, Xost: {new_game_data.host_user_id}")
    
    return convert_ludo_game_to_api_response(ludo_game_instance)

@app.get("/games", response_model=List[GameBaseAPI], tags=["Games"])
async def get_all_active_games_endpoint():
    return [convert_ludo_game_to_api_response(game) for game in active_ludo_games.values()]

@app.get("/games/{game_id}", response_model=GameBaseAPI, tags=["Games"])
async def get_game_details_endpoint(game_id: str = Path(..., description="O'yinning unikal IDsi")):
    ludo_game = active_ludo_games.get(game_id)
    if not ludo_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O'yin {game_id} topilmadi")
    return convert_ludo_game_to_api_response(ludo_game)

@app.post("/games/{game_id}/register", response_model=GameBaseAPI, tags=["Players"])
async def register_player_for_game_endpoint(game_id: str = Path(..., description="O'yinning unikal IDsi"), player_data: PlayerCreate = Body(...)):
    ludo_game = active_ludo_games.get(game_id)
    if not ludo_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O'yin {game_id} topilmadi")

    print(player_data.user_id)
    if player_data.user_id in ludo_game.players:
        print('aaa')
        game_state_for_api = convert_ludo_game_to_api_response(ludo_game)
        return game_state_for_api

    if ludo_game.game_status != "registering":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu o'yinga ro'yxatdan o'tish yakunlangan yoki bekor qilingan.")

    # LudoGame ichida o'yinchilar soni tekshiriladi (max_players)
    # LudoGame ichida o'yinchi allaqachon mavjudligi tekshiriladi
    
    if len(ludo_game.players) >= 4: # Max_players ni LudoGame dan olish kerak
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O'yin to'lgan.")

    success = ludo_game.add_player(user_id=player_data.user_id, first_name=player_data.first_name)
    if not success:
        # add_player da xatolik bo'lsa (masalan, allaqachon qo'shilgan yoki rang yo'q)
        # Bu holatni LudoGame.add_player da aniqroq exception bilan qaytarish mumkin
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"O'yinchi {player_data.user_id} ni qo'shib bo'lmadi (ehtimol, allaqachon mavjud yoki o'yin to'lgan).")

    print(f"O'yinchi {player_data.user_id} ({player_data.first_name}) o'yin {game_id} ga LudoGame orqali qo'shildi.")

    game_state_for_api = convert_ludo_game_to_api_response(ludo_game)

    # O'yinchilar soni 4 ga yetganda avtomatik o'yinni boshlash
    if len(ludo_game.players) == 4 and ludo_game.game_status == "registering": # Max_players
        ludo_game.start_game() # Bu metod game_status ni "playing" ga o'zgartiradi
        print(f"O'yin {game_id} avtomatik boshlandi (LudoGame). Navbat: {ludo_game.get_current_player().user_id if ludo_game.get_current_player() else 'N/A'}")
        
        # game_state_for_api ni yangilash kerak, chunki status o'zgardi
        game_state_for_api = convert_ludo_game_to_api_response(ludo_game)
        
        await manager.broadcast_to_game(
            {"type": "game_started", "game_state": ludo_game.get_game_state()}, # LudoGame.get_game_state() ni ishlatamiz
            game_id
        )
    else:
        await manager.broadcast_to_game(
            {"type": "player_joined", "game_state": ludo_game.get_game_state()},
            game_id
        )
    return game_state_for_api


@app.post("/games/{game_id}/start", response_model=GameBaseAPI, tags=["Games"])
async def start_game_manually_endpoint(game_id: str = Path(..., description="O'yinning unikal IDsi")):
    ludo_game = active_ludo_games.get(game_id)
    if not ludo_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O'yin {game_id} topilmadi")
    
    if not ludo_game.start_game(): # start_game muvaffaqiyatli (True) yoki muvaffaqiyatsiz (False) qaytaradi
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"O'yinni boshlab bo'lmadi. Sabab: {ludo_game.game_status} yoki o'yinchilar soni yetarli emas.")
    
    print(f"O'yin {game_id} qo'lda 'playing' statusiga o'tkazildi (LudoGame). Navbat: {ludo_game.get_current_player().user_id if ludo_game.get_current_player() else 'N/A'}")
    
    await manager.broadcast_to_game(
        {"type": "game_started_manually", "game_state": ludo_game.get_game_state()},
        game_id
    )
    return convert_ludo_game_to_api_response(ludo_game)
# ... (fayl boshi va boshqa endpointlar o'zgarmaydi) ...

# --- WebSocket Endpoint ---
@app.websocket("/ws/{game_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, user_id: int):
    ludo_game = active_ludo_games.get(game_id)
    if not ludo_game:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="O'yin topilmadi")
        return
    if user_id not in ludo_game.players:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"Siz bu o'yinda ro'yxatdan o'tmagansiz.")
        return

    await manager.connect(websocket, game_id)
    player_obj = ludo_game.players.get(user_id)
    if player_obj and player_obj.is_sleeping:
        player_obj.is_sleeping = False
        ludo_game.updated_at = datetime.datetime.now(datetime.timezone.utc)
        print(f"O'yinchi {user_id} o'yin {game_id} ga qayta qo'shildi (sleep rejimidan chiqdi).")
        await manager.broadcast_to_game(
            {"type": "player_state_changed", 
            "user_id": user_id, 
            "is_sleeping": False,
            "game_state": ludo_game.get_game_state()},
            game_id
        )

    try:
        await manager.send_personal_message(
            {"type": "connection_ack", 
             "message": f"O'yin {game_id} ga ulandingiz (ID: {user_id})", 
             "game_state": ludo_game.get_game_state()},
            websocket
        )

        while True:
            data_text = await websocket.receive_text()
            try:
                data_json = json.loads(data_text)
                action_type = data_json.get("action")
                
                print(f"WS dan ({user_id} o'yin {game_id} uchun): {data_json}")

                if ludo_game.game_status != "playing":
                    await manager.send_personal_message({"type": "info", "message": "O'yin hozircha faol emas yoki tugagan."}, websocket)
                    continue

                current_turn_player = ludo_game.get_current_player()
                if not current_turn_player: # Bu holat bo'lmasligi kerak, agar game_status="playing" bo'lsa
                    await manager.send_personal_message({"type": "error", "message": "Joriy navbatdagi o'yinchi topilmadi."}, websocket)
                    continue

                # -------- O'YIN LOGIKASI BILAN BOG'LIQ HARAKATLAR --------
                if action_type == "roll_dice":
                    if current_turn_player.user_id != user_id:
                        await manager.send_personal_message({"type": "error", "message": "Hozir sizning navbatingiz emas (zar uchun)."}, websocket)
                        continue
                    
                    dice_result = ludo_game.roll_dice()
                    if dice_result is not None:
                        valid_moves = ludo_game.get_valid_moves(user_id) # Joriy zar uchun mumkin bo'lgan yurishlar
                        
                        await manager.broadcast_to_game(
                            {"type": "dice_rolled", 
                             "rolled_by_user_id": user_id,
                             "dice_value": dice_result,
                             "valid_moves": valid_moves, # Mumkin bo'lgan yurishlarni klientga yuborish
                             "game_state": ludo_game.get_game_state()},
                            game_id
                        )
                        
                        # Agar 6 tushmasa VA mumkin bo'lgan yurishlar yo'q bo'lsa, avtomatik navbatni o'tkazish
                        if not valid_moves and dice_result != 6:
                            ludo_game.next_turn()
                            await manager.broadcast_to_game(
                                {"type": "next_turn", "reason": "no_valid_moves", "game_state": ludo_game.get_game_state()}, game_id
                            )
                            print(f"O'yinchi {user_id} uchun yurish yo'q (zar {dice_result}), navbat o'tdi.")
                        elif not valid_moves and dice_result == 6:
                             # 6 tushdi, lekin yurish yo'q (masalan, hamma toshlar bloklangan yoki uyda qolganlari uchun yana 6 kerak)
                             # Bu holatda navbat o'tishi kerakmi yoki yana zar tashlaydimi? Ludo qoidasiga bog'liq.
                             # Hozircha, agar 6 tushsa va yurish yo'q bo'lsa, navbat o'tmaydi (yana zar tashlashi mumkin deb o'ylaymiz)
                             # Yoki klassik qoida bo'yicha, agar 6 bilan ham yurish bo'lmasa, navbat o'tadi.
                             # Keling, hozircha, agar 6 tushsa va yurish bo'lmasa, navbatni o'tkazamiz.
                            ludo_game.next_turn()
                            await manager.broadcast_to_game(
                                {"type": "next_turn", "reason": "no_valid_moves_on_6", "game_state": ludo_game.get_game_state()}, game_id
                            )
                            print(f"O'yinchi {user_id} 6 tashladi, lekin yurish yo'q, navbat o'tdi.")


                    else: # dice_result is None
                        await manager.send_personal_message({"type": "error", "message": "Zar tashlab bo'lmadi."}, websocket)
                
                elif action_type == "move_piece":
                    if current_turn_player.user_id != user_id:
                        await manager.send_personal_message({"type": "error", "message": "Hozir sizning navbatingiz emas (yurish uchun)."}, websocket)
                        continue

                    piece_id_to_move = data_json.get("piece_id")
                    if piece_id_to_move is None: # piece_id int bo'lishi kerak (0-3)
                        await manager.send_personal_message({"type": "error", "message": "Yurish uchun 'piece_id' ko'rsatilmagan."}, websocket)
                        continue
                    
                    try:
                        piece_id_to_move = int(piece_id_to_move)
                    except ValueError:
                        await manager.send_personal_message({"type": "error", "message": "'piece_id' butun son bo'lishi kerak."}, websocket)
                        continue

                    move_successful, captured_opponent, captured_color = ludo_game.attempt_move_piece(user_id, piece_id_to_move)
                    
                    if move_successful:
                        # TODO: G'olibni tekshirish
                        ludo_game.check_winner()
                        if ludo_game.winner_user_id:
                            await manager.broadcast_to_game(
                                {"type": "game_finished", 
                                "winner_user_id": ludo_game.winner_user_id,
                                "game_state": ludo_game.get_game_state()}, # Oxirgi holatni yuborish
                                game_id
                            )
                        else:                            
                            should_next_turn = True
                            if ludo_game.current_dice_roll == 6:
                                # Agar 6 tushgan bo'lsa, yana yurish huquqi bor
                                should_next_turn = False 
                                print(f"O'yinchi {user_id} 6 bilan yurdi, yana zar tashlaydi.")
                            
                            # TODO: Agar raqibni urgan bo'lsa, yana yurish huquqi
                            # Bu `attempt_move_piece` metodidan qaytadigan qiymatga bog'liq bo'lishi kerak
                            # (masalan, `(move_successful, captured_opponent)`)

                            elif captured_opponent: # <<-- BUNI QO'SHING
                                should_next_turn = False
                                print(f"O'yinchi {user_id} raqibni urdi ({captured_color.value if captured_color else 'N/A'}), yana yurish huquqini oldi.") # captured_color ni ishlating

                            await manager.broadcast_to_game(
                                {"type": "piece_moved", 
                                "moved_by_user_id": user_id,
                                "piece_id": piece_id_to_move,
                                "dice_value_used": ludo_game.current_dice_roll, # Qaysi zar bilan yurilganini bilish uchun
                                "captured_opponent": captured_opponent, # Klientga bu ma'lumotni yuborish mumkin
                                "captured_color": captured_color.value if captured_color else None, # Klientga urilgan tosh rangini yuborish
                                "can_roll_again": not should_next_turn,
                                "game_state": ludo_game.get_game_state()},
                                game_id
                            )


                            if should_next_turn:
                                ludo_game.next_turn()
                                await manager.broadcast_to_game(
                                    {"type": "next_turn", "reason": "move_completed", "game_state": ludo_game.get_game_state()}, game_id
                                )
                            else: # Agar yana yurish huquqi bo'lsa (masalan 6 tushganda)
                                # Klientga yana zar tashlashi mumkinligi haqida xabar yuborish (ixtiyoriy)
                                await manager.send_personal_message(
                                    {"type": "info", "message": "Siz yana zar tashlashingiz mumkin."}, websocket
                                )


                    else: # move_successful == False
                        await manager.send_personal_message(
                            {"type": "error", 
                             "message": f"Tosh {piece_id_to_move} ni yurib bo'lmadi. Mumkin bo'lgan yurishlarni tekshiring."}, 
                            websocket
                        )
                        # Agar yurish amalga oshmasa, klientga qayta `valid_moves` yuborish mumkin
                        # yoki shunchaki xatolik xabari bilan cheklanish.

                else: # Noma'lum action
                    await manager.send_personal_message({"type": "error", "message": f"Noma'lum harakat: {action_type}"}, websocket)

            except json.JSONDecodeError:
                await manager.send_personal_message({"type": "error", "message": "Noto'g'ri JSON format."}, websocket)
            except Exception as e:
                print(f"XATOLIK (WebSocket xabariga ishlov berishda, o'yin {game_id}, foydalanuvchi {user_id}): {type(e).__name__} - {e}")
                import traceback
                traceback.print_exc() # To'liq tracebackni konsolga chiqarish
                await manager.send_personal_message({"type": "error", "message": f"Serverda kutilmagan xatolik: {type(e).__name__}"}, websocket)

    # ... (except WebSocketDisconnect va qolgan qismi o'zgarmaydi) ...
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
        if ludo_game and user_id in ludo_game.players:
            ludo_game.players[user_id].is_sleeping = True
            ludo_game.updated_at = datetime.datetime.now(datetime.timezone.utc) # LudoGame obyektini yangilash
            await manager.broadcast_to_game(
                {"type": "player_state_changed", # Yoki "player_disconnected"
                "user_id": user_id, 
                "is_sleeping": True, # Yoki "status": "disconnected"
                "game_state": ludo_game.get_game_state()}, # Yangilangan holatni yuborish
                game_id
            )
    except Exception as e:
        manager.disconnect(websocket, game_id) # Har ehtimolga qarshi
        print(f"XATOLIK (WebSocket endpointida, o'yin {game_id}, foydalanuvchi {user_id}): {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()



# Webhook endpoint (bot uchun)
@app.post("/bot/new_game", response_model=BotNewGameResponse, tags=["Bot Webhooks"])
async def webhook_create_new_game_from_bot(payload: BotNewGameRequest = Body(...)):
    """
    Telegram botidan yangi o'yin yaratish uchun so'rov qabul qiladi.
    Yangi game_id generatsiya qilib, botga qaytaradi.
    """
    game_id = str(uuid.uuid4())
    
    # LudoGame obyektini yaratish, endi chat_id bilan
    ludo_game_instance = LudoGame(
        game_id=game_id,
        host_id=payload.host_user_id,
        chat_id=payload.chat_id  # <--- chat_id ni LudoGame ga uzatish
    )
    
    # Xostni LudoGame ga qo'shish
    ludo_game_instance.add_player(user_id=payload.host_user_id, first_name=payload.host_first_name)
    
    active_ludo_games[game_id] = ludo_game_instance
    print(f"Bot orqali yangi Ludo o'yini yaratildi: GameID={game_id}, ChatID={payload.chat_id}, Xost: {payload.host_user_id}")
    
    return BotNewGameResponse(
        game_id=game_id,
        chat_id=payload.chat_id,
        host_id=payload.host_user_id
    )


@app.post("/bot/set_message_id", status_code=status.HTTP_200_OK, tags=["Bot Webhooks"])
async def webhook_set_game_message_id(payload: BotSetMessageIdRequest = Body(...)):
    """
    Bot yuborgan o'yin xabarining message_id sini LudoGame obyektida saqlaydi.
    """
    ludo_game = active_ludo_games.get(payload.game_id)
    if not ludo_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O'yin {payload.game_id} topilmadi")

    ludo_game.set_message_id(payload.message_id)
    print(f"O'yin {payload.game_id} uchun message_id={payload.message_id} o'rnatildi.")
    return {"message": "Message ID muvaffaqiyatli o'rnatildi"}



@app.get("/")
async def root():
    return {"message": "LudoKing Game Backend API ishlamoqda"}