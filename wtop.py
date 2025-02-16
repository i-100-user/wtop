import psutil
import curses
import time
import threading

processes = []  # Lista de procesos compartida
lock = threading.Lock()  # Para evitar problemas de concurrencia

def update_processes():
    """Actualiza la lista de procesos cada 5 segundos en un hilo separado."""
    global processes
    while True:
        new_processes = []
        for proc in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                new_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass  # Ignorar errores de acceso

        with lock:
            processes = sorted(new_processes, key=lambda p: p['cpu_percent'], reverse=True)

        time.sleep(5)  # Espera 5 segundos antes de actualizar nuevamente

def draw_menu(stdscr):
    """Interfaz tipo htop con colores y navegación"""
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.keypad(True)
    selected_row = 0

    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selección
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Encabezado
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Mensajes
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Ayuda

    while True:
        stdscr.erase()  # Evita flickering
        height, width = stdscr.getmaxyx()

        with lock:
            current_processes = processes[:20]  # Copia segura de los procesos

        cpu_usage = psutil.cpu_percent()
        mem_usage = psutil.virtual_memory().percent
        header = f" CPU: {cpu_usage:.1f}%   MEM: {mem_usage:.1f}% "
        stdscr.addstr(1, max(0, (width - len(header)) // 2), header, curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(3, 5, "  PID         NOMBRE                     CPU (%)      MEMORIA (%)  ", curses.A_BOLD | curses.A_UNDERLINE)

        for idx, proc in enumerate(current_processes):
            pid, name, cpu, mem = proc["pid"], proc["name"], proc["cpu_percent"], proc["memory_percent"]
            style = curses.color_pair(1) | curses.A_BOLD if idx == selected_row else curses.color_pair(2)
            stdscr.addstr(5 + idx, 5, f"{pid:<10} {name[:25]:<25} {cpu:>7.1f}%      {mem:>7.1f}%", style)

        help_bar = " [ESC] o [q] Salir | [↑↓] Navegar | [Enter] Terminar proceso "
        stdscr.addstr(height - 2, max(0, (width - len(help_bar)) // 2), help_bar, curses.color_pair(4) | curses.A_BOLD)
        stdscr.refresh()

        stdscr.timeout(200)  # Pequeño retraso para hacer la UI más fluida
        key = stdscr.getch()

        if key == ord("q"):
            break
        elif key == curses.KEY_UP and selected_row > 0:
            selected_row -= 1
        elif key == curses.KEY_DOWN and selected_row < len(current_processes) - 1:
            selected_row += 1
        elif key == 10 and current_processes:  # Enter para eliminar proceso
            pid_to_kill = current_processes[selected_row]["pid"]
            try:
                psutil.Process(pid_to_kill).terminate()
                stdscr.addstr(height - 4, 5, f"✅ Proceso {pid_to_kill} eliminado.", curses.color_pair(3) | curses.A_BOLD)
                stdscr.refresh()
                time.sleep(1)
            except psutil.NoSuchProcess:
                stdscr.addstr(height - 4, 5, "❌ PID no válido o ya terminado.", curses.color_pair(3) | curses.A_BOLD)
                stdscr.refresh()
                time.sleep(1)
            
            selected_row = max(0, min(selected_row, len(current_processes) - 1))

if __name__ == "__main__":
    thread = threading.Thread(target=update_processes, daemon=True)
    thread.start()
    curses.wrapper(draw_menu)
