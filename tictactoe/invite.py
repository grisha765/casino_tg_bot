from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from tictactoe.board import send_ttt_board, initialize_ttt_board
from config import logging_config
import asyncio

logging = logging_config.setup_logging(__name__)

async def update_buttons(client, session_id, session, message, selected_size, selected_mode, get_translation, FloodWait):
    board_size_buttons = [
        InlineKeyboardButton(
            f"{'>>' if selected_size == 3 else ''}3x3{'<<' if selected_size == 3 else ''}", 
            callback_data=f"board_size_3_{session_id}"
        ),
        InlineKeyboardButton(
            f"{'>>' if selected_size == 5 else ''}5x5{'<<' if selected_size == 5 else ''}", 
            callback_data=f"board_size_5_{session_id}"
        ),
        InlineKeyboardButton(
            f"{'>>' if selected_size == 7 else ''}7x7{'<<' if selected_size == 7 else ''}", 
            callback_data=f"board_size_7_{session_id}"
        )
    ]
    if session["board_size"] != 3:
        game_mode_buttons = [
            InlineKeyboardButton(
                f"{'>>' if selected_mode == 0 else ''}{get_translation(session["lang"], "mode_0")}{'<<' if selected_mode == 0 else ''}", 
                callback_data=f"game_mode_0_{session_id}"
            ),
            InlineKeyboardButton(
                f"{'>>' if selected_mode == 1 else ''}{get_translation(session["lang"], "mode_1")}{'<<' if selected_mode == 1 else ''}", 
                callback_data=f"game_mode_1_{session_id}"
            ),
            InlineKeyboardButton(
                f"{'>>' if selected_mode == 2 else ''}{get_translation(session["lang"], "mode_2")}{'<<' if selected_mode == 2 else ''}", 
                callback_data=f"game_mode_2_{session_id}"
            ),
            InlineKeyboardButton(
                f"{'>>' if selected_mode == 3 else ''}{get_translation(session["lang"], "mode_1")[:4]}. {get_translation(session["lang"], "mode_2").lower()}{'<<' if selected_mode == 3 else ''}", 
                callback_data=f"game_mode_3_{session_id}"
            )
        ]
    else:
        game_mode_buttons = None

    keyboard = [board_size_buttons]
    join_button = InlineKeyboardButton(get_translation(session["lang"], "join"), callback_data=f"join_o_{session_id}")

    if game_mode_buttons:
        keyboard.append(game_mode_buttons)

    keyboard.append([join_button])

    reply_markup = InlineKeyboardMarkup(keyboard)
    async def text_edit(client, message, session, reply_markup):
        if message.inline_message_id:
            await client.edit_inline_reply_markup(
                inline_message_id=message.inline_message_id,
                reply_markup=reply_markup,
            )
        else:
            await client.edit_message_reply_markup(
                chat_id=session["chat_id"], 
                message_id=message.message.id, 
                reply_markup=reply_markup
            )
    try:
        await text_edit(client, message, session, reply_markup)
    except FloodWait as e:
        logging.warning(f"Session {session_id}: Flood wait error. Sleeping for {e.value} seconds.")
        await asyncio.sleep(e.value)
        await text_edit(client, message, session, reply_markup)

async def ttt_start(session_id, sessions, message, get_translation):
    user = message.from_user
    sessions[session_id]["x"]["id"] = user.id
    sessions[session_id]["x"]["name"] = user.username if user.username else user.first_name
    
    logging.debug(f"Session {session_id}: Start game: {sessions[session_id]['x']['name']}")
    
    board_size_buttons = [
        InlineKeyboardButton(">>3x3<<", callback_data=f"board_size_3_{session_id}"),
        InlineKeyboardButton("5x5", callback_data=f"board_size_5_{session_id}"),
        InlineKeyboardButton("7x7", callback_data=f"board_size_7_{session_id}")
    ]

    keyboard = [board_size_buttons]
    join_button = InlineKeyboardButton(get_translation(sessions[session_id]["lang"], "join"), callback_data=f"join_o_{session_id}")
    keyboard.append([join_button])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if sessions[session_id]["chat_id"] == None:
        results = [
            InlineQueryResultArticle(
                title=get_translation(sessions[session_id]['lang'], 'inline_title'),
                input_message_content=InputTextMessageContent(
                    f"{get_translation(sessions[session_id]['lang'], 'session_id')}: {session_id}\n"
                    f"{get_translation(sessions[session_id]['lang'], 'x')}: @{sessions[session_id]['x']['name']}\n"
                    f"{get_translation(sessions[session_id]['lang'], 'wait')}"
                ),
                reply_markup=reply_markup
            )
        ]
        return sessions[session_id]["x"]["id"], sessions[session_id]["x"]["name"], results
    else:
        msg = await message.reply_text(
            f"{get_translation(sessions[session_id]['lang'], 'session_id')}: {session_id}\n"
            f"{get_translation(sessions[session_id]['lang'], 'x')}: @{sessions[session_id]['x']['name']}\n"
            f"{get_translation(sessions[session_id]['lang'], 'wait')}",
            reply_markup=reply_markup
        )

        sessions[session_id]["message_id"] = msg.id
        return sessions[session_id]["x"]["id"], sessions[session_id]["x"]["name"], msg.id

