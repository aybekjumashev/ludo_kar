# game_logic.py
import random
from enum import Enum
from typing import List, Dict, Optional, Tuple
import datetime

# --- O'yin uchun Enumlar ---
class PieceColor(Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"

class PieceState(Enum):
    HOME = "home"       # Uyda (boshlang'ich joy)
    ACTIVE = "active"   # O'yin maydonida (xavfsiz bo'lmagan)
    SAFE = "safe"       # Xavfsiz katakda yoki o'z uy yo'lida
    FINISHED = "finished" # Marra chizig'ini kesib o'tgan

class MoveResultType(Enum): # Bu enumni ishlatish/ishlatmaslik sizga bog'liq
    SUCCESS = "success"
    CAPTURED_OPPONENT = "captured_opponent"
    REACHED_FINISH = "reached_finish"
    NO_CHANGE = "no_change" # Yurish natijasida holat o'zgarmadi

# --- O'yin Doskasi Konfiguratsiyasi (Sizning `kor` va `models.py` ga asosan) ---
# BULARNI O'ZINGIZNING `kor` LUG'ATINGIZ VA `models.py` LOGIKASIGA QARAB TEKSHIRING VA TO'G'RILANG!

HOME_BASE_IDS: Dict[PieceColor, List[int]] = { # Har bir rang uchun 4 ta uy katagi IDlari
    PieceColor.RED: [1, 2, 3, 4],
    PieceColor.GREEN: [5, 6, 7, 8],
    PieceColor.YELLOW: [9, 10, 11, 12],
    PieceColor.BLUE: [13, 14, 15, 16]
}

START_PATH_IDS: Dict[PieceColor, int] = { # Uydan chiqqandagi birinchi yo'l katagi IDsi
    PieceColor.RED: 17,
    PieceColor.GREEN: 30,
    PieceColor.YELLOW: 43,
    PieceColor.BLUE: 56
}

PRE_HOME_ENTRANCE_IDS: Dict[PieceColor, int] = { # Uy yo'liga kirishdan oldingi oxirgi umumiy yo'l katagi IDsi
    PieceColor.RED: 67,
    PieceColor.GREEN: 28,
    PieceColor.YELLOW: 41,
    PieceColor.BLUE: 54
}

HOME_LANE_IDS: Dict[PieceColor, List[int]] = { # Uy yo'li kataklari IDlari (marradan oldingi 5 ta katak)
    PieceColor.RED:    [69, 70, 71, 72, 73],
    PieceColor.GREEN:  [75, 76, 77, 78, 79],
    PieceColor.YELLOW: [81, 82, 83, 84, 85],
    PieceColor.BLUE:   [87, 88, 89, 90, 91]
}

FINISH_IDS: Dict[PieceColor, int] = { # Marra kataklari IDlari
    PieceColor.RED: 74,
    PieceColor.GREEN: 80,
    PieceColor.YELLOW: 86,
    PieceColor.BLUE: 92
}

SAFE_SQUARE_IDS: List[int] = [17, 25, 30, 38, 43, 51, 56, 64] # Xavfsiz kataklar (`models.py` dagi `stars`)

MAIN_PATH_START_ID: int = 17
MAIN_PATH_END_ID: int = 68 # 68 dan keyin yana 17 ga o'tadi

SPECIAL_JUMPS: Dict[int, int] = { # models.py dan
    22: 34,
    35: 47,
    48: 60,
    61: 21
}

# --- O'yin Klasslari ---
class Piece:
    def __init__(self, piece_id: int, color: PieceColor, player_id: int):
        self.id: int = piece_id # Har bir tosh uchun unikal ID (0-3)
        self.color: PieceColor = color
        self.player_id: int = player_id
        self.state: PieceState = PieceState.HOME
        # piece.id ga qarab HOME_BASE_IDS dan boshlang'ich pozitsiyani olamiz
        self.position: Optional[int] = HOME_BASE_IDS[self.color][self.id] # Boshlang'ich uy pozitsiyasi
        # self.steps_taken: int = 0 # Bu endi kerak emas, chunki position ID o'zi yetarli

    def __repr__(self):
        return (f"Piece({self.id}, C:{self.color.value}, PUID:{self.player_id}, "
                f"S:{self.state.value}, PosID:{self.position})")

    def to_dict(self):
        return {
            "id": self.id,
            "color": self.color.value,
            "player_id": self.player_id,
            "state": self.state.value,
            "position": self.position,
        }

class LudoPlayer:
    def __init__(self, user_id: int, first_name: str, color: PieceColor):
        self.user_id: int = user_id
        self.first_name: str = first_name
        self.color: PieceColor = color
        self.pieces: List[Piece] = [Piece(i, color, user_id) for i in range(4)]
        self.has_finished_all_pieces: bool = False
        self.is_sleeping: bool = False # O'yinchi "uxlab qolgan" holati

    def __repr__(self):
        return f"LudoPlayer({self.user_id}, {self.first_name}, {self.color.value}, Sleep:{self.is_sleeping})"

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "color": self.color.value,
            "pieces": [p.to_dict() for p in self.pieces],
            "has_finished_all_pieces": self.has_finished_all_pieces,
            "is_sleeping": self.is_sleeping # Frontend uchun
        }

