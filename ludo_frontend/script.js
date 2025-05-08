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
const gameBoardContainer = document.getElementById('game-board-container'); // O'yin maydoni uchun

// O'yin holati uchun global o'zgaruvchilar
let currentGameId = null;
let currentUserId = null;
let currentUsername = null; // Yoki first_name
let websocket = null;
let currentGameState = null;

// Mini App ishga tushganda
window.addEventListener('load', () => {
    tg.ready(); // Telegramga Mini App tayyorligini bildirish
    tg.expand(); // Mini Appni to'liq ekranga kengaytirish

    const initData = tg.initDataUnsafe;
    // console.log("Telegram Init Data:", initData);

    if (initData && initData.user) {
        currentUserId = initData.user.id;
        currentUsername = initData.user.first_name || initData.user.username || 'Foydalanuvchi';
        userIdDisplay.textContent = `${currentUsername} (${currentUserId})`;
    } else {
        console.error("Foydalanuvchi ma'lumotlari topilmadi!");
        gameStatusDisplay.textContent = "Xatolik: Foydalanuvchi ma'lumotlari yo'q.";
        alert("Telegram foydalanuvchi ma'lumotlarini olib bo'lmadi.");
        return;
    }

    // URL'dan game_id ni olish
    const urlParams = new URLSearchParams(window.location.search);
    currentGameId = urlParams.get('tgWebAppStartParam');

    console.log("registerOrGetGameInfo chaqirildi. Olingan currentGameId:", currentGameId); // <--- QO'SHING
    console.log("To'liq URL:", window.location.href); // <--- QO'SHING

    if (currentGameId) {
        gameIdDisplay.textContent = currentGameId;
        // O'yinga ro'yxatdan o'tish/ma'lumot olish
        registerOrGetGameInfo();
    } else {
        gameStatusDisplay.textContent = "Xatolik: O'yin ID topilmadi.";
        gameStatusDisplay.textContent = urlParams;
        alert("O'yin ID URL'da ko'rsatilmagan.");
    }
});

// Backend API manzili (o'zgartiring!)
// Agar GitHub Pages bilan birga lokal serverda (masalan, FastAPI) ishlatayotgan bo'lsangiz:
const API_BASE_URL = 'http://localhost:8000'; // Yoki sizning backend manzilingiz
const WS_BASE_URL = 'ws://localhost:8000';  // Yoki sizning WebSocket manzilingiz


const ETALON_BOARD_WIDTH = 512;
const ETALON_BOARD_HEIGHT = 512;
const CELL_SIZE = ETALON_BOARD_WIDTH / 15;

// Funktsiya: Katak indeksidan piksel koordinatasini olish
function getPixel(gridIndex) {
    return (gridIndex + 0.5) * CELL_SIZE;
}

const homeStartCoordinatesPx = {
    red: [ // piece_id 0, 1, 2, 3
        { x: getPixel(20.5), y: getPixel(10.75) }, { x: getPixel(12.5), y: getPixel(10.75) },
        { x: getPixel(10.5), y: getPixel(12.75) }, { x: getPixel(12.5), y: getPixel(12.75) }
    ],
    green: [
        { x: getPixel(1.5), y: getPixel(10.75) }, { x: getPixel(3.5), y: getPixel(10.75) },
        { x: getPixel(1.5), y: getPixel(12.75) }, { x: getPixel(3.5), y: getPixel(12.75) }
    ],
    yellow: [
        { x: getPixel(1.5), y: getPixel(1.75) }, { x: getPixel(3.5), y: getPixel(1.75) },
        { x: getPixel(1.5), y: getPixel(3.75) }, { x: getPixel(3.5), y: getPixel(3.75) }
    ],
    blue: [
        { x: getPixel(10.5), y: getPixel(1.75) }, { x: getPixel(12.5), y: getPixel(1.75) },
        { x: getPixel(10.5), y: getPixel(3.75) }, { x: getPixel(12.5), y: getPixel(3.75) }
    ],
};

