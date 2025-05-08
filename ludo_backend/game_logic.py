import random
from enum import Enum
from typing import List, Dict, Optional, Tuple
import datetime


# --- O'yin uchun konstantalar va Enumlar ---
class PieceColor(Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"

class PieceState(Enum):
    HOME = "home"       # Uyda (boshlang'ich joy)
    ACTIVE = "active"   # O'yin maydonida
    SAFE = "safe"       # Xavfsiz katakda
    FINISHED = "finished" # Marra chizig'ini kesib o'tgan

# --- O'yin Taxtasi Konfiguratsiyasi ---
# Umumiy yo'l kataklari soni (masalan, 52 ta, uylar va boshlang'ichlardan tashqari)
TOTAL_PATH_SQUARES = 52
# Har bir rang uchun uy yo'li kataklari soni (marragacha)
HOME_PATH_SQUARES = 6 # 5 ta katak + 1 marra

# Boshlang'ich pozitsiyalar (umumiy yo'ldagi indekslar)
START_POSITIONS = {
    PieceColor.RED: 0,
    PieceColor.GREEN: 13, # TOTAL_PATH_SQUARES / 4
    PieceColor.YELLOW: 26, # TOTAL_PATH_SQUARES / 2
    PieceColor.BLUE: 39   # TOTAL_PATH_SQUARES * 3 / 4
}

# Uyga kirishdan oldingi oxirgi umumiy yo'l kataklari
# Bu katakdan keyin o'z uy yo'liga o'tadi
PRE_HOME_ENTRANCE = {
    # Har bir rang o'zining boshlang'ich pozitsiyasidan bitta oldingi katakdan keyin uyiga buriladi
    # Agar boshlang'ich 0 bo'lsa, 51-katak uning oldidagi oxirgi umumiy katak
    PieceColor.RED: (START_POSITIONS[PieceColor.RED] - 1 + TOTAL_PATH_SQUARES) % TOTAL_PATH_SQUARES, # 51
    PieceColor.GREEN: (START_POSITIONS[PieceColor.GREEN] - 1 + TOTAL_PATH_SQUARES) % TOTAL_PATH_SQUARES, # 12
    PieceColor.YELLOW: (START_POSITIONS[PieceColor.YELLOW] - 1 + TOTAL_PATH_SQUARES) % TOTAL_PATH_SQUARES, # 25
    PieceColor.BLUE: (START_POSITIONS[PieceColor.BLUE] - 1 + TOTAL_PATH_SQUARES) % TOTAL_PATH_SQUARES, # 38
}
# TODO: Bu PRE_HOME_ENTRANCE logikasi to'g'rilanishi kerak. Odatda bu start_position - 1 bo'ladi.
# Misol uchun, agar Red 0 dan boshlasa, uning uyiga kirish yo'li 51-katakdan keyin.
# Agar Green 13 dan boshlasa, uning uyiga kirish yo'li 12-katakdan keyin.
# Buni aniqlashtiramiz. Hozircha taxminiy.

# Xavfsiz kataklar (umumiy yo'ldagi indekslar)
# Odatda har bir rangning boshlang'ich katagi va boshqa strategik nuqtalar
SAFE_SQUARES = [
    START_POSITIONS[PieceColor.RED],
    START_POSITIONS[PieceColor.GREEN],
    START_POSITIONS[PieceColor.YELLOW],
    START_POSITIONS[PieceColor.BLUE],
    # Boshqa xavfsiz kataklar (masalan, 8, 21, 34, 47 klassik Ludoda)
    (START_POSITIONS[PieceColor.RED] + 8) % TOTAL_PATH_SQUARES,
    (START_POSITIONS[PieceColor.GREEN] + 8) % TOTAL_PATH_SQUARES,
    (START_POSITIONS[PieceColor.YELLOW] + 8) % TOTAL_PATH_SQUARES,
    (START_POSITIONS[PieceColor.BLUE] + 8) % TOTAL_PATH_SQUARES,
]

# Maksimal pozitsiya indeksi (umumiy yo'lda)
MAX_PATH_POSITION = TOTAL_PATH_SQUARES - 1

class MoveResult(Enum):
    SUCCESS = "success"
    SUCCESS_CAPTURED_OPPONENT = "success_captured_opponent" # Raqib urildi
    SUCCESS_REACHED_FINISH = "success_reached_finish" # Marraga yetdi
    FAILED_INVALID_MOVE = "failed_invalid_move"
    FAILED_NO_PIECE = "failed_no_piece"


# --- O'yin Klasslari ---

class Piece:
    def __init__(self, piece_id: int, color: PieceColor, player_id: int):
        self.id: int = piece_id # Har bir tosh uchun unikal ID (0-3)
        self.color: PieceColor = color
        self.player_id: int = player_id # Bu tosh qaysi o'yinchiga tegishli
        self.state: PieceState = PieceState.HOME
        self.position: Optional[int] = None # Maydondagi pozitsiyasi (indeks)
        self.steps_taken: int = 0 # Uy yo'lida bosgan qadamlari

    def __repr__(self):
        return f"Piece({self.id}, {self.color.value}, P:{self.player_id}, S:{self.state.value}, Pos:{self.position})"

    def to_dict(self):
        return {
            "id": self.id,
            "color": self.color.value,
            "player_id": self.player_id,
            "state": self.state.value,
            "position": self.position,
            "steps_taken": self.steps_taken
        }

class LudoPlayer: # Bu Pydantic PlayerInGame dan farqli, bu o'yin logikasi uchun
    def __init__(self, user_id: int, first_name: str, color: PieceColor):
        self.user_id: int = user_id
        self.first_name: str = first_name
        self.color: PieceColor = color
        self.pieces: List[Piece] = [Piece(i, color, user_id) for i in range(4)]
        self.has_finished_all_pieces: bool = False # Barcha toshlari marraga yetganmi
        self.is_sleeping = False

    def __repr__(self):
        return f"LudoPlayer({self.user_id}, {self.first_name}, {self.color.value})"

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "color": self.color.value,
            "pieces": [p.to_dict() for p in self.pieces],
            "has_finished_all_pieces": self.has_finished_all_pieces
        }