async def join_ttt_o(session_id, sessions, client, callback_query, get_translation, session_cleanup_tasks, random, FloodWait):
    user = callback_query.from_user
    if sessions.get(session_id) == None:
        await callback_query.answer(get_translation(callback_query.from_user.language_code, 'complete'))
        return

    if user.id == sessions[session_id]["x"]["id"]:
            await callback_query.answer(
                get_translation(sessions[session_id]["lang"], "incorrect_join0") +
                get_translation(sessions[session_id]["lang"], "x").lower() +
                get_translation(sessions[session_id]["lang"], "incorrect_join1") +
                get_translation(sessions[session_id]["lang"], "o").lower() + "."
            )
    elif not sessions[session_id]["o"]["id"]:
        if session_id in session_cleanup_tasks:
            session_cleanup_tasks[session_id].cancel()
            logging.debug(f"Session {session_id}: Del cleanup Task {session_cleanup_tasks[session_id]}.")
            del session_cleanup_tasks[session_id]
        sessions[session_id]["o"]["id"] = user.id
        sessions[session_id]["o"]["name"] = user.username if user.username else user.first_name
        if sessions[session_id]["message_id"] == None:
            sessions[session_id]["message_id"] = callback_query.inline_message_id
        logging.debug(f"Session {session_id}: Join game: {sessions[session_id]['o']['name']}")
        logging.debug(f"Session {session_id}: game mode set: {sessions[session_id]["game_mode"]}")
        initialize_ttt_board(session_id, board_size=sessions[session_id]["board_size"])

        if sessions[session_id]["game_mode"] == 1 or sessions[session_id]["game_mode"] == 3:
            sessions[session_id]["random_mode"] = random.choice([0, 3, 4])
            logging.debug(f"Session {session_id}: random mode set: {sessions[session_id]["random_mode"]}")

        logging.debug(f"Session {session_id}: initialize board {sessions[session_id]["board_size"]}")

        async def text_edit(client, session, get_translation):
            if session["chat_id"] == None:
                await client.edit_inline_text(
                    inline_message_id=session["message_id"],
                    text=f"{get_translation(session["lang"], "x")}: @{session['x']['name']}\n{get_translation(session["lang"], "o")}: @{session['o']['name']}\n{get_translation(session["lang"], "start_game")}",
                )
            else:
                await callback_query.message.edit_text(
                    f"{get_translation(session["lang"], "x")}: @{session['x']['name']}\n{get_translation(session["lang"], "o")}: @{session['o']['name']}\n{get_translation(session["lang"], "start_game")}"
                )
        try:
            await text_edit(client, sessions[session_id], get_translation)
        except FloodWait as e:
            logging.warning(f"Session {session_id}: Flood wait error. Sleeping for {e.value} seconds.")
            await asyncio.sleep(e.value)
            await text_edit(client, sessions[session_id], get_translation)

        next_player = "🔴" if sessions[session_id]["next_move"] == "O" else "❌"
        logging.debug(f"Session {session_id}: start move {sessions[session_id]["next_move"]}")
        await send_ttt_board(session_id, client, sessions[session_id], get_translation, FloodWait, next_player)
    else:
        await callback_query.answer(get_translation(sessions[session_id]["lang"], "game_started"))

async def remove_expired_ttt_session(session_id, sessions, selected_squares, available_session_ids, client):
    await asyncio.sleep(600)
    if not sessions[session_id]["o"]["id"]:
        if sessions[session_id]["chat_id"] != None:
            chat_id = sessions[session_id]["chat_id"]
            message_id = sessions[session_id]["message_id"]
            await client.delete_messages(chat_id, message_id)
        del sessions[session_id]
        del selected_squares[session_id]
        available_session_ids.append(session_id)
        logging.debug(f"Session {session_id} expired and was removed.")

if __name__ == "__main__":
    raise RuntimeError("This module should be run only via main.py")
