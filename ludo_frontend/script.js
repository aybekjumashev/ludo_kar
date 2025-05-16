// script.js

const tg = window.Telegram.WebApp;

// HTML Elementlari
const gameIdDisplay = document.getElementById('game-id-display');
const gameStatusDisplay = document.getElementById('game-status-display');
const userIdDisplay = document.getElementById('user-id-display');
const playersListUl = document.getElementById('players-list');
const diceValueDisplay = document.getElementById('dice-value-display');
const rollDiceButton = document.getElementById('roll-dice-button');
const currentTurnPlayerDisplay = document.getElementById('current-turn-player-display');
const systemMessageDisplay = document.getElementById('system-message');
const gameBoardContainer = document.getElementById('game-board-container');

// O'yin holati uchun global o'zgaruvchilar
let currentGameId = null;
let currentUserId = null;
let currentUsername = null;
let websocket = null;
let currentGameState = null; // Backenddan keladigan to'liq o'yin holati

// Backend API va WebSocket manzillari (o'zgartiring!)
const API_BASE_URL = 'http://127.0.0.1:8000'; // Sizning backend manzilingiz
const WS_BASE_URL = 'ws://127.0.0.1:8000';  // Sizning WebSocket manzilingiz

const playerNameCoordinatesPercent = {
    red:    { top: '88%', left: '80%', textAlign: 'right' },  // Pastki o'ng burchak
    green:  { top: '88%', left: '2%', textAlign: 'left' },   // Pastki chap burchak
    yellow: { top: '2%', left: '2%', textAlign: 'left' },    // Yuqori chap burchak
    blue:   { top: '2%', left: '80%', textAlign: 'right' }    // Yuqori o'ng burchak
};

// --- postoimg.py dan `kor` lug'ati va doska o'lchamlari ---
// BU `korBackend` LUG'ATINI TO'LIQ TO'LDIRING!
const korBackend = {
    1:[105,710], 2:[227,710], 3:[105,832], 4:[227,832], 5:[105,108], 6:[227,108], 7:[105,230], 8:[227,230],
    9:[708,108], 10:[830,108], 11:[708,230], 12:[830,230], 13:[708,710], 14:[830,710], 15:[708,832], 16:[830,832],
    17:[400,872], 18:[400,805], 19:[400,738], 20:[400,671], 21:[400,604], 22:[333,537], 23:[266,537], 24:[199,537],
    25:[132,537], 26:[65,537], 27:[-2,537], 28:[-2,470], 29:[-2,403], 30:[65,403], 31:[132,403], 32:[199,403],
    33:[266,403], 34:[333,403], 35:[400,336], 36:[400,269], 37:[400,202], 38:[400,135], 39:[400,68], 40:[400,1],
    41:[467,1], 42:[534,1], 43:[534,68], 44:[534,135], 45:[534,202], 46:[534,269], 47:[534,336], 48:[601,403],
    49:[668,403], 50:[735,403], 51:[802,403], 52:[869,403], 53:[936,403], 54:[936,470], 55:[936,537], 56:[869,537],
    57:[802,537], 58:[735,537], 59:[668,537], 60:[601,537], 61:[534,604], 62:[534,671], 63:[534,738], 64:[534,805],
    65:[534,872], 66:[534,939], 67:[467,939], 68:[400,939],
    69:[467,872], 70:[467,805], 71:[467,738], 72:[467,671], 73:[467,604], 74:[467,537], // Qizil marra (74)
    75:[65,470], 76:[132,470], 77:[199,470], 78:[266,470], 79:[333,470], 80:[400,470], // Yashil marra (80)
    81:[467,68], 82:[467,135], 83:[467,202], 84:[467,269], 85:[467,336], 86:[467,403], // Sariq marra (86)
    87:[869,470], 88:[802,470], 89:[735,470], 90:[668,470], 91:[601,470], 92:[534,470]  // Moviy marra (92)
};

// `board.jpg` ning haqiqiy o'lchamlarini kiriting! Bu juda muhim.
const ETALON_BOARD_WIDTH = 1000;  // Sizning `board.jpg` rasmingizning kengligi (pikselda)
const ETALON_BOARD_HEIGHT = 1000; // Sizning `board.jpg` rasmingizning balandligi (pikselda)

