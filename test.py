import pyautogui
import time

pyautogui.FAILSAFE = True

time.sleep(3)  # 3 seconds to move your mouse away if needed
pyautogui.moveTo(400, 400, duration=1)
pyautogui.click()
pyautogui.write("Hello from Mac automation!")

x