const mainPathCoordinatesPx = [
    // Red Path Start (idx 0 to 12)
    { x: getPixel(8), y: getPixel(13) }, // 0 - Red Start
    { x: getPixel(8), y: getPixel(12) }, // 1
    { x: getPixel(8), y: getPixel(11) }, // 2
    { x: getPixel(8), y: getPixel(10) }, // 3
    { x: getPixel(8), y: getPixel(9) },  // 4
    { x: getPixel(8), y: getPixel(8) },  // 5 (Corner before turning left)
    { x: getPixel(7), y: getPixel(7) },  // 6 (Path towards center line)
    { x: getPixel(6), y: getPixel(7) },  // 7
    { x: getPixel(5), y: getPixel(7) },  // 8
    { x: getPixel(4), y: getPixel(7) },  // 9
    { x: getPixel(3), y: getPixel(7) },  // 10
    { x: getPixel(2), y: getPixel(7) },  // 11
    { x: getPixel(1), y: getPixel(7) },  // 12 (Corner before turning up for Green's path)

    // Green Path Start (idx 13 to 25)
    { x: getPixel(1), y: getPixel(6) },  // 13 - Green Start
    { x: getPixel(2), y: getPixel(6) },  // 14
    { x: getPixel(3), y: getPixel(6) },  // 15
    { x: getPixel(4), y: getPixel(6) },  // 16
    { x: getPixel(5), y: getPixel(6) },  // 17
    { x: getPixel(6), y: getPixel(6) },  // 18 (Corner before turning right)
    { x: getPixel(7), y: getPixel(5) },  // 19 (Path towards center line)
    { x: getPixel(7), y: getPixel(4) },  // 20
    { x: getPixel(7), y: getPixel(3) },  // 21
    { x: getPixel(7), y: getPixel(2) },  // 22
    { x: getPixel(7), y: getPixel(1) },  // 23
    { x: getPixel(7), y: getPixel(0) },  // 24 (Corner before turning right for Yellow's path)
    
    // Yellow Path Start (idx 26 to 38)
    { x: getPixel(6), y: getPixel(1) },  // 26 - Yellow Start
    { x: getPixel(6), y: getPixel(2) },  // 27
    { x: getPixel(6), y: getPixel(3) },  // 28
    { x: getPixel(6), y: getPixel(4) },  // 29
    { x: getPixel(6), y: getPixel(5) },  // 30
    { x: getPixel(6), y: getPixel(6) },  // 31 (Corner before turning right)
    { x: getPixel(7), y: getPixel(7) },  // 32 (Path towards center line) // Bu 6-katak bilan bir xil, bu xato
    // Yuqoridagi 6 va 19-kataklar markaziy yo'lakka kirish nuqtalari. 
    // Mantiqni qayta ko'rib chiqish kerak. Asosiy yo'l bir-birini kesib o'tmaydi.
    // Har bir rangning 13 ta katakdan iborat segmenti bor.
];

// YAXSHIROQ YONDASHUV: Har bir rang uchun asosiy yo'l segmentlarini alohida aniqlash
// va keyin ularni birlashtirish.
// Qizil uchun: (8,13) -> (8,8) -> (7,7) -> (6,7) -> (5,7) -> (4,7) -> (3,7) -> (2,7) -> (1,7) - 13 katak
// Yashil uchun: (1,6) -> (2,6) ... (6,6) -> (7,5) -> (7,4) ... (7,0) - 13 katak
// ...

