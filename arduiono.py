# import asyncio
# from bleak import BleakClient
# from contextlib import AsyncExitStack
# import sys

# # =========================================================
# # BLE UUID
# # =========================================================
# SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
# CHAR_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

# # =========================================================
# # MAC АДРЕСА ESP32
# # =========================================================
# ESP1_ADDRESS = "90:70:69:C3:87:8A"
# ESP2_ADDRESS = "14:63:93:C6:E4:82"

# # =========================================================
# # НАСТРОЙКИ
# # =========================================================
# ESP1_CFG = {"power": 255, "time": 2400, "steps": 500, "stepdelay": 1000}
# ESP2_CFG = {"power": 255, "time": 2500, "steps": 500, "stepdelay": 1000}

# # =========================================================
# # ФУНКЦИИ
# # =========================================================

# async def send(client, cmd):
#     """Безопасная отправка команды устройству"""
#     if client is None or not client.is_connected:
#         return
#     try:
#         await client.write_gatt_char(CHAR_RX_UUID, cmd.encode(), response=True)
#     except Exception as e:
#         print(f"[-] Ошибка отправки на {client.address}: {e}")

# async def setup_esp(client, cfg, name):
#     """Начальная конфигурация устройства"""
#     print(f"[*] Настройка {name} ({client.address})...")
#     configs = [
#         f"POWER:{cfg['power']}",
#         f"TIME:{cfg['time']}",
#         f"STEPS:{cfg['steps']}",
#         f"STEPDELAY:{cfg['stepdelay']}"
#     ]
#     for cmd in configs:
#         await send(client, cmd)
#         await asyncio.sleep(0.1)
#     print(f"[+] {name} готов к работе")

# # =========================================================
# # ОСНОВНОЙ ЦИКЛ
# # =========================================================

# async def main(command_queue):
#     # Исправление для Windows
#     if sys.platform == 'win32':
#         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#     async with AsyncExitStack() as stack:
#         print("[*] Подключение к устройствам...")
        
#         # Пытаемся подключиться к ESP1
#         try:
#             esp1 = await stack.enter_async_context(BleakClient(ESP1_ADDRESS, timeout=15.0))
#             print("[OK] ESP1 подключена")
#             await setup_esp(esp1, ESP1_CFG, "ESP1")
#         except Exception as e:
#             print(f"[ERR] Не удалось подключить ESP1: {e}")
#             esp1 = None

#         # Пытаемся подключиться к ESP2
#         try:
#             esp2 = await stack.enter_async_context(BleakClient(ESP2_ADDRESS, timeout=15.0))
#             print("[OK] ESP2 подключена")
#             await setup_esp(esp2, ESP2_CFG, "ESP2")
#         except Exception as e:
#             print(f"[ERR] Не удалось подключить ESP2: {e}")
#             esp2 = None

#         if esp1 is None and esp2 is None:
#             print("[CRITICAL] Ни одно устройство не подключено. Выход.")
#             return

#         print("\n--- СИСТЕМА УПРАВЛЕНИЯ ESP32 ЗАПУЩЕНА ---")

#         while True:
#             if not command_queue.empty():
#                 cmd = command_queue.get().strip().lower()
                
#                 if cmd == "q": 
#                     print("[*] Завершение работы с ESP")
#                     break
                
#                 # ЛОГИКА КОМАНД (параллельная отправка)
#                 if cmd == "1":
#                     await asyncio.gather(send(esp1, "MOTOR:F"), send(esp2, "MOTOR:B"))
                
#                 elif cmd == "2":
#                     await asyncio.gather(send(esp1, "MOTOR:B"), send(esp2, "MOTOR:F"))
                
#                 elif cmd == "3":
#                     await asyncio.gather(send(esp1, "MOTOR:S"), send(esp2, "MOTOR:S"))
                
#                 elif cmd == "4":
#                     await asyncio.gather(send(esp1, "STEP:F"), send(esp2, "STEP:F"))
                
#                 elif cmd == "5":
#                     await asyncio.gather(send(esp1, "STEP:B"), send(esp2, "STEP:B"))
                
#                 else:
#                     # Отправка произвольной команды на оба устройства
#                     await asyncio.gather(send(esp1, cmd.upper()), send(esp2, cmd.upper()))
            
#             await asyncio.sleep(0.05)