const pieceCoordinatesPercent = {};
for (const key in korBackend) {
    if (korBackend.hasOwnProperty(key)) {
        const coordsPx = korBackend[key];
        pieceCoordinatesPercent[key] = {
            x: parseFloat((((coordsPx[0]+30) / ETALON_BOARD_WIDTH) * 100).toFixed(2)),
            y: parseFloat((((coordsPx[1]+30) / ETALON_BOARD_HEIGHT) * 100).toFixed(2)),
        };
    }
}
// --- Tugadi: postoimg.py dan `kor` lug'ati ---


// Mini App ishga tushganda
window.addEventListener('load', () => {
    tg.ready();
    tg.expand();

    const initData = tg.initDataUnsafe;
    if (initData && initData.user) {
        currentUserId = initData.user.id;
        currentUsername = initData.user.first_name || initData.user.username || `User ${initData.user.id}`;
        userIdDisplay.textContent = `${currentUsername} (${currentUserId})`;
    } else {
        console.error("Foydalanuvchi ma'lumotlari topilmadi!");
        gameStatusDisplay.textContent = "Xatolik: Foydalanuvchi ma'lumotlari yo'q.";
        tg.showAlert("Telegram foydalanuvchi ma'lumotlarini olib bo'lmadi. Iltimos, qayta urinib ko'ring.");
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    currentGameId = urlParams.get('tgWebAppStartParam'); // Bot /start buyrug'i bilan game_id ni yuboradi

    if (currentGameId) {
        gameIdDisplay.textContent = currentGameId;
        registerOrGetGameInfo();
    } else {
        gameStatusDisplay.textContent = "Xatolik: O'yin ID topilmadi.";
        console.error("URLda 'tgWebAppStartParam' orqali o'yin IDsi topilmadi. URL:", window.location.href);
        tg.showAlert("O'yin ID URL'da ko'rsatilmagan. Iltimos, bot orqali qayta kiring.");
    }
});

async function registerOrGetGameInfo() {
    if (!currentGameId || !currentUserId) {
        console.error("registerOrGetGameInfo: currentGameId yoki currentUserId mavjud emas.");
        gameStatusDisplay.textContent = "Xatolik: Kerakli ma'lumotlar topilmadi.";
        return;
    }

    gameStatusDisplay.textContent = "O'yinga qo'shilmoqda...";
    systemMessageDisplay.textContent = "";

    try {
        console.log(`O'yin ${currentGameId} ga o'yinchi ${currentUserId} (${currentUsername}) ni ro'yxatdan o'tkazish/ma'lumot olish...`);
        const response = await fetch(`${API_BASE_URL}/games/${currentGameId}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUserId,
                first_name: currentUsername,
                // username: tg.initDataUnsafe?.user?.username // Agar backendda kerak bo'lsa
            }),
        });
        console.log(response)

        const responseData = await response.json();

        if (response.ok) {
            console.log("Ro'yxatdan o'tish/ma'lumot olish muvaffaqiyatli:", responseData);
            currentGameState = responseData; // API javobi GameBaseAPI formatida bo'lishi kerak
            updateUIWithGameState(currentGameState);
        } else {
            console.warn(`Ro'yxatdan o'tish/ma'lumot olishda xatolik. Status: ${response.status}`, responseData);
            const detailMessage = responseData.detail || `Noma'lum server xatoligi (status: ${response.status}).`;
            systemMessageDisplay.textContent = `Server xabari: ${detailMessage}`;
            if (response.status === 404) {
                gameStatusDisplay.textContent = `Xatolik: O'yin (${currentGameId}) topilmadi.`;
                tg.showAlert(`O'yin ${currentGameId} serverda topilmadi. Iltimos, bot orqali qayta urinib ko'ring.`);
                return; // WebSocket'ga ulanmaymiz
            }
            // Boshqa xatoliklarda (masalan, o'yin to'lgan, o'yin boshlangan) ham UI yangilanadi
            // va WebSocket'ga ulanishga harakat qilinadi (kuzatuvchi sifatida).
            // Agar backend /register da xatolik bo'lsa ham game_state qaytarsa, uni ishlatamiz
            if (responseData && responseData.game_id) { // Agar xatolik bilan birga game_state kelsa
                currentGameState = responseData;
                updateUIWithGameState(currentGameState);
            }
        }
        // Har qanday holatda (agar 404 bo'lmasa) WebSocket'ga ulanamiz.
        // Chunki o'yinchi allaqachon ro'yxatdan o'tgan bo'lishi yoki kuzatuvchi bo'lishi mumkin.
        connectWebSocket();

    } catch (error) {
        console.error("registerOrGetGameInfo funksiyasida umumiy xatolik:", error);
        gameStatusDisplay.textContent = "Aloqa xatoligi";
        systemMessageDisplay.textContent = `Tizim xatoligi: ${error}. Sahifani yangilang.`;
        tg.showAlert(`Server bilan bog'lanishda xatolik: ${error.message}`);
    }
}

function connectWebSocket() {
    if (!currentGameId || !currentUserId) {
        console.error("WebSocket ulanishi uchun currentGameId yoki currentUserId mavjud emas.");
        return;
    }
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        console.log("WebSocket allaqachon ulangan.");
        return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/${currentGameId}/${currentUserId}`;
    console.log(`WebSocket'ga ulanmoqda: ${wsUrl}`);
    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log("WebSocket ulandi!");
        gameStatusDisplay.textContent = "Ulanildi.";
        systemMessageDisplay.textContent = `O'yin ${currentGameId} ga muvaffaqiyatli ulandingiz.`;
        // Odatda server birinchi "connection_ack" va o'yin holatini yuboradi.
    };

    websocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("WebSocket xabari:", data);

            // Har qanday xabarda game_state bo'lsa, UI ni yangilaymiz
            if (data.game_state) {
                currentGameState = data.game_state;
                updateUIWithGameState(data.game_state);
            }

            switch (data.type) {
                case "connection_ack":
                    systemMessageDisplay.textContent = data.message || "Serverga ulanildi.";
                    break;
                case "player_joined":
                    systemMessageDisplay.textContent = `Yangi o'yinchi qo'shildi.`;
                    break;
                case "game_started":
                case "game_started_manually":
                    systemMessageDisplay.textContent = "O'yin boshlandi!";
                    break;
                case "dice_rolled":
                    const roller = currentGameState.players[data.rolled_by_user_id];
                    const rollerName = roller ? roller.first_name : data.rolled_by_user_id;
                    systemMessageDisplay.textContent = `${rollerName} ${data.dice_value} tashladi.`;
                    if (data.rolled_by_user_id === currentUserId) {
                        handleValidMoves(data.valid_moves || {});
                    }
                    break;
                case "piece_moved":
                    // UI allaqachon game_state orqali yangilangan bo'lishi kerak.
                    // Bu yerda qo'shimcha xabar chiqarish mumkin.
                    systemMessageDisplay.textContent = "Tosh yurildi.";
                    clearMovablePieceHighlights();
                    if (data.moved_by_user_id === currentUserId && data.can_roll_again) {
                        systemMessageDisplay.textContent += " Siz yana zar tashlashingiz mumkin.";
                        rollDiceButton.disabled = false;
                        // Muhim: current_dice_roll ni null qilmaymiz, chunki serverda u hali ham oldingi qiymatda
                        // Lekin UI da "Zar: -" ko'rinishi uchun currentGameState ni o'zgartirish mumkin, ammo bu server bilan nomuvofiqlik keltirishi mumkin.
                        // Yaxshisi, server current_dice_roll ni null qilishi kerak, agar yana zar tashlash kerak bo'lsa.
                        // Yoki klient serverga current_dice_roll ni e'tiborga olmasdan "roll_dice" yuboradi.
                    }
                    break;
                case "next_turn":
                    systemMessageDisplay.textContent = `Navbat ${currentGameState.players[currentGameState.current_player_user_id]?.first_name || '-'} ga o'tdi.`;
                    clearMovablePieceHighlights();
                    break;
                case "player_state_changed":
                    const changedPlayer = currentGameState.players[data.user_id];
                    const changedPlayerName = changedPlayer ? changedPlayer.first_name : data.user_id;
                    systemMessageDisplay.textContent = `O'yinchi ${changedPlayerName} holati o'zgardi (${data.is_sleeping ? 'uxlab qoldi' : 'qaytdi'}).`;
                    break;
                case "game_finished":
                    const winner = currentGameState.players[data.winner_user_id];
                    const winnerName = winner ? winner.first_name : data.winner_user_id;
                    systemMessageDisplay.textContent = `O'YIN TUGADI! G'olib: ${winnerName}!`;
                    rollDiceButton.disabled = true;
                    clearMovablePieceHighlights();
                    break;
                case "error":
                    console.error("Serverdan xatolik:", data.message);
                    systemMessageDisplay.textContent = `Xatolik: ${data.message}`;
                    // tg.showAlert(`Server xatoligi: ${data.message}`);
                    break;
                case "info":
                    systemMessageDisplay.textContent = data.message;
                    break;
                default:
                    console.warn("Noma'lum WebSocket xabar turi:", data.type);
            }
        } catch (e) {
            console.error("WebSocket xabarini parse qilishda xatolik:", e, "Xabar:", event.data);
        }
    };

    websocket.onclose = (event) => {
        console.log("WebSocket uzildi:", event.code, event.reason);
        gameStatusDisplay.textContent = "Aloqa uzildi.";
        rollDiceButton.disabled = true;
        clearMovablePieceHighlights();
        // Qayta ulanish logikasi (agar kerak bo'lsa)
        // setTimeout(connectWebSocket, 5000); // Masalan, 5 sekunddan keyin qayta urinish
    };

    websocket.onerror = (error) => {
        console.error("WebSocket xatoligi:", error);
        gameStatusDisplay.textContent = "WebSocket aloqasida xatolik.";
        // tg.showAlert("WebSocket aloqasida xatolik yuz berdi.");
    };
}