// To'g'rilangan mainPathCoordinatesPx (ketma-ketlikda):
const correctedMainPathCoordsPx = [
    // Qizil segmenti (0-12)
    { x: getPixel(8), y: getPixel(13) }, /*0*/ { x: getPixel(8), y: getPixel(12) }, /*1*/ 
    { x: getPixel(8), y: getPixel(11) }, /*2*/ { x: getPixel(8), y: getPixel(10) }, /*3*/
    { x: getPixel(8), y: getPixel(9) },  /*4*/ { x: getPixel(8), y: getPixel(8) },   /*5*/
    { x: getPixel(7), y: getPixel(8) },  /*6*/ { x: getPixel(6), y: getPixel(8) },   /*7*/ // Chapga burilish
    { x: getPixel(6), y: getPixel(7) },  /*8*/ { x: getPixel(6), y: getPixel(6) },   /*9*/ // Yuqoriga
    { x: getPixel(6), y: getPixel(5) },  /*10*/{ x: getPixel(6), y: getPixel(4) },  /*11*/
    { x: getPixel(6), y: getPixel(3) },  /*12*/

    // Yashil segmenti (13-25)
    { x: getPixel(1), y: getPixel(6) },  /*13*/{ x: getPixel(2), y: getPixel(6) },  /*14*/
    { x: getPixel(3), y: getPixel(6) },  /*15*/{ x: getPixel(4), y: getPixel(6) },  /*16*/
    { x: getPixel(5), y: getPixel(6) },  /*17*/{ x: getPixel(6), y: getPixel(6) },  /*18 - BU YASHILNING 5-QADAMI, QIZILNING 12-QADAMI BILAN BIR XIL BO'LMASLIGI KERAK*/
    // XATO! Har bir rangning start pozitsiyasi uning o'z yo'lagida bo'lishi kerak.

    // == TO'G'RI YONDASHUV (ASOSIY YO'L UCHUN) ==
    // Yo'lni bir nuqtadan boshlab, 52 qadam davomida chizib chiqamiz.
    // Masalan, Qizilning startidan boshlab.
];

const mainPathCoordinatesFinalPx = [];
let currentXGrid = 8; let currentYGrid = 13; // Qizilning start katagi grid koordinatasi
let pathIndex = 0;

// 1. Qizilning vertikal yo'li (yuqoriga, 6 katak)
for (let i = 0; i < 6; i++) { mainPathCoordinatesFinalPx[pathIndex++] = { x: getPixel(currentXGrid), y: getPixel(currentYGrid - i) }; }
currentYGrid -= 5; // (8,8) ga keldi

// 2. Chapga burilish, gorizontal (chapga, 6 katak)
for (let i = 0; i < 6; i++) { mainPathCoordinatesFinalPx[pathIndex++] = { x: getPixel(currentXGrid - i), y: getPixel(currentYGrid) }; }
currentXGrid -= 5; // (3,8) ga keldi, lekin yo'l (2,8) da tugaydi, bu 6-qadam.
// 1-qadam (7,8), 2-qadam (6,8), 3-qadam (5,8), 4-qadam (4,8), 5-qadam (3,8), 6-qadam (2,8)
// Yo'q, bu ham xato. Burchaklar hisobga olinishi kerak.
// Har bir "L" shaklidagi segment 6+1+6 = 13 katak.
// Qizil: 5 yuqoriga, 1 chapga-yuqoriga, 5 chapga, 1 yuqoriga-chapga, ...

// Eng yaxshisi har bir katakni alohida yozib chiqish yoki juda aniq algoritm tuzish.
// Hozircha, sizga yuqoridagi Qizilning yo'li (0-12) mantiqini davom ettirib,
// qolgan ranglar uchun ham shunday 13 ta katakdan iborat segmentlarni topishingizni
// va ularni `mainPathCoordinatesPx` massiviga qo'shishingizni tavsiya qilaman.

const homePathCoordinatesPx = {
    red: [ // piece_steps_taken 1 to 5
        { x: getPixel(8), y: getPixel(7) }, { x: getPixel(9), y: getPixel(7) },
        { x: getPixel(10), y: getPixel(7) }, { x: getPixel(11), y: getPixel(7) },
        { x: getPixel(12), y: getPixel(7) }
    ],
    green: [
        { x: getPixel(7), y: getPixel(8) }, { x: getPixel(7), y: getPixel(9) },
        { x: getPixel(7), y: getPixel(10) }, { x: getPixel(7), y: getPixel(11) },
        { x: getPixel(7), y: getPixel(12) }
    ],
    yellow: [
        { x: getPixel(6), y: getPixel(7) }, { x: getPixel(5), y: getPixel(7) },
        { x: getPixel(4), y: getPixel(7) }, { x: getPixel(3), y: getPixel(7) },
        { x: getPixel(2), y: getPixel(7) }
    ],
    blue: [
        { x: getPixel(7), y: getPixel(6) }, { x: getPixel(7), y: getPixel(5) },
        { x: getPixel(7), y: getPixel(4) }, { x: getPixel(7), y: getPixel(3) },
        { x: getPixel(7), y: getPixel(2) }
    ],
};

