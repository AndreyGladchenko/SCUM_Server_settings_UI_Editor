import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def get_resource_path(filename):
    """Get absolute path to resource (for default.ini and icon.ico)"""
    # 1. Check next to executable/script
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    path_near = os.path.join(base_path, filename)
    if os.path.exists(path_near):
        return path_near

    # 2. Check in _MEIPASS (if bundled)
    try:
        meipass_path = sys._MEIPASS
        path_mei = os.path.join(meipass_path, filename)
        if os.path.exists(path_mei):
            return path_mei
    except AttributeError:
        pass
        
    return path_near # fallback

def get_config_path(filename):
    """Path to read/write config (always next to executable/script)"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def parse_ini(filepath):
    data = {}
    if not os.path.exists(filepath):
        return data
        
    current_section = None
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith(';'):
                continue
            if line_str.startswith('[') and line_str.endswith(']'):
                current_section = line_str[1:-1]
                data[current_section] = {}
            elif '=' in line_str and current_section:
                parts = line_str.split('=', 1)
                key = parts[0].strip()
                val_comment = parts[1].strip()
                
                if '#' in val_comment:
                    val_parts = val_comment.split('#', 1)
                    val = val_parts[0].strip()
                    comment = val_parts[1].strip()
                else:
                    val = val_comment
                    comment = ""
                
                data[current_section][key] = {"value": val, "comment": comment}
    return data

def detect_type(val_str):
    if val_str.lower() in ('true', 'false'):
        return 'bool'
    try:
        int(val_str)
        return 'int'
    except ValueError:
        try:
            float(val_str)
            return 'float'
        except ValueError:
            return 'str'

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="#2b2b2b")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        # When canvas is resized, resize the inner frame width
        canvas.bind(
            '<Configure>',
            lambda e: canvas.itemconfig(frame_id, width=e.width)
        )

        frame_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        def _bind_mouse(_):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_mouse(_):
            canvas.unbind_all("<MouseWheel>")
        
        self.scrollable_frame.bind('<Enter>', _bind_mouse)
        self.scrollable_frame.bind('<Leave>', _unbind_mouse)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("SCUM Server Settings Editor")
        self.geometry("800x600")
        self.minsize(500, 400)
        
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            
        self.default_ini_path = get_resource_path("default.ini")
        self.server_ini_path = get_config_path("ServerSettings.ini")
        
        self.presets_dir = get_config_path("presets")
        os.makedirs(self.presets_dir, exist_ok=True)
        
        if not os.path.exists(self.default_ini_path):
            messagebox.showerror("Error", f"Could not find default.ini at {self.default_ini_path}")
            self.destroy()
            return
            
        if not os.path.exists(self.server_ini_path):
            try:
                # Create empty file or copy without comments.
                # A simple copy is fine since ServerSettings might not have internal comments.
                shutil.copyfile(self.default_ini_path, self.server_ini_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create ServerSettings.ini:\n{e}")
                
        self.default_data = parse_ini(self.default_ini_path)
        self.user_data = parse_ini(self.server_ini_path)
        
        # Merge new keys from ServerSettings.ini into default_data
        for section, keys_dict in self.user_data.items():
            if section not in self.default_data:
                self.default_data[section] = {}
            for key, info in keys_dict.items():
                if key not in self.default_data[section]:
                    self.default_data[section][key] = {"value": info["value"], "comment": ""}
        
        self.vars = {}
        self.apply_dark_theme()
        self.build_ui()
        
    def apply_dark_theme(self):
        self.tk_setPalette(background='#2b2b2b', foreground='#d1d1d1', activeBackground='#404040', activeForeground='#ffffff')
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
            
        bg_color = "#2b2b2b"
        fg_color = "#d1d1d1"
        btn_bg = "#404040"
        btn_active = "#555555"
        entry_bg = "#3c3c3c"
        
        style.configure('.', background=bg_color, foreground=fg_color, borderwidth=1)
        style.map('.', background=[('active', btn_active)])
        
        style.configure('TNotebook', background=bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', background=btn_bg, foreground=fg_color, padding=[10, 5], borderwidth=0)
        style.map('TNotebook.Tab', background=[('selected', btn_active)], foreground=[('selected', '#ffffff')])
        
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe', background=bg_color, foreground=fg_color, bordercolor=btn_bg)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
        
        style.configure('TButton', background=btn_bg, foreground=fg_color, borderwidth=0, padding=5)
        style.map('TButton', background=[('active', btn_active), ('pressed', '#1a1a1a')], foreground=[('active', '#ffffff')])
        
        style.configure('TEntry', fieldbackground=entry_bg, foreground=fg_color, insertcolor=fg_color, borderwidth=0)
        style.map('TEntry', fieldbackground=[('focus', '#454545')])
        
        style.configure('TCombobox', fieldbackground=entry_bg, background=btn_bg, foreground=fg_color, arrowcolor=fg_color)
        style.map('TCombobox', fieldbackground=[('readonly', entry_bg)])
        
        style.configure('TCheckbutton', background=bg_color, foreground=fg_color)
        style.map('TCheckbutton', background=[('active', bg_color)])
        
        style.configure('Vertical.TScrollbar', background=btn_bg, troughcolor=bg_color, arrowcolor=fg_color)
        style.map('Vertical.TScrollbar', background=[('active', btn_active)])
        
    def validate_number(self, val_type, P):
        if P == "" or P == "-":
            return True
        if val_type == 'int':
            try:
                int(P)
                return True
            except ValueError:
                return False
        elif val_type == 'float':
            try:
                float(P)
                return True
            except ValueError:
                return False
        return True

    def build_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Presets Tab
        preset_tab = ttk.Frame(self.notebook)
        self.notebook.add(preset_tab, text="Presets")
        
        # UI for loading/refreshing/deleting
        top_frame = ttk.LabelFrame(preset_tab, text="Управление пресетами", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Пресет:").grid(row=0, column=0, padx=5, pady=5)
        self.preset_combo = ttk.Combobox(top_frame, state="readonly", width=25)
        self.preset_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(top_frame, text="Загрузить preset", command=self.load_preset).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(top_frame, text="Обновить список", command=self.scan_presets).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(top_frame, text="Удалить preset", command=self.delete_preset).grid(row=0, column=4, padx=5, pady=5)
        
        # UI for saving
        bottom_frame = ttk.LabelFrame(preset_tab, text="Сохранение пресета", padding=10)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(bottom_frame, text="Введите имя preset:").grid(row=0, column=0, padx=5, pady=5)
        self.new_preset_entry = ttk.Entry(bottom_frame, width=25)
        self.new_preset_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(bottom_frame, text="Сохранить", command=self.save_preset).grid(row=0, column=2, padx=5, pady=5)
        
        # Image block
        image_path = get_resource_path("scum.jpg")
        if os.path.exists(image_path):
            if HAS_PIL:
                try:
                    img = Image.open(image_path)
                    img.thumbnail((400, 200)) # Resize maintaining aspect ratio
                    self.scum_img = ImageTk.PhotoImage(img)
                    img_lbl = ttk.Label(preset_tab, image=self.scum_img)
                    img_lbl.pack(pady=10)
                except Exception as e:
                    print(f"Failed to load scum.jpg: {e}")
            else:
                ttk.Label(preset_tab, text="[ Для отображения scum.jpg установите библиотеку Pillow (pip install Pillow) ]", foreground="red").pack(pady=10)
        
        vcmd_int = (self.register(lambda P: self.validate_number('int', P)), '%P')
        vcmd_float = (self.register(lambda P: self.validate_number('float', P)), '%P')
        
        for section, keys_dict in self.default_data.items():
            self.vars[section] = {}
            
            tab = ScrollableFrame(self.notebook)
            self.notebook.add(tab, text=section)
            
            inner = tab.scrollable_frame
            inner.columnconfigure(1, weight=1)
            
            row = 0
            for key, info in keys_dict.items():
                default_val = info["value"]
                comment = info["comment"]
                
                # Overwrite with user setting if exists
                current_val = default_val
                if section in self.user_data and key in self.user_data[section]:
                    current_val = self.user_data[section][key]["value"]
                    
                val_type = detect_type(default_val)
                
                lbl = ttk.Label(inner, text=key, font=("Segoe UI", 10, "bold"))
                lbl.grid(row=row, column=0, sticky="w", padx=(10, 5), pady=(10, 0))
                
                if val_type == 'bool':
                    is_true = current_val.lower() == 'true'
                    var = tk.BooleanVar(value=is_true)
                    self.vars[section][key] = var
                    chk = ttk.Checkbutton(inner, variable=var, text="Enabled/Disabled")
                    chk.grid(row=row, column=1, sticky="w", padx=5, pady=(10, 0))
                else:
                    var = tk.StringVar(value=current_val)
                    self.vars[section][key] = var
                    entry = ttk.Entry(inner, textvariable=var)
                    if val_type == 'int':
                        entry.config(validate='key', validatecommand=vcmd_int)
                    elif val_type == 'float':
                        entry.config(validate='key', validatecommand=vcmd_float)
                    entry.grid(row=row, column=1, sticky="ew", padx=5, pady=(10, 0))
                
                row += 1
                
                if comment:
                    desc_lbl = ttk.Label(inner, text=comment, font=("Segoe UI", 9, "italic"), foreground="#aaaaaa")
                    desc_lbl.grid(row=row, column=0, columnspan=2, sticky="w", padx=(20, 5), pady=(0, 5))
                    row += 1
                    
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        save_btn = ttk.Button(btn_frame, text="Сохранить", command=self.save_settings)
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        exit_btn = ttk.Button(btn_frame, text="Выход", command=self.destroy)
        exit_btn.pack(side=tk.RIGHT)
        
        self.scan_presets()
        
    def scan_presets(self):
        presets = []
        if os.path.exists(self.presets_dir):
            for entry in os.listdir(self.presets_dir):
                full_path = os.path.join(self.presets_dir, entry)
                if os.path.isdir(full_path):
                    if os.path.isfile(os.path.join(full_path, "ServerSettings.ini")):
                        presets.append(entry)
        self.preset_combo['values'] = presets
        if presets:
            self.preset_combo.current(0)
        else:
            self.preset_combo.set('')

    def load_preset(self):
        preset_name = self.preset_combo.get()
        if not preset_name:
            messagebox.showwarning("Внимание", "Выберите пресет для загрузки")
            return
            
        ini_path = os.path.join(self.presets_dir, preset_name, "ServerSettings.ini")
        if not os.path.exists(ini_path):
            messagebox.showerror("Ошибка", f"Файл {ini_path} не найден")
            return
            
        preset_data = parse_ini(ini_path)
        for section, keys_dict in preset_data.items():
            if section in self.vars:
                for key, info in keys_dict.items():
                    if key in self.vars[section]:
                        var = self.vars[section][key]
                        val_str = info["value"]
                        if isinstance(var, tk.BooleanVar):
                            var.set(val_str.lower() == 'true')
                        else:
                            var.set(val_str)
                            
        messagebox.showinfo("Успех", f"Пресет '{preset_name}' успешно загружен")

    def delete_preset(self):
        preset_name = self.preset_combo.get()
        if not preset_name:
            return
            
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить пресет '{preset_name}'?"):
            target_dir = os.path.join(self.presets_dir, preset_name)
            try:
                shutil.rmtree(target_dir)
                self.scan_presets()
                messagebox.showinfo("Успех", "Пресет удален")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить пресет:\n{e}")

    def save_preset(self):
        preset_name = self.new_preset_entry.get().strip()
        if not preset_name:
            messagebox.showwarning("Внимание", "Введите имя пресета")
            return
            
        target_dir = os.path.join(self.presets_dir, preset_name)
        ini_path = os.path.join(target_dir, "ServerSettings.ini")
        
        if os.path.exists(ini_path):
            if not messagebox.askyesno("Перезапись", f"Пресет '{preset_name}' уже существует. Перезаписать?"):
                return
                
        os.makedirs(target_dir, exist_ok=True)
        
        try:
            with open(ini_path, 'w', encoding='utf-8') as f:
                for section, keys_dict in self.vars.items():
                    f.write(f"[{section}]\n")
                    for key, var in keys_dict.items():
                        if isinstance(var, tk.BooleanVar):
                            val_str = "True" if var.get() else "False"
                        else:
                            val_str = var.get()
                        
                        f.write(f"{key}={val_str}\n")
                    f.write("\n")
            
            self.scan_presets()
            self.preset_combo.set(preset_name)
            messagebox.showinfo("Успех", f"Пресет '{preset_name}' сохранен")
            self.new_preset_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить пресет:\n{e}")
        
    def save_settings(self):
        try:
            with open(self.server_ini_path, 'w', encoding='utf-8') as f:
                for section, keys_dict in self.vars.items():
                    f.write(f"[{section}]\n")
                    for key, var in keys_dict.items():
                        if isinstance(var, tk.BooleanVar):
                            val_str = "True" if var.get() else "False"
                        else:
                            val_str = var.get()
                            
                        f.write(f"{key}={val_str}\n")
                    f.write("\n")
            messagebox.showinfo("Сохранено", "Настройки успешно сохранены в ServerSettings.ini")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
