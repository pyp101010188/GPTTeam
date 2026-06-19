import asyncio
import sys

# 1. СТРОГО В НАЧАЛЕ: Решение проблемы Bleak на Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from bleak import BleakScanner, BleakClient
import pyttsx3
import time

# --- Константы ---
PYBRICKS_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"
HUB_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]


# --- TTS ---
_tts_engine = None
_tts_lock = threading.Lock()

def get_tts_engine():
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty('rate', 160)   # скорость речи
        _tts_engine.setProperty('volume', 1.0) # громкость 0.0–1.0
        voices = _tts_engine.getProperty('voices')
        if len(voices) > 2:
            _tts_engine.setProperty('voice', voices[2].id)
    return _tts_engine

def speak(text: str):
    """Синхронная озвучка текста (запускается в отдельном потоке через executor)."""
    with _tts_lock:
        try:
            engine = get_tts_engine()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS ERROR] {e}")

def run_aiolam(trigger_event, command_queue, speech_busy_flag):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from aiolam import main_loop
        main_loop(trigger_event, command_queue, speech_busy_flag)
    except Exception as e:
        print(f"[AI ERROR] {e}")

# def run_arduino(command_queue):
#     try:
#         import arduiono
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         loop.run_until_complete(arduiono.main(command_queue))
#     except Exception as e:
#         print(f"[ARDUINO ERROR] {e}")

def get_voice_command(model):
    import vosk
    import sounddevice as sd

    print("[VOICE] Запуск распознавания")

    rec = vosk.KaldiRecognizer(model, 16000)

    try:
        with sd.RawInputStream(
            samplerate=16000,
            blocksize=4000,
            dtype='int16',
            channels=1
        ) as stream:

            print("[VOICE] Микрофон открыт")

            while True:
                data, _ = stream.read(2000)

                if rec.AcceptWaveform(bytes(data)):
                    res = json.loads(rec.Result())
                    text = res.get("text", "").strip()

                    print("[VOICE] Распознано:", text)

                    if text:
                        return text.lower()

    except Exception as e:
        print(f"[MIC ERROR] {e}")
        return ""
    
async def main():
    import vosk
    executor = ThreadPoolExecutor(max_workers=4)  # +1 воркер для TTS
    loop = asyncio.get_event_loop()

    arduino_queue = queue.Queue()

    # 1. Подключение роботов
    clients = []
    ready_events = [asyncio.Event() for _ in range(8)]

    def create_handler(idx):
        return lambda _, data: ready_events[idx].set() if (data[0] == 0x01 and b"rdy" in data) else None

    print("--- 1. Подключение к роботам ---")
    for i, name in enumerate(HUB_NAMES):
        try:
            dev = await BleakScanner.find_device_by_name(name, timeout=10.0)
            if dev:
                c = BleakClient(dev)
                await c.connect()
                await c.start_notify(PYBRICKS_UUID, create_handler(i))
                clients.append(c)
                print(f"[OK] Робот {name} подключен")
            else:
                print(f"[!] Робот {name} не найден")
                return
        except Exception as e:
            print(f"[CONN ERROR] {name}: {e}")
            return

    # 2. Инициализация звука

    # 3. Синхронизация
    print("--- 2. Синхронизация ---")
    for c in clients:
        await c.write_gatt_char(PYBRICKS_UUID, b"\x01")
    await asyncio.gather(*(e.wait() for e in ready_events))
    print("[+] Все роботы готовы")

    # 4. Запуск фоновых систем
    # threading.Thread(target=run_arduino, args=(arduino_queue,), daemon=True).start()

    # 5. Модель Vosk
    print("--- 3. Загрузка Vosk ---")
    model = await loop.run_in_executor(executor, lambda: vosk.Model("vosk-model-en-us-0.42-gigaspeech"))

    async def send_command(payloads):
        for e in ready_events: e.clear()
        active_indices = []
        for i, client in enumerate(clients):
            if client.is_connected:
                await client.write_gatt_char(PYBRICKS_UUID, b"\x06" + payloads[i])
                active_indices.append(i)
        
        await asyncio.wait_for(asyncio.gather(*(ready_events[i].wait() for i in active_indices)), timeout=15.0)

    async def say(text: str):
        """Неблокирующая озвучка: запускает speak() в executor."""
        await loop.run_in_executor(executor, speak, text)

    print("\n--- СИСТЕМА ГОТОВА ---")

    try:
        while True:
            cmd = await loop.run_in_executor(executor, get_voice_command, model)
            if not cmd or len(cmd) < 3: continue
            
            print(f"Команда: {cmd}")

            # ЛОГИКА КОМАНД
            if any(w in cmd for w in ['heart']):
                # arduino_queue.put("5")
                # arduino_queue.put("4")
                await send_command([b'5 5aaaaa', b'4 6aaaaa', b'3 5aaaaa', b'4 4aaaaa', b'6 6aaaaa', b'7 5aaaaa', b'6 4aaaaa', b'5 3aaaaa'], )

            elif any(w in cmd for w in ['diamond']):
                # arduino_queue.put("2")
                await send_command([b'5 6aaaaa', b'4 6aaaaa', b'3 5aaaaa', b'4 4aaaaa', b'6 6aaaaa', b'7 5aaaaa', b'6 4aaaaa', b'5 3aaaaa'], )

            elif 'happy' in cmd:
                await send_command([b'4 7aaaaa', b'5 5aaaaa', b'3 4aaaaa', b'4 3aaaaa', b'6 7aaaaa', b'7 4aaaaa', b'6 3aaaaa', b'5 3aaaaa'], )
            
            elif 'sad' in cmd:
                await send_command([b'4 7aaaaa', b'5 5aaaaa', b'3 2aaaaa', b'4 3aaaaa', b'6 7aaaaa', b'7 2aaaaa', b'6 3aaaaa', b'5 3aaaaa'], )

            # ТОЧНАЯ ПРОВЕРКА КОМАНДЫ "ДОМОЙ"
            elif 'start' in cmd: 
            
                await send_command([b'bbbbbbbb'] * 8)
                # await say("Возвращаюсь на место.")

            elif 'honey' in cmd:
                await send_command([b'5 7aaaaa', b'4 6aaaaa', b'4 5aaaaa', b'bbbbbbbb', b'6 6aaaaa', b'6 5aaaaa', b'5 4aaaaa', b'bbbbbbbb'], )

            elif 'stop' in cmd:
                break
            cmd = "stop"
    finally:
        # arduino_queue.put("q")
        for c in clients:
            with suppress(Exception): await c.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
    print("hello world")

    
    