const finishCoordinatesPx = {
    red: { x: getPixel(13), y: getPixel(7) },
    green: { x: getPixel(7), y: getPixel(13) },
    yellow: { x: getPixel(1), y: getPixel(7) },
    blue: { x: getPixel(7), y: getPixel(1) },
};

// FOIZGA O'TKAZISH UCHUN FUNKSIYA
function toPercent(coordsPx) {
    if (Array.isArray(coordsPx)) {
        return coordsPx.map(coord => ({
            x: parseFloat(((coord.x / ETALON_BOARD_WIDTH) * 100).toFixed(2)),
            y: parseFloat(((coord.y / ETALON_BOARD_HEIGHT) * 100).toFixed(2)),
        }));
    } else if (typeof coordsPx === 'object' && coordsPx !== null) {
         if (coordsPx.x !== undefined && coordsPx.y !== undefined) { // Agar {x,y} obyekt bo'lsa
            return {
                x: parseFloat(((coordsPx.x / ETALON_BOARD_WIDTH) * 100).toFixed(2)),
                y: parseFloat(((coordsPx.y / ETALON_BOARD_HEIGHT) * 100).toFixed(2)),
            };
        } else { // Agar ranglar bo'yicha obyekt bo'lsa (masalan, homeStartCoordinatesPx)
            const percentObj = {};
            for (const key in coordsPx) {
                percentObj[key] = toPercent(coordsPx[key]);
            }
            return percentObj;
        }
    }
    return coordsPx; // Agar boshqa turdagi ma'lumot bo'lsa
}


// FOIZLI KOORDINATALAR (BULARNI ISHLATASIZ)
const homeStartCoordinatesPercent = toPercent(homeStartCoordinatesPx);
// const mainPathCoordinatesPercent = toPercent(mainPathCoordinatesFinalPx); // TO'LDIRILMAGAN
const homePathCoordinatesPercent = toPercent(homePathCoordinatesPx);
const finishCoordinatesPercent = toPercent(finishCoordinatesPx);

// TODO: mainPathCoordinatesFinalPx ni to'liq to'ldiring va keyin foizga o'tkazing!
// Hozircha mainPathCoordinatesPercent bo'sh qoladi yoki taxminiy qiymatlar bilan to'ldiriladi.
// Test uchun bir nechta qo'lda kiritilgan foizli qiymatlar:
const mainPathCoordinatesPercent = [
    // Bu juda taxminiy, siz o'zingiznikini aniq hisoblashingiz kerak!
    // Red (0-12)
    {x: 56.64, y: 89.84}, {x: 56.64, y: 83.4}, {x: 56.64, y: 76.95}, {x: 56.64, y: 70.51}, {x: 56.64, y: 64.06}, {x: 56.64, y: 57.62}, // 0-5
    {x: 50.0, y: 56.64}, {x: 43.36, y: 56.64}, // 6-7
    {x: 36.91, y: 56.64}, {x: 30.47, y: 56.64}, {x: 24.02, y: 56.64}, {x: 17.58, y: 56.64}, {x: 11.13, y: 56.64}, // 8-12
    // Green (13-25)
    {x: 10.16, y: 56.64}, {x: 10.16, y: 50.0}, {x: 10.16, y: 43.36}, {x: 10.16, y: 36.91}, {x: 10.16, y: 30.47}, {x: 10.16, y: 24.02},
    {x: 17.58, y: 10.16}, {x: 24.02, y: 10.16},
    {x: 30.47, y: 10.16}, {x: 36.91, y: 10.16}, {x: 43.36, y: 10.16}, {x: 50.0, y: 10.16}, {x: 56.64, y: 10.16},
    // Yellow (26-38)
    {x: 56.64, y: 10.16}, {x: 63.09, y: 10.16}, {x: 69.53, y: 10.16}, {x: 75.98, y: 10.16}, {x: 82.42, y: 10.16}, {x: 88.87, y: 10.16},
    {x: 89.84, y: 17.58}, {x: 89.84, y: 24.02},
    {x: 89.84, y: 30.47}, {x: 89.84, y: 36.91}, {x: 89.84, y: 43.36}, {x: 89.84, y: 50.0}, {x: 89.84, y: 56.64},
    // Blue (39-51)
    {x: 88.87, y: 56.64}, {x: 82.42, y: 56.64}, {x: 75.98, y: 56.64}, {x: 69.53, y: 56.64}, {x: 63.09, y: 56.64}, {x: 56.64, y: 56.64},
    {x: 50.0, y: 63.09}, {x: 50.0, y: 69.53},
    {x: 50.0, y: 75.98}, {x: 50.0, y: 82.42}, {x: 50.0, y: 88.87}, {x: 50.0, y: 89.84}, {x: 56.64, y: 89.84} // Bu 0-katak bilan bir xil
];
// `mainPathCoordinatesPercent` ni to'g'rilash kerak. Yuqoridagi qiymatlar faqat taxminiy.