class LudoGame:
    def __init__(self, game_id: str, host_id: int):
        self.game_id: str = game_id
        self.host_id: int = host_id
        self.players: Dict[int, LudoPlayer] = {} # user_id: LudoPlayer
        self.player_order: List[int] = [] # O'yinchilarning navbat tartibi (user_id lar)
        self.current_player_index: int = 0
        self.current_dice_roll: Optional[int] = None
        self.game_status: str = "registering" # "registering", "playing", "finished"
        self.winner_user_id: Optional[int] = None
        # Ranglarni o'yinchilarga taqsimlash uchun mavjud ranglar
        self.available_colors: List[PieceColor] = list(PieceColor) 
        random.shuffle(self.available_colors) # Ranglarni aralashtirish

        self.max_players: int = 4 # YANGI
        self.created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) # YANGI
        self.updated_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) # YANGI

        # O'yin taxtasi va yo'llar (keyingi bosqichda)
        # self.board = Board() 

    def add_player(self, user_id: int, first_name: str) -> bool:
        if user_id in self.players:
            print(f"O'yinchi {user_id} allaqachon o'yinda mavjud.")
            return False
        if not self.available_colors:
            print("Bo'sh rang qolmadi.")
            return False
        
        player_color = self.available_colors.pop(0)
        new_player = LudoPlayer(user_id, first_name, player_color)
        self.players[user_id] = new_player
        self.player_order.append(user_id) # Navbatga qo'shish
        print(f"O'yinchi {first_name} ({user_id}) {player_color.value} rangi bilan qo'shildi.")
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)  
        return True

    def start_game(self) -> bool:
        if len(self.players) < 2: # Minimal o'yinchilar soni
            print("O'yinni boshlash uchun yetarli o'yinchi yo'q.")
            return False
        if self.game_status == "playing":
            print("O'yin allaqachon boshlangan.")
            return False
            
        self.game_status = "playing"
        # Navbatni aralashtirish (ixtiyoriy) yoki birinchi qo'shilgan/xostdan boshlash
        # random.shuffle(self.player_order)
        self.current_player_index = 0 # Birinchi o'yinchidan boshlaymiz
        print(f"O'yin {self.game_id} boshlandi. Navbat {self.get_current_player().user_id} da.")
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        return True

    def get_current_player(self) -> Optional[LudoPlayer]:
        if not self.player_order or self.game_status != "playing":
            return None
        current_user_id = self.player_order[self.current_player_index]
        return self.players.get(current_user_id)

    def roll_dice(self) -> Optional[int]:
        current_player = self.get_current_player()
        if not current_player:
            print("Hozir hech kimning navbati emas yoki o'yin boshlanmagan.")
            return None
        
        self.current_dice_roll = random.randint(1, 6)
        print(f"O'yinchi {current_player.user_id} zar tashladi: {self.current_dice_roll}")
        # Agar 6 tushmasa va yurish imkoni bo'lmasa, navbatni o'tkazish kerak (keyinroq)
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        return self.current_dice_roll

    def next_turn(self):
        if not self.player_order or self.game_status != "playing":
            return
        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.current_dice_roll = None # Yangi navbatda zar qiymati nolga tenglashadi
        print(f"Navbat o'tdi. Endi {self.get_current_player().user_id} ning navbati.")
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    # --- Keyingi qismlarda qo'shiladigan metodlar ---
    # def get_movable_pieces(self, player_id: int, dice_roll: int) -> List[Piece]:
    #     pass
    # def move_piece(self, player_id: int, piece_id: int, dice_roll: int) -> bool:
    #     pass
    # def check_winner(self) -> Optional[int]:
    #     pass

    def get_game_state(self) -> dict:
        """O'yinning joriy holatini dict ko'rinishida qaytaradi (klientga yuborish uchun)"""
        return {
            "game_id": self.game_id,
            "status": self.game_status,
            "players": {uid: p.to_dict() for uid, p in self.players.items()},
            "player_order": self.player_order,
            "current_player_user_id": self.get_current_player().user_id if self.get_current_player() else None,
            "current_dice_roll": self.current_dice_roll,
            "winner_user_id": self.winner_user_id
        }
    

    def _calculate_new_position(self, piece: Piece, dice_roll: int) -> Tuple[Optional[int], PieceState, int]:
        """
        Berilgan tosh uchun zar natijasiga ko'ra yangi pozitsiya, holat va uy yo'lidagi qadamlarni hisoblaydi.
        Returns: (new_absolute_position_on_main_path, new_state, new_steps_on_home_path)
        new_absolute_position_on_main_path: None bo'lishi mumkin, agar HOME, HOME_PATH yoki FINISHED bo'lsa.
        Agar yurish imkonsiz bo'lsa (masalan, uy yo'lida oshib ketsa), asl holatini qaytaradi.
        """
        current_main_path_pos = piece.position
        current_state = piece.state
        current_steps_on_home_path = piece.steps_taken
        color = piece.color

        # 1. Tosh Uyda (HOME)
        if current_state == PieceState.HOME:
            if dice_roll == 6:
                # Uydan chiqish. Boshlang'ich pozitsiya xavfsiz bo'lishi mumkin.
                start_pos = START_POSITIONS[color]
                new_state = PieceState.SAFE if start_pos in SAFE_SQUARES else PieceState.ACTIVE
                return start_pos, new_state, 0
            else:
                # Uyda qoladi, o'zgarish yo'q.
                return current_main_path_pos, current_state, current_steps_on_home_path

        # 2. Tosh Marraga Yetgan (FINISHED)
        if current_state == PieceState.FINISHED:
            # O'zgarish yo'q.
            return current_main_path_pos, current_state, current_steps_on_home_path

        # 3. Tosh allaqachon Uy Yo'lida (lekin FINISHED emas)
        # Bu holatda piece.position == None va 0 < piece.steps_taken < HOME_PATH_SQUARES
        if current_main_path_pos is None and current_steps_on_home_path > 0:
            potential_total_steps_on_home = current_steps_on_home_path + dice_roll
            
            if potential_total_steps_on_home == HOME_PATH_SQUARES:
                # Marraga yetdi
                return None, PieceState.FINISHED, HOME_PATH_SQUARES
            elif potential_total_steps_on_home < HOME_PATH_SQUARES:
                # Uy yo'lida oldinga yurdi
                return None, PieceState.ACTIVE, potential_total_steps_on_home # Uy yo'li odatda xavfsiz, lekin state ACTIVE
            else:
                # Uy yo'lida oshib ketdi, joyida qoladi. Bu valid yurish emas.
                return current_main_path_pos, current_state, current_steps_on_home_path

        # 4. Tosh Umumiy Yo'lda (ACTIVE yoki SAFE)
        # Bu holatda piece.position is not None
        if current_main_path_pos is not None:
            entry_point_to_home_lane = PRE_HOME_ENTRANCE[color]
            
            temp_main_path_pos = current_main_path_pos
            
            for i in range(1, dice_roll + 1): # 1 dan dice_roll gacha qadam bosamiz
                # Agar joriy qadamda tosh uyga kirish nuqtasida bo'lsa
                # VA bu oxirgi qadam bo'lmasa (ya'ni, uyga kirish uchun kamida bitta qadam kerak)
                if temp_main_path_pos == entry_point_to_home_lane:
                    steps_taken_on_main_path_to_reach_entry = i -1 # Kirish nuqtasigacha bosilgan qadamlar
                    # Kirish nuqtasiga QADAM BOSISH uchun 1 qadam sarflanadi,
                    # bu uy yo'lidagi birinchi qadam hisoblanadi.
                    remaining_dice_for_home_path = dice_roll - (steps_taken_on_main_path_to_reach_entry + 1)
                    
                    # Uy yo'lidagi birinchi qadam + qolgan zar
                    potential_total_steps_on_home = 1 + remaining_dice_for_home_path
                    
                    if potential_total_steps_on_home == HOME_PATH_SQUARES:
                        return None, PieceState.FINISHED, HOME_PATH_SQUARES
                    elif potential_total_steps_on_home < HOME_PATH_SQUARES:
                        return None, PieceState.ACTIVE, potential_total_steps_on_home
                    else: # Uy yo'lida oshib ketdi (uyga kirishga urinib)
                        # Bu yurish valid emas, tosh joyida qoladi.
                        return piece.position, piece.state, piece.steps_taken

                # Umumiy yo'lda keyingi katakka o'tish
                temp_main_path_pos = (temp_main_path_pos + 1) % TOTAL_PATH_SQUARES

            # Agar butun zar umumiy yo'lda sarflangan bo'lsa (uyga kirmagan bo'lsa)
            # temp_main_path_pos endi yangi pozitsiyani ko'rsatadi
            new_state = PieceState.SAFE if temp_main_path_pos in SAFE_SQUARES else PieceState.ACTIVE
            return temp_main_path_pos, new_state, 0 # Uy yo'lida emas, shuning uchun 0 qadam

        # Agar yuqoridagi shartlarning hech biri bajarilmasa (bu bo'lmasligi kerak)
        # print(f"OGOHLANTIRISH: Piece {piece.id} ({color}) uchun _calculate_new_position da kutilmagan holat.")
        return piece.position, piece.state, piece.steps_taken


    def get_valid_moves(self, player_id: int) -> Dict[int, Tuple[Optional[int], str, int]]:
        """
        Joriy o'yinchi va zar qiymati uchun mumkin bo'lgan barcha valid yurishlarni qaytaradi.
        Returns: Dict[piece_id, Tuple[new_main_path_pos, new_state_value, new_steps_on_home_path]]
        """
        player = self.players.get(player_id)
        dice_roll = self.current_dice_roll

        if not player or dice_roll is None:
            # print(f"Debug (get_valid_moves): O'yinchi {player_id} yoki zar topilmadi.")
            return {}

        valid_moves: Dict[int, Tuple[Optional[int], str, int]] = {}

        for piece in player.pieces:
            if piece.state == PieceState.FINISHED:
                # print(f"Debug (get_valid_moves): Tosh {piece.id} allaqachon marrada.")
                continue

            # 1. Har bir tosh uchun potentsial yangi holatni hisoblash
            new_main_path_pos, new_state_enum, new_steps_on_home = self._calculate_new_position(piece, dice_roll)

            # 2. Agar yurish natijasida hech qanday o'zgarish bo'lmasa, bu valid yurish emas.
            # Bu holatlar:
            #   - Tosh uyda (HOME) va zar 6 emas (HOME da qoladi).
            #   - Tosh uy yo'lida va zar qiymati uni oshirib yuboradi (uy yo'lida joyida qoladi).
            #   - Tosh umumiy yo'lda va uyga kirishga urinib oshib ketadi (umumiy yo'lda joyida qoladi).
            # `_calculate_new_position` bu holatlarda toshning asl holatini qaytaradi.
            
            no_change_in_state = (new_main_path_pos == piece.position and \
                                new_state_enum == piece.state and \
                                new_steps_on_home == piece.steps_taken)

            # Maxsus holat: Agar tosh HOMEda bo'lsa va zar 6 tushib, uydan chiqsa, bu o'zgarishdir.
            is_moving_out_of_home = (piece.state == PieceState.HOME and \
                                    dice_roll == 6 and \
                                    new_state_enum != PieceState.HOME) # != HOME chunki ACTIVE yoki SAFE bo'lishi mumkin
            
            if no_change_in_state and not is_moving_out_of_home:
                # print(f"Debug (get_valid_moves): Tosh {piece.id} uchun o'zgarish yo'q, zar: {dice_roll}.")
                continue
            
            # 3. Boshlang'ich katakda o'zining boshqa toshi bo'lsa (agar uydan chiqarilayotgan bo'lsa)
            # Bu `is_moving_out_of_home` holati uchun tekshiriladi.
            # `new_main_path_pos` bu holatda START_POSITIONS[piece.color] bo'ladi.
            if is_moving_out_of_home:
                is_start_pos_occupied_by_own_piece = False
                for p_check in player.pieces:
                    # O'zi emas va yangi pozitsiyada (boshlang'ich katak) boshqa toshi bormi
                    if p_check.id != piece.id and p_check.position == new_main_path_pos:
                        is_start_pos_occupied_by_own_piece = True
                        break
                if is_start_pos_occupied_by_own_piece:
                    # print(f"Debug (get_valid_moves): Tosh {piece.id} uchun boshlang'ich katak {new_main_path_pos} band.")
                    continue # Bu toshni uydan chiqara olmaydi

            # 4. Yangi pozitsiyada (umumiy yo'lda) o'zining boshqa toshi (blokirovka)
            # Bu faqat tosh umumiy yo'lga harakatlanayotganda yoki umumiy yo'lda harakatlanayotganda tekshiriladi.
            # Agar new_main_path_pos is None bo'lsa, tosh uy yo'liga kirgan yoki FINISHED bo'lgan.
            if new_main_path_pos is not None: # Faqat umumiy yo'ldagi yangi pozitsiyalar uchun
                is_new_pos_occupied_by_own_piece = False
                for p_check in player.pieces:
                    # O'zi emas va yangi pozitsiyada boshqa toshi bormi
                    # Shuningdek, p_check FINISHED yoki HOME da bo'lmasligi kerak (garchi position None bo'lsa ham)
                    if p_check.id != piece.id and \
                    p_check.position == new_main_path_pos and \
                    p_check.state not in [PieceState.HOME, PieceState.FINISHED]:
                        is_new_pos_occupied_by_own_piece = True
                        break
                if is_new_pos_occupied_by_own_piece:
                    # print(f"Debug (get_valid_moves): Tosh {piece.id} uchun yangi pozitsiya {new_main_path_pos} o'zining boshqa toshi bilan band.")
                    continue # Bu katakka yurish mumkin emas

            # Agar barcha tekshiruvlardan o'tsa, bu valid yurish
            valid_moves[piece.id] = (new_main_path_pos, new_state_enum.value, new_steps_on_home)
        
        # print(f"Debug (get_valid_moves): O'yinchi {player_id}, Zar: {dice_roll}, Mumkin yurishlar: {valid_moves}")
        return valid_moves

    def attempt_move_piece(self, player_id: int, piece_id_to_move: int) -> Tuple[bool, bool]: # (succeeded, captured_opponent)
        player = self.players.get(player_id)
        dice_roll = self.current_dice_roll # Bu metod chaqirilishidan oldin zar tashlangan bo'lishi kerak
        
        if not player or dice_roll is None:
            print(f"Xatolik: O'yinchi ({player_id}) yoki zar ({dice_roll}) topilmadi (attempt_move_piece).")
            return False, False

        target_piece: Optional[Piece] = None
        for p in player.pieces:
            if p.id == piece_id_to_move:
                target_piece = p
                break
        
        if not target_piece or target_piece.state == PieceState.FINISHED:
            print(f"Xatolik: Tosh ({piece_id_to_move}) topilmadi yoki allaqachon marrada.")
            return False, False

        # Bu tosh uchun mumkin bo'lgan yurishni _calculate_new_position orqali qayta hisoblash
        # Yoki get_valid_moves dan olingan ma'lumotni ishlatish
        # Hozircha, qayta hisoblaymiz, chunki get_valid_moves hali to'liq emas
        
        new_pos, new_state_enum, new_steps = self._calculate_new_position(target_piece, dice_roll)

        # Agar yurish natijasida tosh joyidan qimirlamasa (valid bo'lmagan yurish)
        if target_piece.state == PieceState.HOME and new_state_enum == PieceState.HOME:
            print(f"Muvaffaqiyatsiz yurish: Tosh {target_piece.id} uyda qoldi (zar {dice_roll}).")
            return False, False
        # Agar tosh uy yo'lida oshib ketib, joyida qolgan bo'lsa (bu holatni _calc.. aniqroq qaytarishi kerak)
        if target_piece.position is None and target_piece.steps_taken > 0 and \
           new_pos is None and new_steps == target_piece.steps_taken and new_state_enum != PieceState.FINISHED:
            print(f"Muvaffaqiyatsiz yurish: Tosh {target_piece.id} uy yo'lida oshib ketdi.")
            return False, False


        # TODO: Yangi pozitsiyada o'zining boshqa toshi borligini tekshirish (blokirovka)
        # Agar `new_pos` `None` bo'lmasa:
        #   for p_check in player.pieces:
        #       if p_check.id != target_piece.id and p_check.position == new_pos:
        #           print(f"Muvaffaqiyatsiz yurish: Yangi pozitsiyada ({new_pos}) o'zining boshqa toshi bor.")
        #           return False, False
        
        captured_opponent = False
        if new_pos is not None and new_state_enum != PieceState.HOME: # Faqat maydondagi yangi pozitsiyalar uchun
            captured_opponent = self._handle_capture(new_pos, player_id)

        # Tosh holatini yangilash
        target_piece.position = new_pos
        target_piece.state = new_state_enum
        target_piece.steps_taken = new_steps
        
        print(f"O'yinchi {player_id} tosh {target_piece.id} ni yurdi. Yangi holat: Pos:{new_pos}, State:{new_state_enum.value}, StepsHome:{new_steps}")
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        return True, captured_opponent

    def _handle_capture(self, position_to_check: int, current_player_id: int):
        """
        Berilgan pozitsiyada raqib toshi bo'lsa, uni uradi.
        current_player_id - hozir yurayotgan o'yinchi.
        """
        if position_to_check in SAFE_SQUARES:
            return # Xavfsiz katakda tosh urilmaydi

        for p_id, player_obj in self.players.items():
            if p_id == current_player_id: # O'zining toshini urmaydi
                continue
            for piece_to_check in player_obj.pieces:
                if piece_to_check.position == position_to_check and piece_to_check.state not in [PieceState.HOME, PieceState.FINISHED]:
                    # Raqib toshi topildi va u maydonda
                    piece_to_check.state = PieceState.HOME
                    piece_to_check.position = None
                    piece_to_check.steps_taken = 0
                    print(f"!!! O'yinchi {current_player_id} o'yinchi {p_id} ning toshini ({piece_to_check.id}) pozitsiya {position_to_check} da urdi!")
                    # Klassik Ludoda bitta katakda bitta o'yinchining faqat bitta toshi bo'lishi mumkin,
                    # Shuning uchun bir marta urish yetarli. Agar "stack" bo'lsa, bu logika o'zgaradi.
                    return # Faqat bitta toshni uramiz (agar bir nechta bo'lsa ham)
    
    # game_logic.py LudoGame klassi ichida
    def check_winner(self) -> bool:
        if self.game_status == "finished": # Agar allaqachon g'olib aniqlangan bo'lsa
            return True

        for player_id, player in self.players.items():
            finished_pieces_count = 0
            for piece in player.pieces:
                if piece.state == PieceState.FINISHED:
                    finished_pieces_count += 1
            
            if finished_pieces_count == 4: # Barcha 4 tosh marraga yetgan
                self.winner_user_id = player_id
                player.has_finished_all_pieces = True # LudoPlayer da bu atribut bor edi
                self.game_status = "finished"
                self.updated_at = datetime.datetime.now(datetime.timezone.utc)
                print(f"!!! G'OLIB ANIQLANDI: O'yinchi {player_id} !!!")
                return True
        return False