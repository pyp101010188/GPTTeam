import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

print("--- Доступные голоса ---")
for index, voice in enumerate(voices):
    print(f"Индекс: {index}")
    print(f"ID: {voice.id}")
    print(f"Имя: {voice.name}")
    print(f"Языки: {voice.languages}")
    print(f"Пол: {voice.gender}")
    print("-" * 30)