// script.js dagi getPiecePixelPosition funksiyasini getPieceStylePosition ga o'zgartiring
// va foizli koordinatalarni ishlating.
function getPieceStylePosition(pieceData, playerColorName) {
    const pieceState = pieceData.state;
    const piecePosition = pieceData.position;
    const pieceStepsTaken = pieceData.steps_taken;
    const pieceId = pieceData.id;

    let coordsPercent;

    if (pieceState === 'home') {
        if (homeStartCoordinatesPercent[playerColorName] && homeStartCoordinatesPercent[playerColorName][pieceId]) {
            coordsPercent = homeStartCoordinatesPercent[playerColorName][pieceId];
        }
    } else if (pieceState === 'active' || pieceState === 'safe') {
        if (piecePosition !== null && mainPathCoordinatesPercent[piecePosition]) {
            coordsPercent = mainPathCoordinatesPercent[piecePosition];
        } else if (piecePosition === null && pieceStepsTaken > 0 && pieceStepsTaken <= homePathCoordinatesPercent[playerColorName].length) {
            // Uy yo'lida (marraga yetmagan)
             if (homePathCoordinatesPercent[playerColorName] && homePathCoordinatesPercent[playerColorName][pieceStepsTaken - 1]) {
                coordsPercent = homePathCoordinatesPercent[playerColorName][pieceStepsTaken - 1];
            }
        }
    } else if (pieceState === 'finished') {
        if (finishCoordinatesPercent[playerColorName]) {
            coordsPercent = finishCoordinatesPercent[playerColorName];
        }
    }

    if (coordsPercent) {
        return { left: `${coordsPercent.x}%`, top: `${coordsPercent.y}%` };
    }
    console.warn(`Foizli koordinata topilmadi:`, pieceData, playerColorName);
    return { left: '-1000px', top: '-1000px' }; // Yoki display: 'none'
}