function updateUIWithGameState(gameState) {
    if (!gameState) {
        console.warn("updateUIWithGameState: gameState mavjud emas.");
        return;
    }
    currentGameState = gameState; // Global holatni yangilash

    gameStatusDisplay.textContent = gameState.status || "Noma'lum";
    diceValueDisplay.textContent = gameState.current_dice_roll || '-';

    const currentPlayerInfo = gameState.current_player_user_id ? gameState.players[gameState.current_player_user_id] : null;
    currentTurnPlayerDisplay.textContent = currentPlayerInfo ? `${currentPlayerInfo.first_name} (${currentPlayerInfo.user_id === currentUserId ? 'Siz' : currentPlayerInfo.user_id})` : '-';

    playersListUl.innerHTML = '';
    if (gameState.players && typeof gameState.players === 'object') {
        // player_order bo'yicha o'yinchilarni chiqarish (agar mavjud bo'lsa)
        const orderedPlayerIds = gameState.player_order && gameState.player_order.length > 0 ?
                                 gameState.player_order : Object.keys(gameState.players);

        orderedPlayerIds.forEach(playerId => {
            const player = gameState.players[playerId];
            if (!player) return;

            const li = document.createElement('li');
            const colorIndicator = document.createElement('span');
            colorIndicator.classList.add('player-color-indicator');
            if (player.color) {
                colorIndicator.style.backgroundColor = player.color;
                // colorIndicator.classList.add(`player-color-${player.color}`); // Agar CSS da ranglar klass orqali bo'lsa
            }

            let playerText = `${player.first_name}`;
            if (player.user_id === currentUserId) playerText += " (Siz)";
            if (player.user_id === gameState.host_id) playerText += " (Xost)";
            if (player.is_sleeping) { // game_logic.py da LudoPlayer.to_dict() da is_sleeping bo'lishi kerak
                playerText += " (Kutmoqda)";
                li.style.opacity = 0.5;
            }
            li.appendChild(colorIndicator);
            li.appendChild(document.createTextNode(playerText));
            playersListUl.appendChild(li);
        });
    }

    // Zar tashlash tugmasini sozlash
    if (gameState.status === 'playing' &&
        currentPlayerInfo &&
        currentPlayerInfo.user_id === currentUserId &&
        !currentPlayerInfo.is_sleeping &&
        gameState.current_dice_roll === null) {
        rollDiceButton.disabled = false;
    } else {
        rollDiceButton.disabled = true;
    }

    drawBoardElements(gameState);
}

