import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile, BufferedInputFile
from models import *
import json
from postoimg import pos2img
from io import BytesIO
import asyncio
import random
from aiogram.filters import CommandStart, Command
from os import getenv
from aiogram.enums import ParseMode
import sys

TOKEN = "6888564755:AAH6Rej8KPHEqTTgmDZE2T4acn2C_pBeB4o"

bot = Bot(TOKEN)
dp = Dispatcher()

cards = ['🟥', '🟩', '🟨', '🟦']
stns = {
    1:'♠️',
    2:'♥️',
    3:'♣️',
    4:'♦️'
}




async def send_board(chat_id):
    group = session.query(Group).filter_by(chat_id=chat_id).first()
    players_names = [(await bot.get_chat_member(chat_id=chat_id, user_id=id)).user.first_name for id in group.get_players()]
    board = pos2img(group.get_positions(), players_names)
    image_bytes = BytesIO()
    board.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    text = ''
    players = group.get_players()
    for i in range(4):
        text += f'\n[{cards[i]} {((await bot.get_chat_member(chat_id=group.chat_id, user_id=group.get_players()[i])).user.first_name)[:30]}](tg://user?id={group.get_players()[i]})'
    await bot.send_photo(chat_id=chat_id, photo=BufferedInputFile(file=image_bytes.getvalue(), filename='image.png'), caption=text, parse_mode='Markdown')


async def send_zarik(chat_id):
    group = session.query(Group).filter_by(chat_id=chat_id).first()
    zarik_button = InlineKeyboardButton(text='🎲', callback_data='zarik')
    zarik_msg = await bot.send_message(chat_id=chat_id, text=f'[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=chat_id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]}) zarik taslań', parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[zarik_button]]))
    group.button_clicked = zarik_msg.message_id
    session.commit()
    await asyncio.sleep(30)
    if group.button_clicked == zarik_msg.message_id:
        await zarik_msg.edit_text(text=f'[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=chat_id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]}) uyqlap qalǵan 😴', parse_mode='Markdown')
        group.sleeps += 1
        group.next_quewe()
        session.commit()
        if group.sleeps == 5:
            group.game = False
            group.players = None
            group.positions = None
            group.dice = None
            group.queue = None
            group.sleeps = 0
            session.commit()
            await bot.send_message(chat_id=chat_id, text='Oyın toqtatıldı, oyınshılarımızǵa qayırlı tún tilep qalamız\n\nOyındı baslaw ushın /game buyrıǵınan paydalanıń')
            return   

        await send_zarik(chat_id)

async def send_stones(chat_id, stones, dice, allow_stones):
    group = session.query(Group).filter_by(chat_id=chat_id).first()
    stones_msg = await bot.send_message(chat_id=chat_id, text=f'[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=chat_id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]}) sizge {dice} tústi\n\nqaysı tastı júremiz?', parse_mode="Markdown", reply_markup=stones)
    group.button_clicked = stones_msg.message_id
    session.commit()
    await asyncio.sleep(60)
    if group.button_clicked == stones_msg.message_id:
        await stones_msg.edit_text(text=f'[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=chat_id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]}) uyqlap qalǵan 😴', parse_mode='Markdown')
        group.next_quewe()
        session.commit()
        await send_zarik(chat_id)



