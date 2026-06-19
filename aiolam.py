import pyttsx3
import time
from ollama import Client

# ── Конфигурация ──────────────────────────────────────────
client = Client()

FIGURE_NAMES = {
    'улыб':  'весёлый смайлик',
    'груст': 'грустный смайлик',
    'серд':  'сердце',
    'алмаз': 'алмаз',
}

SKIP_COMMANDS = {'дом', 'домой'}
recent_responses = []

def speak(text):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        # Индекс вашего голоса (например, 2)
        voice_index = 2 
        
        if len(voices) > voice_index:
            engine.setProperty('voice', voices[voice_index].id)
        
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 1.0)
        
        engine.say(text)
        engine.runAndWait()
        
        engine.stop()
        del engine
    except Exception as e:
        print(f"[TTS ERROR] {e}")

def llama_evaluate(figure: str):
    global recent_responses
    history = "\n".join(recent_responses[-4:])
    
    prompt = f"""
Ты профессиональный комментатор робо-шоу. 
Роботы выстроились в фигуру: {figure}.

ВАЖНО обезательно отвечать  
1. Не повторяй свои прошлые фразы: {history}
2. НЕ ГОВОРИ про точность, красоту или симметрию фигур.
3. Оценивай эмоционально, как на стадионе.
4. Используй одно из слов: "отлично", "хорошо" или "неплохо".
5. Максимум 2 коротких предложения.
6 на груст ты должен призывать аудиторию поднять настроение роботов
7 Отвечай только по-русски.
8 без эмодзи не используй слова ценост ,настро,алмаз ,поддер,любовь,сердце, поддержки и все их сколонение шарж
9 на поддерж ты должен поблагодарить аудиторию от лица роботов
"""
    messages = [{'role': 'user', 'content': prompt}]
    full_response = ""
    
    try:
        for part in client.chat('llama3.1:8b', messages=messages, stream=True):
            chunk = part.message.content
            print(chunk, end='', flush=True)
            full_response += chunk
        
        clean_response = full_response.strip()
        recent_responses.append(clean_response)
        if len(recent_responses) > 10: recent_responses.pop(0)
        return clean_response
    except Exception as e:
        return "Роботы справились неплохо!"

def main_loop(trigger_event, command_queue, speech_busy_flag):
    print("[AIOLAM] Система ИИ готова.")

    while True:
        trigger_event.wait()
        trigger_event.clear()

        if not command_queue.empty():
            command = command_queue.get()
            
            if command in SKIP_COMMANDS:
                continue

            # Блокируем микрофон
            speech_busy_flag.set()
            
            figure_name = FIGURE_NAMES.get(command, "неизвестная фигура")
            response_text = llama_evaluate(figure_name)
            
            speak(response_text)
            
            # Небольшая пауза после речи, чтобы микрофон не поймал эхо
            time.sleep(0.5)
            speech_busy_flag.clear()
            print("\n[AIOLAM] Готов слушать снова.")