rollDiceButton.addEventListener('click', () => {
    if (websocket && websocket.readyState === WebSocket.OPEN && !rollDiceButton.disabled) {
        console.log("Zar tashlash so'rovi yuborilmoqda...");
        websocket.send(JSON.stringify({ action: "roll_dice" }));
        rollDiceButton.disabled = true; // So'rov yuborilgach darhol o'chirish
    }
});

// function drawGameBoardAndPieces(gameState) {
//     gameBoardContainer.innerHTML = ''; // Eski toshlarni tozalash

//     if (!gameState || !gameState.players) {
//         console.warn("drawGameBoardAndPieces: gameState yoki gameState.players mavjud emas.");
//         return;
//     }

//     const piecesToDraw = [];
//     Object.values(gameState.players).forEach(player => {
//         if (player && player.pieces && Array.isArray(player.pieces)) {
//             player.pieces.forEach(pieceData => {
//                 piecesToDraw.push({ ...pieceData, playerColor: player.color });
//             });
//         }
//     });
    
//     // Bir xil pozitsiyadagi toshlarni guruhlash (keyinchalik ofset uchun)
//     const positionsMap = new Map();
//     piecesToDraw.forEach(p => {
//         if (p.position === null || p.position === undefined) return; // Pozitsiyasi yo'q toshlarni chizmaymiz
//         if (!positionsMap.has(p.position)) {
//             positionsMap.set(p.position, []);
//         }
//         positionsMap.get(p.position).push(p);
//     });