@dp.message(CommandStart())
async def start_bot(message: types.Message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        group = session.query(Group).filter_by(chat_id=message.chat.id).first()
        if group:
            if group.game or group.reg_id:
                await message.delete()
                return
        else:
            new_group = Group(chat_id=message.chat.id, game=False)
            session.add(new_group)
            session.commit()
        await message.answer("Sálem, bul Ludo Kar oyını.\nOyındı baslaw ushın /game buyrıǵınan paydalanıń")
        try:
            await message.delete()
        except:
            pass
        return
    
    
    btn1 = InlineKeyboardButton(text="Bottı gruupaǵa qosıw", url="https://t.me/LudoKarBot?startgroup=true")
    btn2 = InlineKeyboardButton(text="Gruppada oynaw", url="https://t.me/ludo_kar")
    btns = InlineKeyboardMarkup(inline_keyboard=[[btn1], [btn2]])
    await message.answer("Sálem, bul Ludo Kar oyını", reply_markup=btns)
    user = session.query(User).filter_by(user_id=message.chat.id).first()
    if not user:
        new_user = User(user_id=message.chat.id)
        session.add(new_user)
        session.commit()


@dp.message(Command('game'))
async def start_reg(message: types.Message):
    chat_member = await bot.get_chat_member(message.chat.id, bot.id)
    if message.chat.type == 'private':
        await message.reply("Bul buyrıq tek ǵana gruppalarda isleydi")
        return
    if chat_member.status != 'administrator':
        await message.reply('Oyındı baslaw ushın maǵan admin beriń!')
        return
    try:
        await message.delete()
    except:
        await message.reply('Oyındı baslaw ushın maǵan xabarlardı óshire alıw imkaniyatın beriń!')
        return

    group = session.query(Group).filter_by(chat_id=message.chat.id).first()
    if not group:
        return


    if group.reg_id or group.game:
        return
    
    join_btn = InlineKeyboardButton(text='Qosılıw', callback_data='join')
    reg_msg = await message.answer("Dizimnen ótiw dawam etpekte", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[join_btn]]))
    await reg_msg.pin()
    group.reg_id = reg_msg.message_id
    group.button_clicked = reg_msg.message_id
    session.commit()
    await asyncio.sleep(120)
    if group.button_clicked == reg_msg.message_id:
        await reg_msg.edit_text(text='Dizimnen ótiw qaldırıldı.\nOyındı baslaw ushın /game buyrıǵınan paydalanıń')
        await reg_msg.unpin()
        group.reg_id = None
        group.players = None
        group.game = False
        group.button_clicked = None
        session.commit()


@dp.message(Command('stop'))
async def stop_reg(message: types.Message):
    if message.chat.type == 'private':
        await message.reply("Bul buyrıq tek ǵana gruppalarda isleydi")
        return
    group = session.query(Group).filter_by(chat_id=message.chat.id).first()
    if message.from_user.id not in group.get_players():
        await message.delete()
        return
    if group.reg_id:
        await bot.delete_message(message.chat.id, group.reg_id)
    group.game = False
    group.players = None
    group.positions = None
    group.dice = None
    group.queue = None
    group.sleeps = 0
    group.reg_id = None
    group.button_clicked = None
    session.commit()
    await message.answer(f'[{message.from_user.first_name}](tg://user?id={message.from_user.id}) oyındı toqtattı.\n\nOyındı baslaw ushın /game buyrıǵınan paydalanıń', parse_mode='Markdown')
    await message.delete()

@dp.message(Command('toplist'))
async def top_list(message: types.Message):
    await message.delete()
    group = session.query(Group).filter_by(chat_id=message.chat.id).first()
    if group and group.game:
        return
    if message.chat.type == 'private':
        await message.reply("Bul buyrıq tek ǵana gruppalarda isleydi")
        return
    players = session.query(Player).filter_by(chat_id=message.chat.id).order_by(Player.win.desc()).limit(30).all()
    if len(players) == 0:
        return
    text = 'Top oyınshılar dizimi:\n\n'
    for i, player in enumerate(players, 1):
        try:
            text += f'{i}. [{((await bot.get_chat_member(chat_id=message.chat.id, user_id=player.player_id)).user.first_name)[:30]}](tg://user?id={player.player_id}) - {player.win}\n'
        except:
            text += f'{i}. Belgisiz oyınshı - {player.win}\n'
    
    await message.answer(text, parse_mode='Markdown')

@dp.message(Command('stat'))
async def stat(message: types.Message): 
    users = session.query(User).all()    
    groups = session.query(Group).all()
    for gr in groups:
        try:
            await bot.get_chat_member(chat_id=gr.chat_id, user_id=bot.id)
        except:
            session.delete(gr)
            session.commit()
    await message.reply(f'Statistika:\nGruppalar sanı - {len(session.query(Group).all())}\nPaydalanıwshılar sanı - {len(users)}')

