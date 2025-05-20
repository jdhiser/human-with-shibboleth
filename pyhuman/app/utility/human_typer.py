import os
import pty
import time
import select
import threading
import re
import sys
import random
from typing import Callable

class HumanTyperShell:
    def __init__(self,
                 shell: str = "/bin/bash",
                 prompt_regex: str = rb"[\r\n]?[\w.-]+@[\w.-]+:[^\n]*[$#] ",
                 live_echo: bool = False,
                 keystroke_delay_fn: Callable[[], float] = None,
                 post_prompt_delay: float = 1.0,
                 prompt_timeout: float = 10.0,
                 verbose: bool = False):
        """
        :param shell: Shell binary to launch.
        :param prompt_regex: Regex to detect shell prompt.
        :param live_echo: If True, prints shell output and typed characters in real time.
        :param keystroke_delay_fn: Function returning float delay per keystroke (in seconds).
        :param post_prompt_delay: Additional wait time after prompt match to gather more output.
        :param prompt_timeout: how long to wait for a prompt.  may need to crank this up if doing something like long link times
        :param verbose: If True, enables debug output.
        """
        self.shell = shell
        self.live_echo = live_echo
        self.verbose = verbose
        self.prompt_regex = re.compile(prompt_regex)
        self.keystroke_delay_fn = keystroke_delay_fn or (lambda: random.uniform(0.05, 0.35))
        self.post_prompt_delay = post_prompt_delay
        self.child_pid, self.master_fd = pty.fork()
        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._stop = False
        self._suppress_output = False
        self.prompt_timeout = prompt_timeout

        if self.child_pid == 0:
            os.execvp(self.shell, [self.shell])
        else:
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            try:
                self._wait_for_prompt()
            except TimeoutError:
                raise RuntimeError("Shell did not produce prompt in time. Is the shell hanging or producing unexpected output?")

    def _read_output(self):
        while not self._stop:
            r, _, _ = select.select([self.master_fd], [], [], 0.1)
            if self.master_fd in r:
                try:
                    data = os.read(self.master_fd, 1024)
                    if not data:
                        break
                    with self._lock:
                        self._buffer += data
                    if self.live_echo and not self._suppress_output:
                        sys.stdout.buffer.write(data)
                        sys.stdout.flush()
                except OSError:
                    break

    def _wait_for_prompt(self, timeout: float = 10.0) -> str:
        if self.verbose:
            print("[DEBUG] Waiting for prompt...")
        start = time.time()
        last_buffer_size = 0
        last_change = start
        while time.time() - last_change < timeout:
            time.sleep(0.05)
            with self._lock:
                match = self.prompt_regex.search(self._buffer)
                if match:
                    end = match.end()
                    if self.verbose:
                        print("[DEBUG] Prompt matched.")
                    break
                if len(self._buffer) != last_buffer_size:
                    last_change = time.time()
                    last_buffer_size = len(self._buffer)
        else:
            raise TimeoutError("Timed out waiting for prompt.")

        time.sleep(self.post_prompt_delay)
        with self._lock:
            output = self._buffer[:end]
            self._buffer = self._buffer[end:]
            return output.decode(errors='ignore')


    def type_command(self, command: str) -> str:
        qwerty_neighbors = {
            'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx', 'e': 'wsdr',
            'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'i': 'ujko', 'j': 'huikmn',
            'k': 'jiolm', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
            'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awedxz', 't': 'rfgy',
            'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tugh',
            'z': 'asx', '1': '2q', '2': '13w', '3': '24e', '4': '35r', '5': '46t',
            '6': '57y', '7': '68u', '8': '79i', '9': '80o', '0': '9p',
            '-': '0p', '=': '-',
            ' ': ' '
        }

        with self._lock:
            self._buffer.clear()
        self._suppress_output = True

        i = 0
        while i < len(command):
            typo_happened = False

            # 3% chance to inject a typo
            if random.random() < 0.03:
                typo_count = random.choice([1, 3])

                # extra sleep for understanding your typo before fixing it.
                time.sleep(4*self.keystroke_delay_fn())
                for _ in range(typo_count):
                    char = command[i]
                    typo_choices = qwerty_neighbors.get(char.lower(), random.choice('abcdefghijklmnopqrstuvwxyz'))

                    typo = random.choice(typo_choices)
                    os.write(self.master_fd, typo.encode())
                    if self.live_echo:
                        sys.stdout.write(typo)
                        sys.stdout.flush()
                    # time.sleep(self.keystroke_delay_fn())

                for _ in range(typo_count):
                        # simulate backspace
                        os.write(self.master_fd, b"\x7f")
                        if self.live_echo:
                            sys.stdout.write('\b \b')
                            sys.stdout.flush()
                        time.sleep(self.keystroke_delay_fn())
                        typo_happened = True

            # now type the correct character
            char = command[i]
            os.write(self.master_fd, char.encode())
            if self.live_echo:
                sys.stdout.write(char)
                sys.stdout.flush()
            time.sleep(self.keystroke_delay_fn())
            i += 1

        os.write(self.master_fd, b'\n')
        if self.live_echo:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self._suppress_output = False
        return self._wait_for_prompt(self.prompt_timeout)


    def close(self):
        self._stop = True
        try:
            os.write(self.master_fd, b"exit\n")
        except OSError:
            pass
        self.reader_thread.join(timeout=1)
        os.close(self.master_fd)

# Example usage
if __name__ == "__main__":
    # Custom keystroke delay function for a slightly "sloppy" typer
    def jittery_typist():
        return random.gauss(0.1, 0.03)  # mean 100ms, stddev 30ms

    shell = HumanTyperShell(live_echo=True, keystroke_delay_fn=jittery_typist, verbose=True)

    try:
        output=shell.type_command("echo Hello, world")
        print(f"(Shell output was {output}")
        output=shell.type_command("uname -r")
        print(f"(Shell output was {output}")
        output=shell.type_command("ls -lh /tmp")
        print(f"(Shell output was {output}")
    finally:
        shell.close()