class LudoGame:
    def __init__(self, game_id: str, host_id: int, chat_id: int):
        self.game_id: str = game_id
        self.host_id: int = host_id # O'yinni yaratgan foydalanuvchi IDsi
        self.chat_id: int = chat_id  # <--- YANGI: Guruh IDsi
        self.message_id: Optional[int] = None  # <--- YANGI: Bot yuborgan xabarning IDsi
        self.players: Dict[int, LudoPlayer] = {} # user_id: LudoPlayer
        self.player_order: List[int] = [] # O'yinchilarning navbat tartibi (user_id lar)
        self.current_player_index: int = 0
        self.current_dice_roll: Optional[int] = None
        self.game_status: str = "registering" # "registering", "playing", "finished", "cancelled"
        self.winner_user_id: Optional[int] = None
        self.available_colors: List[PieceColor] = list(PieceColor)
        random.shuffle(self.available_colors)

        self.max_players: int = 4
        self.min_players_to_start: int = 2 # O'yinni boshlash uchun minimal o'yinchilar
        self.created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        self.updated_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        self.last_action_time: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) # Navbat taymeri uchun

        # Timer uchun o'zgaruvchilar
        self.turn_time_limit_seconds: int = 30  # Har bir yurish uchun sekundlar
        self.turn_timer_deadline: Optional[float] = None  # Unix timestamp (float)

    def _update_timestamp(self):
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.last_action_time = self.updated_at # Har qanday muhim harakatda yangilanadi

    def add_player(self, user_id: int, first_name: str) -> bool:
        if user_id in self.players:
            print(f"O'yinchi {user_id} allaqon o'yinda.")
            return True # Yoki False, agar qayta qo'shilishni cheklamoqchi bo'lsangiz
        if len(self.players) >= self.max_players:
            print("O'yin to'lgan, yangi o'yinchi qo'shib bo'lmaydi.")
            return False
        if not self.available_colors:
            print("Bo'sh rang qolmadi.") # Bu holat bo'lmasligi kerak, agar max_players=4 va 4 ta rang bo'lsa
            return False

        player_color = self.available_colors.pop(0)
        new_player = LudoPlayer(user_id, first_name, player_color)
        self.players[user_id] = new_player
        if user_id not in self.player_order: # Agar qayta qo'shilish bo'lsa, tartibga qo'shmaymiz
            self.player_order.append(user_id)
        
        print(f"O'yinchi {first_name} ({user_id}) {player_color.value} rangi bilan qo'shildi.")
        self._update_timestamp()
        return True

    def start_game(self) -> bool:
        if len(self.players) < self.min_players_to_start:
            print(f"O'yinni boshlash uchun yetarli o'yinchi yo'q (kerak: {self.min_players_to_start}, mavjud: {len(self.players)}).")
            return False
        if self.game_status == "playing":
            print("O'yin allaqon boshlangan.")
            return False # Yoki True, agar bu chaqiruv zararsiz bo'lsa

        self.game_status = "playing"
        # Navbatni aralashtirish ixtiyoriy, hozircha qo'shilish tartibida
        # random.shuffle(self.player_order)
        self.current_player_index = 0 # Birinchi o'yinchidan boshlaymiz
        print(f"O'yin {self.game_id} boshlandi. Navbat {self.get_current_player().user_id if self.get_current_player() else 'N/A'} da.")
        self._update_timestamp()
        return True

    def get_current_player(self) -> Optional[LudoPlayer]:
        if not self.player_order or self.game_status != "playing" or self.current_player_index >= len(self.player_order):
            return None
        current_user_id = self.player_order[self.current_player_index]
        return self.players.get(current_user_id)

    def roll_dice(self) -> Optional[int]:
        current_player = self.get_current_player()
        if not current_player or current_player.is_sleeping: # Uyqudagi o'yinchi zar tashlay olmaydi
            print("Hozirgi o'yinchi zar tashlay olmaydi (navbati emas, topilmadi yoki uxlayapti).")
            return None

        self.current_dice_roll = random.randint(1, 6)
        print(f"O'yinchi {current_player.user_id} zar tashladi: {self.current_dice_roll}")
        self._update_timestamp()
        return self.current_dice_roll

    def _calculate_new_position(self, piece: Piece, dice_roll: int) -> Tuple[Optional[int], PieceState]:
        """
        Berilgan tosh uchun zar natijasiga ko'ra yangi pozitsiya IDsi va holatini hisoblaydi.
        Returns: (new_position_id, new_state)
        Agar yurish imkonsiz bo'lsa (masalan, uy yo'lida oshib ketsa), asl (position_id, state) qaytariladi.
        """
        current_pos_id = piece.position
        current_state = piece.state
        color = piece.color

        # 1. Tosh Marraga Yetgan (FINISHED)
        if current_state == PieceState.FINISHED:
            return current_pos_id, current_state

        # 2. Tosh Uyda (HOME)
        if current_state == PieceState.HOME:
            if dice_roll == 6:
                new_pos_id = START_PATH_IDS[color]
                new_state = PieceState.SAFE if new_pos_id in SAFE_SQUARE_IDS else PieceState.ACTIVE
                return new_pos_id, new_state
            else:
                return current_pos_id, current_state # Uyda qoladi

        # 3. Tosh Yo'lda (ACTIVE yoki SAFE, shu jumladan o'zining uy yo'lida)
        temp_pos_id = current_pos_id
        
        # Tosh allaqachon uy yo'lidami?
        is_on_home_lane = temp_pos_id in HOME_LANE_IDS[color]
        
        for i in range(1, dice_roll + 1): # Zar qadamlarini birma-bir bosamiz
            if is_on_home_lane:
                current_lane_idx = HOME_LANE_IDS[color].index(temp_pos_id)
                if current_lane_idx + 1 < len(HOME_LANE_IDS[color]): # Uy yo'lida oldinga
                    temp_pos_id = HOME_LANE_IDS[color][current_lane_idx + 1]
                else: # Uy yo'lining oxirgi katagida, keyingisi marra
                    # Bu i-qadamda marraga yetdi
                    if i == dice_roll: # Agar zar aynan shu qadamda tugasa
                        temp_pos_id = FINISH_IDS[color]
                        break # For loopdan chiqish
                    else: # Zar ortiqcha, marradan oshib ketadi
                        return current_pos_id, current_state # Joyida qoladi, yurish imkonsiz
            
            # Umumiy yo'lda yoki uy yo'liga kirish arafasida
            elif temp_pos_id == PRE_HOME_ENTRANCE_IDS[color]:
                # Bu qadamda o'z uy yo'liga kiradi
                temp_pos_id = HOME_LANE_IDS[color][0]
                is_on_home_lane = True # Keyingi qadamlar uy yo'lida bo'ladi
            
            elif temp_pos_id == MAIN_PATH_END_ID: # Umumiy yo'lning oxiri
                temp_pos_id = MAIN_PATH_START_ID # Umumiy yo'lning boshiga o'tadi
            
            else: # Umumiy yo'lda oddiy oldinga yurish
                temp_pos_id += 1
            
            # Maxsus sakrashlar (agar mavjud bo'lsa va umumiy yo'lda bo'lsa)
        if not is_on_home_lane and temp_pos_id in SPECIAL_JUMPS:
            temp_pos_id = SPECIAL_JUMPS[temp_pos_id]

        # Yakuniy holatni aniqlash
        final_pos_id = temp_pos_id
        new_state: PieceState

        if final_pos_id == FINISH_IDS[color]:
            new_state = PieceState.FINISHED
        elif final_pos_id in HOME_LANE_IDS[color] or final_pos_id in SAFE_SQUARE_IDS:
            new_state = PieceState.SAFE
        elif final_pos_id in HOME_BASE_IDS[color]: # Bu holat bo'lmasligi kerak, agar HOME dan chiqqan bo'lsa
             new_state = PieceState.HOME
        else: # Umumiy yo'ldagi oddiy (xavfsiz bo'lmagan) katak
            new_state = PieceState.ACTIVE
        
        return final_pos_id, new_state


    def get_valid_moves(self, player_id: int) -> Dict[int, Tuple[Optional[int], str]]:
        """
        Joriy o'yinchi va zar qiymati uchun mumkin bo'lgan barcha valid yurishlarni qaytaradi.
        Returns: Dict[piece_id, Tuple[new_position_id, new_state_value]]
        """
        player = self.players.get(player_id)
        dice_roll = self.current_dice_roll

        if not player or dice_roll is None or player.is_sleeping:
            return {}

        valid_moves: Dict[int, Tuple[Optional[int], str]] = {}

        for piece in player.pieces:
            if piece.state == PieceState.FINISHED:
                continue

            new_pos_id, new_state_enum = self._calculate_new_position(piece, dice_roll)

            # Agar yurish natijasida hech qanday o'zgarish bo'lmasa (joyida qolsa), bu valid yurish emas.
            # Istisno: Uydan chiqish (HOME -> ACTIVE/SAFE) har doim o'zgarish.
            is_moving_out_of_home = (piece.state == PieceState.HOME and new_state_enum != PieceState.HOME)
            
            if new_pos_id == piece.position and new_state_enum == piece.state and not is_moving_out_of_home:
                continue # O'zgarish yo'q, valid emas

            # Yangi pozitsiyada o'zining boshqa toshi borligini tekshirish (blokirovka)
            # Bu faqat yangi pozitsiya HOME yoki FINISHED bo'lmaganda tekshiriladi
            if new_state_enum not in [PieceState.HOME, PieceState.FINISHED]:
                is_new_pos_occupied_by_own_active_piece = False
                for p_check in player.pieces:
                    if p_check.id != piece.id and \
                       p_check.position == new_pos_id and \
                       p_check.state not in [PieceState.HOME, PieceState.FINISHED]:
                        is_new_pos_occupied_by_own_active_piece = True
                        break
                if is_new_pos_occupied_by_own_active_piece:
                    continue # Bu katakka yura olmaydi, o'zining boshqa faol toshi bor

            valid_moves[piece.id] = (new_pos_id, new_state_enum.value)
        
        return valid_moves

    def attempt_move_piece(self, player_id: int, piece_id_to_move: int) -> Tuple[bool, bool, Optional[PieceColor]]: # (succeeded, captured_opponent, captured_opponent_color)
        player = self.players.get(player_id)
        dice_roll = self.current_dice_roll

        if not player or dice_roll is None or player.is_sleeping:
            return False, False, None
        if player.user_id != self.get_current_player().user_id: # Navbat tekshiruvi
            return False, False, None

        target_piece: Optional[Piece] = None
        for p in player.pieces:
            if p.id == piece_id_to_move:
                target_piece = p
                break
        
        if not target_piece or target_piece.state == PieceState.FINISHED:
            return False, False, None

        # Mumkin bo'lgan yurishlar orasidan tanlanganini tekshirish
        possible_moves = self.get_valid_moves(player_id)
        if piece_id_to_move not in possible_moves:
            print(f"Xatolik: Tosh {piece_id_to_move} uchun zar {dice_roll} bilan valid yurish yo'q.")
            return False, False, None
        
        new_pos_id, new_state_str = possible_moves[piece_id_to_move]
        new_state_enum = PieceState(new_state_str)

        # Tosh holatini yangilash
        original_position_before_move = target_piece.position # Urish uchun
        target_piece.position = new_pos_id
        target_piece.state = new_state_enum
        
        captured_opponent = False
        captured_opponent_color: Optional[PieceColor] = None

        # Raqibni urish logikasi (agar yangi pozitsiya HOME yoki FINISHED bo'lmasa va xavfsiz katak bo'lmasa)
        if new_state_enum not in [PieceState.HOME, PieceState.FINISHED] and \
           new_pos_id is not None and new_pos_id not in SAFE_SQUARE_IDS and \
           new_pos_id not in HOME_LANE_IDS[target_piece.color]: # O'zining uy yo'lida urmaydi
            
            for opp_player_id, opp_player_obj in self.players.items():
                if opp_player_id == player_id: # O'zini o'zi urmaydi
                    continue
                for opp_piece in opp_player_obj.pieces:
                    if opp_piece.position == new_pos_id and \
                       opp_piece.state not in [PieceState.HOME, PieceState.FINISHED]:
                        # Raqib toshi topildi
                        opp_piece.state = PieceState.HOME
                        opp_piece.position = HOME_BASE_IDS[opp_piece.color][opp_piece.id] # Uyiga qaytarish
                        captured_opponent = True
                        captured_opponent_color = opp_piece.color
                        print(f"!!! O'yinchi {player_id} o'yinchi {opp_player_id} ning {opp_piece.color.value} rangli toshini ({opp_piece.id}) pozitsiya {new_pos_id} da urdi!")
                        break # Bitta katakda bir nechta raqib toshi bo'lsa, faqat bittasi uriladi (klassik qoida)
                if captured_opponent:
                    break
        
        print(f"O'yinchi {player_id} tosh {target_piece.id} ni yurdi. Yangi holat: PosID:{new_pos_id}, State:{new_state_enum.value}")
        self._update_timestamp()
        self.check_winner() # Har bir yurishdan keyin g'olibni tekshirish
        return True, captured_opponent, captured_opponent_color

    def start_turn_timer(self):
        import time
        self.turn_timer_deadline = time.time() + self.turn_time_limit_seconds

    def get_turn_time_left(self) -> Optional[int]:
        import time
        if self.turn_timer_deadline is None:
            return None
        left = int(self.turn_timer_deadline - time.time())
        return max(left, 0)

    def next_turn(self) -> None:
        """O'yin navbatini keyingi o'yinchiga o'tkazadi"""
        self._reset_current_dice_roll()
        
        if not self.current_turn_color:
            # O'yin endi boshlangan. Birinchi navbat random
            self.current_turn_color = random.choice(list(self.active_player_colors))
        else:
            # Keyingi rangni top
            current_color_index = list(PieceColor).index(self.current_turn_color)
            for _ in range(4):  # Maximum 4 ta rang bor
                current_color_index = (current_color_index + 1) % len(PieceColor)
                next_color = list(PieceColor)[current_color_index]
                if next_color in self.active_player_colors:
                    self.current_turn_color = next_color
                    break

        # Reset and start the turn timer
        self.start_turn_timer()
        self._update_timestamp()

    def check_winner(self) -> bool:
        if self.game_status == "finished":
            return True

        for player_id, player in self.players.items():
            if player.has_finished_all_pieces: # Agar allaqon yutgan bo'lsa
                if self.winner_user_id is None: # Bu faqat bir marta o'rnatilishi kerak
                    self.winner_user_id = player_id
                    self.game_status = "finished"
                    print(f"G'olib allaqon belgilangan: {player_id}")
                # Agar bir nechta o'yinchi bir vaqtda yutsa (kamdan-kam), logikani kengaytirish mumkin
                continue

            finished_pieces_count = 0
            for piece in player.pieces:
                if piece.state == PieceState.FINISHED:
                    finished_pieces_count += 1
            
            if finished_pieces_count == 4:
                self.winner_user_id = player_id
                player.has_finished_all_pieces = True
                self.game_status = "finished"
                self._update_timestamp()
                print(f"!!! G'OLIB ANIQLANDI: O'yinchi {player_id} !!!")
                return True # G'olib topildi
        return False # Hali g'olib yo'q
    
    def set_message_id(self, message_id: int): # <--- YANGI METOD
        self.message_id = message_id
        self._update_timestamp()

    def get_game_state(self) -> dict:
        """O'yinning joriy holatini dict ko'rinishida qaytaradi (klientga yuborish uchun)"""
        current_player = self.get_current_player()
        state = {
            "game_id": self.game_id,
            "status": self.game_status,
            "players": {uid: p.to_dict() for uid, p in self.players.items()},
            "player_order": self.player_order,
            "current_player_user_id": current_player.user_id if current_player else None,
            "current_dice_roll": self.current_dice_roll,
            "winner_user_id": self.winner_user_id,
            "host_id": self.host_id,
            "max_players": self.max_players,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "turn_time_left": self.get_turn_time_left(),
            "turn_time_limit": self.turn_time_limit_seconds
        }
        return state

    def set_player_sleep_status(self, player_id: int, is_sleeping: bool):
        player = self.players.get(player_id)
        if player:
            was_sleeping = player.is_sleeping
            player.is_sleeping = is_sleeping
            self._update_timestamp()
            print(f"O'yinchi {player_id} ning uyqu holati o'zgartirildi: {is_sleeping}")
            
            # Agar hozir navbati kelgan o'yinchi uxlayotgan bo'lsa va endi uyg'ongan bo'lmasa
            # yoki endi uxlab qolgan bo'lsa, navbatni tekshirish kerak.
            current_navbatdagi_player = self.get_current_player()
            if current_navbatdagi_player and current_navbatdagi_player.user_id == player_id and is_sleeping:
                print(f"Navbatdagi o'yinchi {player_id} uxlab qoldi, navbat o'tkaziladi.")
                self.next_turn() # Darhol navbatni o'tkazish
            elif not is_sleeping and was_sleeping: # Agar uyg'ongan bo'lsa
                 # Qayta qo'shilish logikasi (masalan, xabar yuborish) backend WebSocket qismida hal qilinadi
                 pass


