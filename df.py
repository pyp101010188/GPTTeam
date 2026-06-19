import asyncio
from bleak import BleakClient

# =========================================================
# BLE UUID
# =========================================================

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

# =========================================================
# MAC АДРЕСА ESP32
# =========================================================

ESP1_ADDRESS = "90:70:69:C3:87:8A"
ESP2_ADDRESS = "14:63:93:C6:E4:82"

# =========================================================
# НАСТРОЙКИ
# =========================================================

ESP1 = {
    "power": 255,
    "time": 2400,
    "steps": 500,
    "stepdelay": 1000,
}

ESP2 = {
    "power": 255,
    "time": 2500,
    "steps": 500,
    "stepdelay": 1000,
}

# =========================================================
# ОТПРАВКА КОМАНДЫ
# =========================================================

async def send(client, cmd):
    await client.write_gatt_char(
        CHAR_RX_UUID,
        cmd.encode(),
        response=True
    )

# =========================================================
# НАСТРОЙКА ESP
# =========================================================

async def setup_esp(client, cfg):

    await send(client, f"POWER:{cfg['power']}")
    await asyncio.sleep(0.1)

    await send(client, f"TIME:{cfg['time']}")
    await asyncio.sleep(0.1)

    await send(client, f"STEPS:{cfg['steps']}")
    await asyncio.sleep(0.1)

    await send(client, f"STEPDELAY:{cfg['stepdelay']}")
    await asyncio.sleep(0.1)

# =========================================================
# ОСНОВНАЯ ЛОГИКА
# =========================================================

async def main():

    async with BleakClient(ESP1_ADDRESS) as esp1 
            #    BleakClient(ESP2_ADDRESS) as esp2


        # ---------------------------------------------
        # Настройка устройств
        # ---------------------------------------------

        await setup_esp(esp1, ESP1)

        
        # await setЯЯЯЯup_esp(esp2, ESP2)


        # =================================================
        # МЕНЮ
        # =================================================

        while True:
            cmd = input("Команда: ").strip().lower(),

            # ---------------------------------------------
            # DC мотор
            # ---------------------------------------------

            if cmd == "2":

                await asyncio.gather(
                    send(esp1, "MOTOR:F"),
                    # send(esp2, "MOTOR:B")
                )

            elif cmd == "1":

                await asyncio.gather(
                    send(esp1, "MOTOR:B"),
                    # send(esp2, "MOTOR:F")
                )

            elif cmd == "3":

                await asyncio.gather(
                    send(esp1, "MOTOR:S"),
                    # send(esp2, "MOTOR:S")
                )

            # ---------------------------------------------
            # Шаговый
            # ---------------------------------------------

            elif cmd == "4":

                await asyncio.gather(
                    send(esp1, "STEP:F"),
                    # send(esp2, "STEP:F")
                )

            elif cmd == "5":

                await asyncio.gather(
                    send(esp1, "STEP:B"),
                    # send(esp2, "STEP:B")
                )

            elif cmd == "q":
                break

            

# =========================================================

if __name__ == "__main__":
    asyncio.run(main())