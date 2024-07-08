import tkinter as tk
from tkinter import filedialog, ttk
import subprocess
import queue
import threading
import shlex
import os

class DockerGUI:
    def __init__(self, master):
        # log settings
        self.log_file = "docker_gui.log"
        self.log_buffer = []
        self.log_update_scheduled = False

        self.output_queue = queue.Queue()
        self.is_running = False

        self.master = master
        master.title("Docker Image Script Tester")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # Image and Container sections
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        top_frame.columnconfigure(1, weight=1)

        # Image section
        ttk.Label(top_frame, text="Docker Image:").grid(row=0, column=0, sticky=tk.W)
        self.image_entry = ttk.Entry(top_frame)
        self.image_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Button(top_frame, text="Pull Image", command=lambda: self.run_threaded(self.pull_image)).grid(row=0, column=2, padx=5)

        # Container section
        ttk.Label(top_frame, text="Container Name:").grid(row=1, column=0, sticky=tk.W)
        self.container_entry = ttk.Entry(top_frame)
        self.container_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        ttk.Button(top_frame, text="Create Container", command=lambda: self.run_threaded(self.create_container)).grid(
            row=1, column=2, padx=5)
        ttk.Button(top_frame, text="Load Container", command=lambda: self.run_threaded(self.load_container)).grid(row=1, column=3, padx=5)

        # Local path section
        ttk.Label(top_frame, text="Local Path:").grid(row=2, column=0, sticky=tk.W)
        self.local_entry = ttk.Entry(top_frame)
        self.local_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        ttk.Button(top_frame, text="Browse", command=self.browse_local).grid(row=2, column=2, padx=5)
        ttk.Button(top_frame, text="Copy to Container", command=lambda: self.run_threaded(self.copy_to_container)).grid(
            row=2, column=3, padx=5)

        # Code Execution section
        code_frame = ttk.LabelFrame(main_frame, text="Code Execution")
        code_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        code_frame.columnconfigure(0, weight=1)
        code_frame.rowconfigure(0, weight=1)

        self.code_text = tk.Text(code_frame)
        self.code_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        code_scroll = ttk.Scrollbar(code_frame, orient="vertical", command=self.code_text.yview)
        code_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.code_text.configure(yscrollcommand=code_scroll.set)

        ttk.Button(code_frame, text="Run", command=lambda: self.run_threaded(self.run_container)).grid(row=1, column=0, pady=5)

        # Result section
        result_frame = ttk.LabelFrame(main_frame, text="Result")
        result_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_text = tk.Text(result_frame)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        result_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=result_scroll.set)

        # Result Clear Button
        ttk.Button(result_frame, text="Clear", command=self.clear_result_text).grid(row=1, column=0, pady=5)

        # List section
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=2, rowspan=5, sticky=(tk.N, tk.S, tk.E), padx=10)
        list_frame.rowconfigure(1, weight=1)
        list_frame.rowconfigure(4, weight=1)

        ttk.Label(list_frame, text="Images:").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.image_listbox = tk.Listbox(list_frame)
        self.image_listbox.grid(row=1, column=0, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        image_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.image_listbox.yview)
        image_scroll.grid(row=1, column=2, sticky=(tk.N, tk.S))
        self.image_listbox.configure(yscrollcommand=image_scroll.set)
        self.image_listbox.bind("<<ListboxSelect>>", self.on_image_select)

        ttk.Button(list_frame, text="Delete Image", command=lambda: self.run_threaded(self.delete_image)).grid(row=2, column=0, columnspan=2, pady=5)

        ttk.Label(list_frame, text="Containers:").grid(row=3, column=0, columnspan=2, sticky=tk.W)
        self.container_listbox = tk.Listbox(list_frame)
        self.container_listbox.grid(row=4, column=0, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        container_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.container_listbox.yview)
        container_scroll.grid(row=4, column=2, sticky=(tk.N, tk.S))
        self.container_listbox.configure(yscrollcommand=container_scroll.set)
        self.container_listbox.bind("<<ListboxSelect>>", self.on_container_select)

        ttk.Button(list_frame, text="Stop Container", command=lambda: self.run_threaded(self.stop_container)).grid(
            row=5, column=0, pady=5)
        ttk.Button(list_frame, text="Delete Container", command=lambda: self.run_threaded(self.delete_container)).grid(
            row=5, column=1, pady=5)

        self.update_image_list()
        self.update_container_list()

        # 프로그레스 바 추가
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, columnspan=1, sticky=(tk.W, tk.E), pady=5)

    def clear_result_text(self):
        self.result_text.delete("1.0", tk.END)

    def run_threaded(self, func):
        thread = threading.Thread(target=func)
        thread.start()

    def resize_panes(self, event):
        delta = event.y - self.separator.winfo_y()
        if delta > 0:
            self.master.rowconfigure(3, weight=self.master.rowconfigure(3)['weight'] + delta)
            self.master.rowconfigure(4, weight=max(0, self.master.rowconfigure(4)['weight'] - delta))
        else:
            self.master.rowconfigure(4, weight=self.master.rowconfigure(4)['weight'] - delta)
            self.master.rowconfigure(3, weight=max(0, self.master.rowconfigure(3)['weight'] + delta))

    def log_to_file(self, message):
        with open(self.log_file, "a") as f:
            f.write(message)
        
        self.result_text.insert(tk.END, message)
        self.result_text.see(tk.END)
        self.result_text.update()

    def _update_log_display(self):
        self.auto_scroll()
        self._log_update_scheduled = False

    def limit_log_size(self, max_lines=300):
        content = self.result_text.get("1.0", tk.END)
        lines = content.splitlines()
        if len(lines) > max_lines:
            new_content = "\n".join(lines[-max_lines:])
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, new_content)

    def flush_log_buffer(self):
        if self.log_buffer:
            self.result_text.insert(tk.END, ''.join(self.log_buffer))
            self.log_buffer.clear()
            self.limit_log_size()
            self.auto_scroll()
        
        self.log_update_scheduled = False
        
        if self.log_buffer:
            self.master.after(100, self.flush_log_buffer)

    def auto_scroll(self):
        self.result_text.see(tk.END)
        self.result_text.update_idletasks()

    def clear_log(self):
        self.result_text.delete('1.0', tk.END)
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def update_image_list(self):
        self.image_listbox.delete(0, tk.END)
        images = subprocess.check_output(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"])
        for image in images.decode().strip().split("\n"):
            self.image_listbox.insert(tk.END, image)

    def update_container_list(self):
        self.container_listbox.delete(0, tk.END)
        containers = subprocess.check_output(["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"])
        for container_info in containers.decode().strip().split("\n"):
            if container_info:
                name, status = container_info.split("|")
                self.container_listbox.insert(tk.END, name)
                if status.startswith("Up"):
                    self.container_listbox.itemconfig(tk.END, fg="blue")

    def show_progress(self, message):
        self.progress_var.set(0)
        self.progress_bar.grid()
        self.result_text.insert(tk.END, f"{message}\n")
        self.result_text.see(tk.END)
        self.result_text.update()

    def update_progress(self, value):
        self.progress_var.set(value)
        self.master.after_idle(self.master.update_idletasks)

    def on_image_select(self, event):
        if self.image_listbox.curselection():
            selected_image = self.image_listbox.get(self.image_listbox.curselection())
            self.image_entry.delete(0, tk.END)
            self.image_entry.insert(0, selected_image)

    def on_container_select(self, event):
        if self.container_listbox.curselection():
            selected_container = self.container_listbox.get(self.container_listbox.curselection())
            self.container_entry.delete(0, tk.END)
            self.container_entry.insert(0, selected_container)

    def pull_image(self):
        image_name = self.image_entry.get()
        try:
            self.show_progress("Pulling image...")
            process = subprocess.Popen(["docker", "pull", image_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            progress = 0
            for line in process.stdout:
                self.result_text.insert(tk.END, line)
                self.result_text.see(tk.END)
                self.result_text.update()
                progress = (progress + 1) % 100
                self.update_progress(progress)

            process.wait()
            
            if process.returncode == 0:
                self.update_progress(100)
                self.master.update_idletasks()
                self.result_text.insert(tk.END, f"Pulled image: {image_name}\n")
                self.update_image_list()
            else:
                self.result_text.insert(tk.END, f"Failed to pull image: {image_name}\n")
        except Exception as e:
            self.result_text.insert(tk.END, f"Error: {str(e)}\n")

    def delete_image(self):
        if self.image_listbox.curselection():
            selected_image = self.image_listbox.get(self.image_listbox.curselection())
            try:
                subprocess.run(["docker", "rmi", selected_image], check=True)
                self.result_text.insert(tk.END, f"Deleted image: {selected_image}\n")
                self.update_image_list()
            except subprocess.CalledProcessError:
                self.result_text.insert(tk.END, f"Failed to delete image: {selected_image}\n")

    def create_container(self):
        image_name = self.image_entry.get()
        container_name = self.container_entry.get()
        try:
            subprocess.run(["docker", "run", "-d", "--name", container_name, image_name, "tail", "-f", "/dev/null", "sleep", "infinity"], check=True)
            self.result_text.insert(tk.END, f"Created and running container: {container_name}\n")
            self.update_container_list()
        except subprocess.CalledProcessError:
            self.result_text.insert(tk.END, f"Failed to create container: {container_name}\n")

    def browse_local(self):
        local_path = filedialog.askdirectory()
        self.local_entry.delete(0, tk.END)
        self.local_entry.insert(0, local_path)

    def copy_to_container(self):
        local_path = self.local_entry.get()
        container_name = self.container_entry.get()
        try:
            self.show_progress(f"Copying {local_path} to container {container_name}...")
            
            # docker cp 명령어 실행
            command = f"docker cp {local_path} {container_name}:/"
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            progress = 0
            # 실시간으로 출력 표시
            for line in process.stdout:
                self.result_text.insert(tk.END, line)
                self.result_text.see(tk.END)
                self.result_text.update()
                progress = (progress + 1) % 100
                self.update_progress(progress)
            
            # 에러 출력 표시
            for line in process.stderr:
                self.result_text.insert(tk.END, f"Error: {line}", "error")
                self.result_text.see(tk.END)
                self.result_text.update()
                progress = (progress + 1) % 100
                self.update_progress(progress)

            process.wait()
            
            if process.returncode == 0:
                self.update_progress(100)
                self.result_text.insert(tk.END, f"Successfully copied {local_path} to container {container_name}\n")
            else:
                self.result_text.insert(tk.END, f"Failed to copy {local_path} to container {container_name}\n")
        except Exception as e:
            self.result_text.insert(tk.END, f"Error: {str(e)}\n")

    def load_container(self):
        container_name = self.container_entry.get()
        try:
            # 컨테이너 시작
            subprocess.run(["docker", "start", container_name], check=True)

            self.result_text.insert(tk.END, f"Started container: {container_name}\n")
            self.update_container_list()
        except subprocess.CalledProcessError:
            self.result_text.insert(tk.END, f"Failed to start container: {container_name}\n")

    def delete_container(self):
        if self.container_listbox.curselection():
            selected_container = self.container_listbox.get(self.container_listbox.curselection())
            try:
                subprocess.run(["docker", "rm", "-f", selected_container], check=True)
                self.result_text.insert(tk.END, f"Deleted container: {selected_container}\n")
                self.update_container_list()
            except subprocess.CalledProcessError:
                self.result_text.insert(tk.END, f"Failed to delete container: {selected_container}\n")

    def run_container(self):
        container_name = self.container_entry.get()
        code = self.code_text.get("1.0", tk.END).strip()
        if code:
            threading.Thread(target=self._execute_container_command, args=(container_name, code), daemon=True).start()
        else:
            self.log_to_file("No code provided.\n")
    
    def _execute_container_command(self, container_name, code):
        script_content = "#!/bin/sh\n" + code
        with open("container_script.sh", "w", newline='\n') as f:
            f.write(script_content)

        try:
            subprocess.run(["docker", "cp", "container_script.sh", f"{container_name}:/container_script.sh"], check=True)
            subprocess.run(["docker", "exec", container_name, "chmod", "+x", "/container_script.sh"], check=True)

            result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_name], capture_output=True, text=True)
            if result.returncode != 0 or result.stdout.strip() != "true":
                self.master.after_idle(lambda: self.log_to_file(f"Container {container_name} is not running.\n"))
                return

            self.master.after_idle(lambda: self.log_to_file("Executing code...\n"))

            command = f"docker exec {container_name} sh -c /container_script.sh"
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            self.output_queue = queue.Queue()
            self.is_running = True
            
            def enqueue_output(out, queue):
                for line in iter(out.readline, ''):
                    queue.put(line)
                out.close()

            threading.Thread(target=enqueue_output, args=(process.stdout, self.output_queue), daemon=True).start()
            threading.Thread(target=enqueue_output, args=(process.stderr, self.output_queue), daemon=True).start()

            self.update_output(process)

        except Exception as e:
            self.log_to_file(f"Error: {str(e)}\n")
    
    def update_output(self, process):
        try:
            lines = []
            while self.is_running:
                try:
                    # 한 번에 최대 100줄만 처리
                    for _ in range(100):
                        line = self.output_queue.get_nowait()
                        lines.append(line)
                        if len(lines) >= 10:
                            self.log_to_file(''.join(lines))
                            lines = []
                except queue.Empty:
                    if lines:
                        self.log_to_file(''.join(lines))
                        lines = []
                    if process.poll() is not None:
                        self.is_running = False
                    else:
                        # 더 짧은 간격으로 업데이트
                        self.master.after(10, lambda: self.update_output(process))
                    return

            if process.returncode == 0:
                self.log_to_file("Code executed successfully.\n")
            else:
                self.log_to_file("Code execution failed.\n")

        except Exception as e:
            self.log_to_file(f"Error in update_output: {str(e)}\n")

    def enqueue_output(self, out, queue):
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()

    def stop_container(self):
        if self.container_listbox.curselection():
            selected_container = self.container_listbox.get(self.container_listbox.curselection())
            try:
                subprocess.run(["docker", "stop", selected_container], check=True)
                self.result_text.insert(tk.END, f"Stopped container: {selected_container}\n")
                self.update_container_list()
            except subprocess.CalledProcessError:
                self.result_text.insert(tk.END, f"Failed to stop container: {selected_container}\n")


if __name__ == "__main__":
    root = tk.Tk()
    docker_gui = DockerGUI(root)
    root.mainloop()