async function registerOrGetGameInfo() {
    if (!currentGameId || !currentUserId) {
        console.error("registerOrGetGameInfo: currentGameId yoki currentUserId mavjud emas.");
        gameStatusDisplay.textContent = "Xatolik: Kerakli ma'lumotlar topilmadi.";
        return;
    }

    gameStatusDisplay.textContent = "O'yinga qo'shilmoqda...";
    systemMessageDisplay.textContent = ""; // Eski xabarlarni tozalash

    try {
        // 1. O'yinga ro'yxatdan o'tish yoki o'yinchi ma'lumotlarini yangilash
        console.log(`O'yin ${currentGameId} ga o'yinchi ${currentUserId} (${currentUsername}) ni ro'yxatdan o'tkazishga urinilmoqda...`);
        const registerResponse = await fetch(`${API_BASE_URL}/games/${currentGameId}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Agar backendda Telegram initData ni tekshirish kerak bo'lsa, uni ham yuboring
                // 'X-Telegram-Init-Data': tg.initData // Misol uchun
            },
            body: JSON.stringify({
                user_id: currentUserId,
                first_name: currentUsername,
                username: tg.initDataUnsafe?.user?.username // Agar backendda kerak bo'lsa
            }),
        });

        const responseData = await registerResponse.json(); // Javobni har doim o'qishga harakat qilish

        if (registerResponse.ok) {
            console.log("Ro'yxatdan o'tish/qo'shilish muvaffaqiyatli:", responseData);
            // Odatda bu yerda serverdan o'yinning joriy holati keladi
            if (responseData) {
                currentGameState = responseData; // responseData GameBaseAPI formatida bo'lishi kerak
                updateUIWithGameState(currentGameState);
            }
        } else {
            // Ro'yxatdan o'tishda kutilgan xatoliklar (masalan, o'yin to'lgan, o'yin boshlangan)
            // yoki kutilmagan xatoliklar.
            console.warn(`Ro'yxatdan o'tishda xatolik yuz berdi. Status: ${registerResponse.status}`, responseData);
            if (responseData && responseData.detail) {
                systemMessageDisplay.textContent = `Server xabari: ${responseData.detail}`;
            } else {
                systemMessageDisplay.textContent = `Ro'yxatdan o'tishda noma'lum xatolik (status: ${registerResponse.status}).`;
            }
            // Agar ro'yxatdan o'tishda jiddiy xatolik bo'lsa (masalan, 404 - o'yin umuman topilmadi),
            // WebSocket'ga ulanmaslik mumkin. Lekin ko'p holatlarda (400, 409)
            // o'yinchi allaqachon mavjud yoki o'yin boshqa holatda bo'lishi mumkin,
            // bu holatda WebSocket'ga ulanib, joriy holatni olishga harakat qilish mumkin.
            if (registerResponse.status === 404) {
                 gameStatusDisplay.textContent = `Xatolik: O'yin (${currentGameId}) topilmadi.`;
                 alert(`O'yin ${currentGameId} serverda topilmadi. Iltimos, bot orqali qayta urinib ko'ring.`);
                 return; // WebSocket'ga ulanmaymiz
            }
             // Agar o'yin to'lgan (masalan, 400 "O'yin to'lgan") yoki boshqa holat bo'lsa,
             // UI da buni ko'rsatib, WebSocket'ga ulanishga harakat qilishimiz mumkin (faqat kuzatish uchun)
             // yoki shu yerda to'xtatishimiz mumkin.
             // Hozircha, xatolik bo'lsa ham WSga ulanishga harakat qilamiz, chunki WS endpoint
             // o'z tekshiruvlarini qiladi.
        }

        // 2. WebSocket'ga ulanish
        // Ro'yxatdan o'tish natijasidan qat'iy nazar (agar 404 bo'lmasa) WS ga ulanamiz,
        // chunki WS endpointi o'yinchining o'yinda bor yoki yo'qligini o'zi tekshiradi.
        connectWebSocket();

    } catch (error) {
        console.error("registerOrGetGameInfo funksiyasida umumiy xatolik:", error);
        gameStatusDisplay.textContent = `Xatolik: ${error.message}`;
        systemMessageDisplay.textContent = `Tizim xatoligi: ${error.message}. Iltimos, sahifani yangilang.`;
        // alert(`Kutilmagan xatolik: ${error.message}`);
    }
}


function connectWebSocket() {
    if (!currentGameId || !currentUserId) return;

    const wsUrl = `${WS_BASE_URL}/ws/${currentGameId}/${currentUserId}`;
    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log("WebSocket ulandi!");
        gameStatusDisplay.textContent = "Ulanildi. O'yin kutilmoqda...";
        // Ulanishdan so'ng server odatda "connection_ack" bilan birga o'yin holatini yuboradi
    };

    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("WebSocket'dan xabar:", data);
        currentGameState = data.game_state; // Joriy o'yin holatini saqlash

        if (data.type === "connection_ack") {
            systemMessageDisplay.textContent = data.message;
            if (data.game_state) updateUIWithGameState(data.game_state);
        } else if (data.type === "player_joined" || data.type === "game_started" || data.type === "game_started_manually" || data.type === "piece_moved" || data.type === "next_turn" || data.type === "player_state_changed") {
            if (data.game_state) updateUIWithGameState(data.game_state);
            if (data.type === "player_joined") systemMessageDisplay.textContent = `O'yinchi qo'shildi.`;
            if (data.type === "game_started" || data.type === "game_started_manually") systemMessageDisplay.textContent = "O'yin boshlandi!";
        } else if (data.type === "dice_rolled") {
            if (data.game_state) updateUIWithGameState(data.game_state); // Dice value ham game_state da bo'ladi
            systemMessageDisplay.textContent = `O'yinchi ${data.rolled_by_user_id} zar ${data.dice_value} tashladi.`;
            // TODO: Valid moves ni ko'rsatish (data.valid_moves)
            handleValidMoves(data.valid_moves);
        } else if (data.type === "game_finished") {
            if (data.game_state) updateUIWithGameState(data.game_state);
            systemMessageDisplay.textContent = `O'yin tugadi! G'olib: ${data.winner_user_id}.`;
            rollDiceButton.disabled = true;
        } else if (data.type === "error") {
            systemMessageDisplay.textContent = `Xatolik: ${data.message}`;
            console.error("Serverdan xatolik:", data.message);
        } else if (data.type === "info") {
            systemMessageDisplay.textContent = `Info: ${data.message}`;
        }
    };

    websocket.onclose = (event) => {
        console.log("WebSocket uzildi:", event);
        gameStatusDisplay.textContent = "Aloqa uzildi.";
        rollDiceButton.disabled = true;
        // Qayta ulanish logikasini qo'shish mumkin
    };

    websocket.onerror = (error) => {
        console.error("WebSocket xatoligi:", error);
        gameStatusDisplay.textContent = "WebSocket aloqasida xatolik.";
    };
}