//     piecesToDraw.forEach(pieceData => {
//         const pieceElement = document.createElement('div');
//         pieceElement.classList.add('piece-on-board');
//         if (pieceData.playerColor) {
//             pieceElement.classList.add(`piece-color-${pieceData.playerColor}`); // e.g., piece-color-red
//             // Yoki to'g'ridan-to'g'ri style.backgroundColor = pieceData.playerColor;
//             pieceElement.style.backgroundColor = pieceData.playerColor;
//         }

//         // pieceElement.textContent = pieceData.id; // Tosh ID sini ko'rsatish (ixtiyoriy)
//         pieceElement.dataset.pieceId = pieceData.id;
//         pieceElement.dataset.ownerId = pieceData.player_id;

//         const stylePos = getPieceStylePosition(pieceData);
        
//         let finalLeft = stylePos.left;
//         let finalTop = stylePos.top;

//         // Bir xil pozitsiyadagi toshlar uchun ofset
//         const piecesInSameCell = positionsMap.get(pieceData.position) || [];
//         if (piecesInSameCell.length > 1) {
//             const pieceIndexInCell = piecesInSameCell.findIndex(p => p.id === pieceData.id && p.player_id === pieceData.player_id);
//             const { dxPercent, dyPercent } = calculateOffsetForStackedPieces(piecesInSameCell.length, pieceIndexInCell);
            
//             finalLeft = `${parseFloat(stylePos.left) + dxPercent}%`;
//             finalTop = `${parseFloat(stylePos.top) + dyPercent}%`;
//         }
        
//         pieceElement.style.left = finalLeft;
//         pieceElement.style.top = finalTop;

//         if (stylePos.display === 'none') {
//             pieceElement.style.display = 'none';
//         }

//         gameBoardContainer.appendChild(pieceElement);
//     });
// }


