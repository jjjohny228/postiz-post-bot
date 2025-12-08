import os
import types

from aiogram import types
from aiogram import Dispatcher
from aiogram.dispatcher.filters import CommandStart

from src.utils import ApostolVideoUploader

async def handle_start_command(message: types.Message) -> None:
    await message.answer(
        text='Добро пожаловать в бот по постигу. Чтобы начать постинг отправьте мне файл csv'
    )


async def handle_csv_file(message: types.Message):
    # Проверяем, что пришёл файл
    if not message.document:
        await message.answer("Пожалуйста, пришлите CSV файл.")
        return

    file_info = await message.document.get_file()
    file_name = message.document.file_name

    # Сохраняем файл локально
    download_path = f"temp/{file_name}"
    await message.document.download(destination_file=download_path)

    # Вызываем вашу функцию обработки CSV файла (предположим, она асинхронная)
    try:
        await ApostolVideoUploader().upload_video(download_path, message)
        await message.answer("Файл успешно обработан.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке файла: {str(e)}")
    finally:
        # Удаляем файл после обработки
        if os.path.exists(download_path):
            os.remove(download_path)





def register_user_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(handle_start_command, CommandStart())
    dp.register_message_handler(handle_csv_file, content_types=types.ContentType.DOCUMENT)