function updateUIWithGameState(gameState) {
    if (!gameState) return;
    currentGameState = gameState; // globalni yangilash

    gameStatusDisplay.textContent = gameState.status;
    diceValueDisplay.textContent = gameState.current_dice_roll || '-';
    
    const currentPlayerFromState = gameState.players[gameState.current_player_user_id];
    currentTurnPlayerDisplay.textContent = currentPlayerFromState ? `${currentPlayerFromState.first_name} (${currentPlayerFromState.user_id})` : '-';

    playersListUl.innerHTML = ''; 
    Object.values(gameState.players).forEach(player => {
        const li = document.createElement('li');
        const colorIndicator = document.createElement('span');
        colorIndicator.classList.add('player-color-indicator');
        if (player.color) {
            colorIndicator.style.backgroundColor = player.color;
        }
        li.appendChild(colorIndicator);
        
        let playerText = `${player.first_name} (${player.user_id})`;
        if (player.user_id === gameState.host_id) playerText += " (Xost)";
        if (player.user_id === currentUserId) playerText += " (Siz)";
        // 'is_active' backenddan to'g'ri kelishiga ishonch hosil qiling (PlayerInGameAPI)
        const ludoPlayer = gameState.players[player.user_id]; // Bu gameState.players ichidagi player
        if (ludoPlayer && !ludoPlayer.is_active) { // is_active Pydantic modeldan keladi
            playerText += " (Kutmoqda)";
            li.style.opacity = 0.6;
        }
        
        li.appendChild(document.createTextNode(playerText));
        playersListUl.appendChild(li);
    });

    if (gameState.status === 'playing' && gameState.current_player_user_id === currentUserId) {
        rollDiceButton.disabled = false;
    } else {
        rollDiceButton.disabled = true;
    }

    drawGameBoard(gameState); // O'yin maydonini har safar yangilash
}

// Zar tashlash tugmasi bosilganda
rollDiceButton.addEventListener('click', () => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ action: "roll_dice" }));
        rollDiceButton.disabled = true; // Xabarni yuborgandan so'ng darhol o'chirish
    }
});

function handleValidMoves(validMoves) {
    console.log("Mumkin bo'lgan yurishlar:", validMoves);
    systemMessageDisplay.textContent = "Yurish uchun toshni tanlang.";
    clearMovablePieceHandlers(); // Avvalgi handlerlarni tozalash

    const pieceElements = gameBoardContainer.querySelectorAll('.piece-on-board');
    pieceElements.forEach(pieceElement => {
        const pieceId = parseInt(pieceElement.dataset.pieceId);
        const ownerPlayerId = parseInt(pieceElement.dataset.ownerId); // Tosh egasining IDsi

        if (ownerPlayerId === currentUserId && validMoves && validMoves.hasOwnProperty(pieceId)) {
            pieceElement.classList.add('movable');
            pieceElement.onclick = (event) => {
                event.stopPropagation(); // Boshqa clicklarga xalaqit bermaslik uchun
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    console.log(`Tosh ${pieceId} tanlandi.`);
                    websocket.send(JSON.stringify({ action: "move_piece", piece_id: pieceId }));
                    clearMovablePieceHandlers();
                    rollDiceButton.disabled = true; // Yurishdan keyin zarni o'chirish
                }
            };
        }
    });
}