function drawBoardElements(gameState) {
    gameBoardContainer.innerHTML = ''; // Eski elementlarni tozalash (toshlar va ismlar)

    if (!gameState || !gameState.players) {
        console.warn("drawBoardElements: gameState yoki gameState.players mavjud emas.");
        return;
    }

    const piecesToDraw = [];
    Object.values(gameState.players).forEach(player => {
        if (player && player.pieces && Array.isArray(player.pieces)) {
            player.pieces.forEach(pieceData => {
                piecesToDraw.push({ ...pieceData, playerColor: player.color });
            });
        }

        // O'YINCHI ISMINI CHIZISH
        if (player && player.color && playerNameCoordinatesPercent[player.color]) {
            const nameElement = document.createElement('div');
            nameElement.classList.add('player-name-on-board');
            
            // Ismni qisqartirish (agar juda uzun bo'lsa)
            let displayName = player.first_name;
            if (displayName.length > 10) { // Masalan, 10 belgidan uzun bo'lsa
                displayName = displayName.substring(0, 8) + "..";
            }
            nameElement.textContent = displayName;
            
            const nameCoords = playerNameCoordinatesPercent[player.color];
            nameElement.style.top = nameCoords.top;
            nameElement.style.left = nameCoords.left;
            if (nameCoords.textAlign) {
                nameElement.style.textAlign = nameCoords.textAlign;
            }
            if (nameCoords.transform) { // Agar markazlashtirish kerak bo'lsa
                 nameElement.style.transform = nameCoords.transform;
            } else { // Agar left/top burchakni ko'rsatsa, transform kerak emas
                if (nameCoords.textAlign === 'right') {
                    nameElement.style.transform = 'translateX(-100%)'; // O'ng tomonga yopishish uchun
                } else if (nameCoords.textAlign === 'center') {
                    nameElement.style.transform = 'translateX(-50%)'; // Markazlash uchun
                }
            }


            // Rangiga qarab fon yoki chegara berish (ixtiyoriy)
            nameElement.style.borderColor = player.color;
            // nameElement.style.backgroundColor = player.color; // Agar shaffof fon o'rniga rangli fon kerak bo'lsa
            
            gameBoardContainer.appendChild(nameElement);
        }
    });
    
    // TOSHLARNI CHIZISH (mavjud kodingiz)
    const positionsMap = new Map();
    piecesToDraw.forEach(p => {
        if (p.position === null || p.position === undefined) return;
        if (!positionsMap.has(p.position)) {
            positionsMap.set(p.position, []);
        }
        positionsMap.get(p.position).push(p);
    });

    piecesToDraw.forEach(pieceData => {
        const pieceElement = document.createElement('div');
        pieceElement.classList.add('piece-on-board');
        if (pieceData.playerColor) {
            pieceElement.style.backgroundColor = pieceData.playerColor;
        }

        pieceElement.dataset.pieceId = pieceData.id;
        pieceElement.dataset.ownerId = pieceData.player_id;

        const stylePos = getPieceStylePosition(pieceData);
        
        let finalLeft = stylePos.left;
        let finalTop = stylePos.top;

        const piecesInSameCell = positionsMap.get(pieceData.position) || [];
        if (piecesInSameCell.length > 1 && stylePos.display !== 'none') { // Faqat ko'rinadigan toshlar uchun ofset
            const pieceIndexInCell = piecesInSameCell.findIndex(p => p.id === pieceData.id && p.player_id === pieceData.player_id);
            const { dxPercent, dyPercent } = calculateOffsetForStackedPieces(piecesInSameCell.length, pieceIndexInCell);
            
            finalLeft = `${parseFloat(stylePos.left) + dxPercent}%`;
            finalTop = `${parseFloat(stylePos.top) + dyPercent}%`;
        }
        
        pieceElement.style.left = finalLeft;
        pieceElement.style.top = finalTop;

        if (stylePos.display === 'none') {
            pieceElement.style.display = 'none';
        }

        gameBoardContainer.appendChild(pieceElement);
    });
}

function calculateOffsetForStackedPieces(totalPieces, pieceIndex) {
    // Bu funksiya bir katakdagi bir nechta tosh uchun kichik surilishni hisoblaydi
    // Masalan, ularni aylana shaklida yoki qator qilib joylashtirish mumkin
    if (totalPieces <= 1) return { dxPercent: 0, dyPercent: 0 };

    const maxOffset = 1.5; // Foizda, tosh o'lchamiga nisbatan
    let dxPercent = 0;
    let dyPercent = 0;

    // Oddiy gorizontal ofset misoli:
    const step = (totalPieces > 1) ? (maxOffset * 2 / (totalPieces - 1)) : 0;
    dxPercent = -maxOffset + (pieceIndex * step);
    // dyPercent = ... (vertikal uchun ham qilish mumkin)
    
    // Yana bir variant: kichik aylana bo'ylab joylashtirish
    const angle = (pieceIndex / totalPieces) * 2 * Math.PI;
    const radiusPercent = 1.0; // Kichik radius
    // dxPercent = Math.cos(angle) * radiusPercent;
    // dyPercent = Math.sin(angle) * radiusPercent;


    return { dxPercent, dyPercent };
}