@dp.callback_query()
async def join_game(query: types.CallbackQuery):    
    group = session.query(Group).filter_by(chat_id=query.message.chat.id).first()
    if query.data == 'join':
        if group.reg_id and not group.game:
            if query.from_user.id in group.get_players():
                await bot.answer_callback_query(query.id, text="Siz oyındasız!", show_alert=True)
                return
            group.add_player(query.from_user.id)
            session.commit()
        
            players = ', '.join(["["+((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=id)).user.first_name)[:30]+"](tg://user?id="+str(id)+")" for id in group.get_players()])
            join_btn = InlineKeyboardButton(text='Qosılıw', callback_data='join')
            await bot.edit_message_text(chat_id=query.message.chat.id, message_id=group.reg_id, text=f'Dizimnen ótiw dawam etpekte\n{players}', parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[join_btn]]))
            if len(group.get_players()) == 4:
                await bot.send_message(chat_id=query.message.chat.id, text='Oyın baslandı')
                await bot.delete_message(chat_id=query.message.chat.id, message_id=group.reg_id)
                group.game = True
                group.reg_id = None
                group.queue = 1
                group.sleeps = 0
                group.button_clicked = None

                chpos = []
                positions = []
                pos = []
                while True:
                    p = random.randint(17, 67)
                    if p in (29,42,55,22,35,48,61) or p in chpos:
                        continue
                    pos.append(p)
                    chpos.append(p)
                    if len(pos) == 4:
                        positions.append(pos)
                        pos = []
                    if len(positions) == 4:
                        break
                
                positions = [[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]]
                #positions = [[62,63,64,65],[23,24,25,26],[36,37,38,39],[49,50,51,52]]
                group.positions = json.dumps(positions)
                session.commit()
                await send_board(query.message.chat.id)
                await asyncio.sleep(10)
                await send_zarik(query.message.chat.id)
                
    elif query.data == 'zarik':
        if query.from_user.id != group.get_players()[group.queue-1]:
            await bot.answer_callback_query(query.id, text="Bul knopka siz ushın emes!", show_alert=True)
            return
        
        group.button_clicked = None
        group.sleeps = 0
        session.commit()
        await bot.edit_message_reply_markup(chat_id=query.message.chat.id, message_id=query.message.message_id, reply_markup=None)
        dice = (await bot.send_dice(chat_id=query.message.chat.id)).dice.value
        await asyncio.sleep(5)
        allow_stones = group.check_stone(dice)
        session.commit()
        if len(allow_stones) != 0:
            if len(allow_stones) == 1:
                text = f'[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]}) {stns[allow_stones[0]]} tasın júrdi'
                data = group.forward(int(allow_stones[0]))
                await bot.send_message(chat_id=query.message.chat.id, text=text, parse_mode='Markdown')
                if data[0] == 'back':
                    text = f'[{cards[data[1]]} {((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=group.get_players()[data[1]])).user.first_name)[:30]}](tg://user?id={group.get_players()[data[1]]}) sizdiń {stns[data[2]]} tasıńız izge qayttı'
                    await bot.send_message(chat_id=query.message.chat.id, text=text, parse_mode='Markdown')
                await send_board(query.message.chat.id)
                await asyncio.sleep(10)
                if data == 'win':
                    rek_messages = await bot.get_chat(chat_id=-1002009816777)
                    last_message = rek_messages.pinned_message
                    if last_message:
                        await bot.forward_message(query.message.chat.id, -1002009816777, last_message.message_id)
                    
                    winner_id = group.get_players()[group.queue-1]
                    text = 'Oyın tamam boldı!\n\nJeńimpaz: '
                    text += f'\n[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]})'
                    text += '\n\nQalǵan oyınshılar:'
                    for i in range(3):
                        group.next_quewe()
                        text += f'\n[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]})'
                    text += '\n\nOyındı baslaw ushın /game buyrıǵınan paydalanıń'
                    await bot.send_message(chat_id=query.message.chat.id, text=text, parse_mode='Markdown')
                    group.game = False
                    group.players = None
                    group.positions = None
                    group.dice = None
                    group.queue = None
                    player = session.query(Player).filter_by(chat_id=query.message.chat.id, player_id=winner_id).first()
                    if player:
                        player.win += 1
                    else:
                        new_player = Player(chat_id=query.message.chat.id, player_id=winner_id, win=1)
                        session.add(new_player)
                    session.commit()
                    return                    
                await send_zarik(query.message.chat.id)
                return
            elif len(allow_stones) == 2:
                btn1 = InlineKeyboardButton(text=stns[allow_stones[0]], callback_data=f'stone-{allow_stones[0]}')
                btn2 = InlineKeyboardButton(text=stns[allow_stones[1]], callback_data=f'stone-{allow_stones[1]}')
                stones = InlineKeyboardMarkup(inline_keyboard=[[btn1, btn2]])
            elif len(allow_stones) == 3:
                btn1 = InlineKeyboardButton(text=stns[allow_stones[0]], callback_data=f'stone-{allow_stones[0]}')
                btn2 = InlineKeyboardButton(text=stns[allow_stones[1]], callback_data=f'stone-{allow_stones[1]}')
                btn3 = InlineKeyboardButton(text=stns[allow_stones[2]], callback_data=f'stone-{allow_stones[2]}')
                stones = InlineKeyboardMarkup(inline_keyboard=[[btn1, btn2, btn3]])
            elif len(allow_stones) == 4:
                btn1 = InlineKeyboardButton(text=stns[allow_stones[0]], callback_data=f'stone-{allow_stones[0]}')
                btn2 = InlineKeyboardButton(text=stns[allow_stones[1]], callback_data=f'stone-{allow_stones[1]}')
                btn3 = InlineKeyboardButton(text=stns[allow_stones[2]], callback_data=f'stone-{allow_stones[2]}')
                btn4 = InlineKeyboardButton(text=stns[allow_stones[3]], callback_data=f'stone-{allow_stones[3]}')
                stones = InlineKeyboardMarkup(inline_keyboard=[[btn1, btn2, btn3, btn4]])
            
            await send_stones(chat_id=query.message.chat.id, stones=stones, dice=dice, allow_stones=allow_stones)


        else:
            if dice != 6:
                group.next_quewe()
            await send_zarik(query.message.chat.id)
            
    elif 'stone' in query.data:
        if query.from_user.id != group.get_players()[group.queue-1]:
            await bot.answer_callback_query(query.id, text="Bul knopka siz ushın emes!", show_alert=True)
            return
        t,s = (query.data).split('-')

        group.button_clicked = None
        session.commit()
        text = f'[{cards[group.queue-1]} {((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=group.get_players()[group.queue-1])).user.first_name)[:30]}](tg://user?id={group.get_players()[group.queue-1]}) {stns[int(s)]} tasın júrdi'
        data = group.forward(int(s))
        await bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text=text, parse_mode='Markdown')
        if data[0] == 'back':
            text = f'[{cards[data[1]]} {((await bot.get_chat_member(chat_id=query.message.chat.id, user_id=group.get_players()[data[1]])).user.first_name)[:30]}](tg://user?id={group.get_players()[data[1]]}) sizdiń {stns[data[2]]} tasıńız izge qayttı'
            await bot.send_message(chat_id=query.message.chat.id, text=text, parse_mode='Markdown')
        await send_board(query.message.chat.id)
        await asyncio.sleep(10)
        await send_zarik(query.message.chat.id)


            

