import asyncio
import subprocess
import sys
import os
from contextlib import suppress
from bleak import BleakScanner, BleakClient

PYBRICKS_COMMAND_EVENT_CHAR_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"
HUB_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]

sys.coinit_flags = 0
try:
    from bleak.backends.winrt.util import allow_sta
    allow_sta()
except ImportError:
    pass



def launch_subprocesses():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python = sys.executable
    processes = []

    # arduino_path = os.path.join(base_dir, "arduiono.py")
    # if os.path.exists(arduino_path):
    #     print(f" Запуск _arduiono.py ...")
    #     p = subprocess.Popen([python, arduino_path],
    #                           creationflags=subprocess.CREATE_NEW_CONSOLE
    #                           if sys.platform == "win32" else 0)
    #     processes.append(("arduino", p))
    # else:
    #     print(f" arduiono.py не найден: {arduino_path}")

    return processes

async def main():
    print("=" * 50)
    print("  ЗАПУСК ВСЕХ КОМПОНЕНТОВ")
    print("=" * 50)
    child_procs = launch_subprocesses()
    print()

    # ── Импорт aiolam (напрямую, не subprocess) ───────────
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_dir)
    try:
        from aiolam import analyze_image, listen_for_command, COMMAND_SEQUENCE
        import cv2
        aiolam_available = True
        print("aiolam модуль загружен")
    except ImportError as e:
        print(f"  aiolam не импортирован: {e}")
        aiolam_available = False

    main_task = asyncio.current_task()

    # ready_events[i] — хаб i прислал rdy (готов принять команду)
    ready_events = [asyncio.Event() for _ in range(8)]

    # all_done_event — все 8 хабов прислали rdy после движения
    all_done_event = asyncio.Event()

    # rdy_count — счётчик хабов завершивших движение
    rdy_count = [0]
    waiting_for_done = [False]  # True пока ждём завершения движения

    clients = []

    def create_rx_handler(index):
        def handle_rx(_, data: bytearray):
            if data[0] == 0x01:
                payload = data[1:].strip()
                if payload == b"rdy":
                    ready_events[index].set()

                    if waiting_for_done[0]:
                        # Роботы едут — считаем кто доехал
                        rdy_count[0] += 1
                        print(f"  [{rdy_count[0]}/8] Хаб {index + 1} доехал (rdy)")
                        if rdy_count[0] >= 8:
                            print("✅ Все роботы встали в позицию!")
                            all_done_event.set()
                    else:
                        print(f"--- Хаб {index + 1} ГОТОВ ---")
                else:
                    print(f"Хаб {index + 1}: {payload.decode(errors='ignore')}")
        return handle_rx

    def handle_disconnect(client):
        print(f"Хаб {client.address} отключен.")
        if not main_task.done():
            main_task.cancel()

    async def send_all(data_list, current_command="фигура"):
        """
        1. Ждём rdy от всех (готовы принять)
        2. Отправляем команду
        3. Ждём rdy от всех (движение завершено)
        4. Снимаем камерой и анализируем
        """
        # Шаг 1: убедимся что все хабы готовы
        await asyncio.gather(*(e.wait() for e in ready_events))
        for e in ready_events:
            e.clear()

        # Шаг 2: готовимся считать завершения
        rdy_count[0] = 0
        all_done_event.clear()
        waiting_for_done[0] = True

        # Шаг 3: отправка команд
        tasks = [
            clients[i].write_gatt_char(
                PYBRICKS_COMMAND_EVENT_CHAR_UUID,
                b"\x06" + data_list[i],
                response=True
            )
            for i in range(8)
        ]
        await asyncio.gather(*tasks)
        print(f"📤 Команды отправлены роботам, жду пока все доедут...")

        await all_done_event.wait()
        waiting_for_done[0] = False

        # Шаг 5: снимок + анализ
        if aiolam_available:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    img_path = f"snap_{current_command}.jpg"
                    cv2.imwrite(img_path, frame)
                    print(f" Снимок сохранён: {img_path}")
                else:
                    img_path = "test.jpg"
            else:
                cap.release()
                img_path = "test.jpg"
                print("  Камера не найдена, использую test.jpg")

            print("🔍 Анализирую фигуру...")
            # Запускаем в executor чтобы не блокировать asyncio
            await asyncio.get_event_loop().run_in_executor(
                None, analyze_image, img_path
            )


    print("--- Поиск BLE устройств ---")
    devices = []
    for name in HUB_NAMES:
        device = await BleakScanner.find_device_by_name(name)
        if not device:
            print(f"Ошибка: Хаб {name} не найден!")
            for _, p in child_procs:
                p.terminate()
            return
        devices.append(device)
        print(f"Найден: {name}")

    print("\n--- Подключение хабов ---")
    try:
        for i, device in enumerate(devices):
            client = BleakClient(device, disconnected_callback=handle_disconnect)
            await client.connect()
            await client.start_notify(
                PYBRICKS_COMMAND_EVENT_CHAR_UUID, create_rx_handler(i))
            clients.append(client)
            print(f"Подключен хаб {i+1} ({HUB_NAMES[i]})")
            await asyncio.sleep(1.0)

        print("\nЗапуск программ на роботах...")
        for client in clients:
            await client.write_gatt_char(
                PYBRICKS_COMMAND_EVENT_CHAR_UUID, b"\x01", response=True)

        print("Ожидание первого 'rdy' от всех хабов...")
        await asyncio.gather(*(e.wait() for e in ready_events))
        print("Все системы в норме!\n")

        seq_index = [0]

        while True:
            # ── Vosk: ждём голосовую команду ──────────────────
            if aiolam_available:
                expected = COMMAND_SEQUENCE[seq_index[0] % len(COMMAND_SEQUENCE)]
                print(f"\n Следующая команда: '{expected}' — скажи её вслух")

                recognized = await asyncio.get_event_loop().run_in_executor(
                    None, listen_for_command, expected
                )

                if recognized:
                    command = expected
                    seq_index[0] += 1
                else:
                    print("Голос не распознан. Введите вручную:")
                    command = input("(серд / улыб / груст / алмаз / дом / стоп): ").strip().lower()
            else:
                command = input("\n Команда (серд / улыб / груст / алмаз / дом / стоп): ").strip().lower()

            # ── Отправка и ожидание rdy ────────────────────────
            if 'серд' in command or command == 'сердце':
                await send_all([b'5 5aaaaa', b'4 6aaaaa', b'3 5aaaaa', b'4 4aaaaa',
                                b'6 6aaaaa', b'7 5aaaaa', b'6 4aaaaa', b'5 3aaaaa'],
                               current_command="сердце")

            elif 'улыб' in command or command == 'улыбка':
                await send_all([b'4 7aaaaa', b'5 5aaaaa', b'3 4aaaaa', b'4 3aaaaa',
                                b'6 7aaaaa', b'7 4aaaaa', b'6 3aaaaa', b'5 3aaaaa'],
                               current_command="улыбка")

            elif 'груст' in command or command == 'грусть':
                await send_all([b'4 7aaaaa', b'5 5aaaaa', b'3 2aaaaa', b'4 3aaaaa',
                                b'6 7aaaaa', b'7 2aaaaa', b'6 3aaaaa', b'5 3aaaaa'],
                               current_command="грусть")

            elif 'алмаз' in command or command == 'алмаз':
                await send_all([b'5 6aaaaa', b'4 6aaaaa', b'3 5aaaaa', b'4 4aaaaa',
                                b'6 6aaaaa', b'7 5aaaaa', b'6 4aaaaa', b'5 3aaaaa'],
                               current_command="алмаз")

            elif 'дом' in command:
                await send_all([b'bbbbbbbb'] * 8, current_command="дом")

            elif 'стоп' in command:
                for client in clients:
                    with suppress(Exception):
                        await client.write_gatt_char(
                            PYBRICKS_COMMAND_EVENT_CHAR_UUID, b"\x00", response=True)
                print("Программы на хабах остановлены.")
                break

    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        print("\nЗакрытие BLE соединений...")
        for client in clients:
            await client.disconnect()
        print("Остановка дочерних процессов...")
        for name, p in child_procs:
            p.terminate()
            print(f"  {name} остановлен.")


if __name__ == "__main__":
    with suppress(asyncio.CancelledError):
        asyncio.run(main())