function getPieceStylePosition(pieceData) {
    const piecePositionId = pieceData.position; // Bu `korBackend` dagi ID
    const pieceState = pieceData.state; // "home", "active", "safe", "finished"

    let coordsPercent;

    if (piecePositionId !== null && piecePositionId !== undefined && pieceCoordinatesPercent[piecePositionId.toString()]) {
        coordsPercent = pieceCoordinatesPercent[piecePositionId.toString()];
    }

    if (coordsPercent) {
        return { left: `${coordsPercent.x}%`, top: `${coordsPercent.y}%` };
    }

    // Agar koordinata topilmasa (masalan, backendda pozitsiya null bo'lsa yoki ID xato bo'lsa)
    console.warn(`Foizli koordinata topilmadi (ID: ${piecePositionId}, State: ${pieceState}):`, pieceData);
    return { left: '0%', top: '0%', display: 'none' }; // Yashirish
}

function handleValidMoves(validMovesMap) { // validMovesMap: { piece_id: [new_pos_id, new_state_str] }
    clearMovablePieceHighlights(); // Avvalgi yoritishlarni tozalash

    if (Object.keys(validMovesMap).length === 0 && currentGameState.current_dice_roll !== 6) {
        systemMessageDisplay.textContent = "Yurish uchun imkoniyat yo'q.";
        // Server avtomatik navbatni o'tkazishi kerak (agar 6 bo'lmasa)
        return;
    }
    if (Object.keys(validMovesMap).length === 0 && currentGameState.current_dice_roll === 6) {
        systemMessageDisplay.textContent = "6 tushdi, lekin yurish imkoniyati yo'q. Yana zar tashlang.";
        // Server navbatni o'tkazmasligi kerak, o'yinchi yana zar tashlaydi
        rollDiceButton.disabled = false; // Yana zar tashlash uchun tugmani yoqish
        return;
    }


    systemMessageDisplay.textContent = "Yurish uchun toshni tanlang.";

    Object.keys(validMovesMap).forEach(pieceIdStr => {
        const pieceId = parseInt(pieceIdStr);
        const pieceElement = gameBoardContainer.querySelector(`.piece-on-board[data-piece-id="${pieceId}"][data-owner-id="${currentUserId}"]`);
        if (pieceElement) {
            pieceElement.classList.add('movable');
            pieceElement.onclick = (event) => {
                event.stopPropagation();
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    console.log(`Tosh ${pieceId} tanlandi. So'rov yuborilmoqda...`);
                    websocket.send(JSON.stringify({ action: "move_piece", piece_id: pieceId }));
                    clearMovablePieceHighlights();
                    rollDiceButton.disabled = true; // Yurishdan keyin zarni o'chirish
                    systemMessageDisplay.textContent = "Yurish amalga oshirilmoqda...";
                }
            };
        }
    });
}

function clearMovablePieceHighlights() {
    const movablePieces = gameBoardContainer.querySelectorAll('.piece-on-board.movable');
    movablePieces.forEach(el => {
        el.classList.remove('movable');
        el.onclick = null;
    });
    // Zar tugmasi holatini updateUIWithGameState ichida boshqarish yaxshiroq
    if (currentGameState) { // Faqat currentGameState mavjud bo'lsa
      if (currentGameState.status === 'playing' &&
          currentGameState.current_player_user_id === currentUserId &&
          !currentGameState.players[currentUserId]?.is_sleeping &&
          currentGameState.current_dice_roll === null) {
          rollDiceButton.disabled = false;
      } else {
          rollDiceButton.disabled = true;
      }
    }
}

// Sahifani yopish/orqaga qaytishda WebSocketni yopish (ixtiyoriy)
window.addEventListener('beforeunload', () => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close();
    }
});