# Test uchun (ixtiyoriy)
if __name__ == '__main__':
    game = LudoGame("test_game_123", host_id=100)
    game.add_player(100, "Ali")
    game.add_player(200, "Vali")
    
    game.start_game()
    
    current_player_obj = game.get_current_player()
    if current_player_obj:
        print(f"O'yin boshlandi. Birinchi navbat: {current_player_obj.first_name} ({current_player_obj.user_id})")
        
        # Test: Uydan chiqarish
        print("\n--- Test: Uydan chiqarish ---")
        game.current_dice_roll = 6
        player_100_pieces = game.players[100].pieces
        
        # 0-toshni (ID 0) uydan chiqarishga harakat
        valid_moves_p100 = game.get_valid_moves(100)
        print(f"O'yinchi 100 uchun zar 6 bilan mumkin bo'lgan yurishlar: {valid_moves_p100}")
        
        if 0 in valid_moves_p100: # Agar 0-toshni yurish mumkin bo'lsa
            succeeded, captured, _ = game.attempt_move_piece(100, 0) # 0 - piece_id
            print(f"0-toshni yurish natijasi: Succeeded={succeeded}, Captured={captured}")
            print(f"0-toshning yangi holati: {player_100_pieces[0]}")
        else:
            print("0-toshni zar 6 bilan uydan chiqarib bo'lmadi (valid movesda yo'q).")

        print(f"\nO'yin holati: {game.get_game_state()}")

        # Test: Oddiy yurish
        print("\n--- Test: Oddiy yurish (agar tosh maydonda bo'lsa) ---")
        if player_100_pieces[0].state != PieceState.HOME: # Agar 0-tosh maydonga chiqqan bo'lsa
            game.current_dice_roll = 3
            valid_moves_p100_after_out = game.get_valid_moves(100)
            print(f"O'yinchi 100 uchun zar 3 bilan mumkin bo'lgan yurishlar: {valid_moves_p100_after_out}")
            if 0 in valid_moves_p100_after_out:
                 succeeded, captured, _ = game.attempt_move_piece(100, 0)
                 print(f"0-toshni (maydonda) zar 3 bilan yurish: Succeeded={succeeded}, Captured={captured}")
                 print(f"0-toshning yangi holati: {player_100_pieces[0]}")
            else:
                print("0-toshni zar 3 bilan yurib bo'lmadi.")
        else:
            print("0-tosh hali ham uyda, oddiy yurishni test qilib bo'lmaydi.")

        game.next_turn()
        current_player_obj_after_turn = game.get_current_player()
        if current_player_obj_after_turn:
             print(f"\nKeyingi navbat: {current_player_obj_after_turn.first_name} ({current_player_obj_after_turn.user_id})")


        # Test: Uyqu holati
        print("\n--- Test: Uyqu holati ---")
        game.set_player_sleep_status(200, True) # Vali uxlab qoldi
        print(f"Valining holati: {game.players[200]}")
        
        # Alining navbati (agar avvalgi navbat Alida bo'lsa va u 6 tashlamagan bo'lsa)
        # Agar Alining navbati bo'lsa, u yursin.
        if game.get_current_player().user_id == 100:
            game.current_dice_roll = 2
            valid_moves_ali_sleep = game.get_valid_moves(100)
            print(f"Ali (Vali uxlayotganda) zar 2 bilan yurishlari: {valid_moves_ali_sleep}")
            # ... yurishni amalga oshirish ...
            # game.attempt_move_piece(100, piece_to_move_id)
            game.next_turn() # Navbatni o'tkazish

        print(f"Vali uxlayotgandan keyingi navbat: {game.get_current_player().user_id if game.get_current_player() else 'N/A'}")
        # Bu yerda navbat yana 100 (Ali) ga qaytishi kerak, chunki Vali (200) uxlayapti.