import time
while True:
    try:
        time.sleep(1)
        print(time.time())
    except KeyboardInterrupt:
        print("yah")
        break