function clearMovablePieceHandlers() {
    const piecesOnBoard = gameBoardContainer.querySelectorAll('.piece.movable');
    piecesOnBoard.forEach(pieceElement => {
        pieceElement.classList.remove('movable');
        pieceElement.onclick = null;
    });
    if (currentGameState && currentGameState.status === 'playing' && 
        currentGameState.current_player_user_id === currentUserId && 
        currentGameState.current_dice_roll === null) {
            rollDiceButton.disabled = false;
    } else {
            rollDiceButton.disabled = true;
    }
}


function drawGameBoard(gameState) {
    gameBoardContainer.innerHTML = ''; // Eskisini tozalash

    if (!gameState || !gameState.players) {
        console.warn("drawGameBoard: gameState yoki gameState.players mavjud emas.");
        return;
    }

    Object.values(gameState.players).forEach(player => {
        if (!player || !player.pieces || !Array.isArray(player.pieces)) {
            console.warn(`drawGameBoard: O'yinchi ${player ? player.user_id : 'N/A'} uchun 'pieces' topilmadi.`);
            return; 
        }

        const playerColorName = player.color; 

        player.pieces.forEach(pieceData => {
            const pieceElement = document.createElement('div');
            pieceElement.classList.add('piece-on-board');
            
            if (playerColorName) {
                pieceElement.classList.add(`piece-color-${playerColorName}`);
            } else {
                pieceElement.style.backgroundColor = 'grey'; 
            }

            pieceElement.textContent = `${pieceData.id}`;

            pieceElement.dataset.pieceId = pieceData.id;
            pieceElement.dataset.ownerId = player.user_id; 

            // Toshning pozitsiyasini o'rnatish (FOIZLI KOORDINATALAR BILAN)
            const stylePos = getPieceStylePosition(pieceData, playerColorName); // <--- O'ZGARTIRILDI
            pieceElement.style.left = stylePos.left; // left: "X.XX%"
            pieceElement.style.top = stylePos.top;   // top:  "Y.YY%"
            
            // Agar tosh yashirin bo'lishi kerak bo'lsa 
            if (stylePos.left === '-1000px') { // getPieceStylePosition dan qaytgan maxsus qiymat
                pieceElement.style.display = 'none';
            }

            gameBoardContainer.appendChild(pieceElement);
        });
    });
}

// TODO:
// 1. `registerOrGetGameInfo`: Bu funksiya o'yinchi allaqachon o'yinda yoki yo'qligini
//    aniqroq tekshirishi va shunga qarab harakat qilishi kerak. Hozir u faqat
//    WS ga ulanishga harakat qiladi. Agar o'yinchi o'yinda bo'lmasa, WS ulanishi
//    backend tomonidan rad etiladi.
//    Ideal holatda, Mini App ochilganda, agar o'yinchi o'yinda bo'lmasa,
//    `/games/{game_id}/register` endpointiga POST so'rov yuborilishi kerak.
//    Buni Telegram `initData` ni tekshirish orqali qilish mumkin.
//
// 2. `drawGameBoard`: Haqiqiy Ludo o'yin maydonini (kataklar, ranglar, toshlar)
//    chizadigan funksiyani implementatsiya qilish. Bu eng ko'p vaqt oladigan qism bo'lishi mumkin.
//    SVG yoki HTML div elementlaridan foydalanishingiz mumkin.
//
// 3. `handleValidMoves`: Foydalanuvchiga qaysi toshlarni yurishi mumkinligini
//    grafik tarzda ko'rsatish (masalan, toshlarni yoritish, atrofiga chegara chizish).
//    Va tosh tanlanganda `move_piece` xabarini yuborish. Hozirgi implementatsiya
//    `.piece` klassiga ega elementlarni qidiradi, bu elementlar `drawGameBoard` da yaratilishi kerak.
//
// 4. CSS stillarini yaxshilash.