import pyaudio
import numpy as np
import serial
import time

SERIAL_PORT = '/dev/tty.usbserial-0001'  # Замените на ваш порт ESP32
BAUD_RATE = 115200
THRESHOLD = 2000      # Минимальный порог громкости для свечения
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 22050

LIGHT_ON_TIME = 0.2

# Максимальное значение яркости (для ШИМ) - 255
MAX_BRIGHTNESS = 255

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Подключено к ESP32.")
except Exception as e:
    print(f"Ошибка подключения к порту: {e}")
    exit()

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("🎤 Слушаю микрофон...")

last_trigger_time = 0

def volume_to_brightness(volume, min_vol=THRESHOLD, max_vol=50000):
    """
    Преобразует уровень громкости в яркость от 0 до 255.
    min_vol - порог минимального громкого звука
    max_vol - верхний порог (значение громкости, выше которого яркость = max)
    """
    if volume < min_vol:
        return 0
    elif volume > max_vol:
        return MAX_BRIGHTNESS
    else:
        # Линейное масштабирование
        return int((volume - min_vol) / (max_vol - min_vol) * MAX_BRIGHTNESS)

try:
    while True:
        try:
            data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
        except Exception as e:
            print(f"🔴 Ошибка чтения аудио: {e}")
            continue

        volume = np.linalg.norm(data)
        brightness = volume_to_brightness(volume)

        print(f"🎧 Громкость: {int(volume)}  →  Яркость: {brightness}")

        current_time = time.time()
        if brightness > 0:
            ser.write(bytes([brightness]))  # Отправляем 1 байт с яркостью
            last_trigger_time = current_time
        else:
            # Держим свет включенным LIGHT_ON_TIME секунд после последнего громкого звука
            if current_time - last_trigger_time > LIGHT_ON_TIME:
                ser.write(bytes([0]))
            else:
                ser.write(bytes([brightness]))

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nЗавершено пользователем")

finally:
    if stream.is_active():
        stream.stop_stream()
    stream.close()
    p.terminate()
    ser.close()