@dp.message()
async def echo(message: types.Message):
    if message.chat.type == 'private':
        return
    group = session.query(Group).filter_by(chat_id=message.chat.id).first()
    if group.game:
        await message.delete()

@dp.channel_post()
async def channel_post(message: types.Message):
    if message.chat.id != -1002135475673:
        return
    users = session.query(User).all()
    n = 0
    for user in users:
        try:
            await message.forward(user.user_id)
            n += 1
        except: 
            session.delete(user)
            session.commit()
    chats = session.query(Group).all()
    k = 0
    for chat in chats:
        try:
            await message.forward(chat.chat_id)
            k += 1
        except:
            session.delete(chat)
            session.commit()
    await message.reply(f'{n} adamǵa hám {k} gruppaǵa jiberildi')


async def main():
    groups = session.query(Group).all()
    for group in groups:
        if group.game or group.reg_id:
            group.game = False
            group.players = None
            group.positions = None
            group.dice = None
            group.queue = None
            group.sleeps = 0
            group.reg_id = None
            group.button_clicked = None
            session.commit()
            if group.button_clicked:
                await bot.delete_message(chat_id=group.chat_id, message_id=group.button_clicked)
            await bot.send_message(chat_id=group.chat_id, text='Oyın toqtatıldı.\nOyındı baslaw ushın /game buyrıǵınan paydalanıń')

    
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
    
