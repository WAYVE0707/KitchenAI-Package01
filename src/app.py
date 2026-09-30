import base64
import copy
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    import psutil
except ImportError:
    psutil = None

APP_NAME = "Kitchen AI Designer"
APP_VERSION = "1.0.0-package01"
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
OLLAMA_URL = os.environ.get("KITCHENAI_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def app_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = root / "KitchenAI"
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = app_data_dir()
PROJECTS_DIR = DATA_DIR / "Projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def slugify(value):
    value = re.sub(r"[^\w\- ]+", "", value, flags=re.UNICODE).strip().replace(" ", "_")
    return value[:50] or "Project"


def new_object_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def default_project(name="Новая кухня"):
    ts = now_iso()
    return {
        "schema_version": "1.0",
        "project_id": str(uuid.uuid4()),
        "name": name,
        "created_at": ts,
        "updated_at": ts,
        "version": 1,
        "room": {"units": "mm", "width": None, "depth": None, "height": None},
        "walls": [], "doors": [], "windows": [], "cabinets": [], "appliances": [],
        "countertops": [], "materials": [], "references": [],
        "lighting": {}, "camera": {},
        "objects": {},
        "history": [],
        "chat": []
    }


class ProjectStore:
    def __init__(self):
        self.projects = {}
        self.refresh()

    def refresh(self):
        self.projects = {}
        for p in sorted(PROJECTS_DIR.iterdir() if PROJECTS_DIR.exists() else [], key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_dir():
                f = p / "project.kitchen.json"
                if f.exists():
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        self.projects[data["project_id"]] = data
                    except Exception:
                        pass

    def path_for(self, project):
        return PROJECTS_DIR / f"{slugify(project['name'])}_{project['project_id'][:8]}"

    def save(self, project, snapshot=True):
        project = copy.deepcopy(project)
        project["updated_at"] = now_iso()
        folder = self.path_for(project)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "references").mkdir(exist_ok=True)
        (folder / "renders").mkdir(exist_ok=True)
        versions = folder / "versions"
        versions.mkdir(exist_ok=True)
        if snapshot:
            project["version"] = int(project.get("version", 0)) + 1
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            atomic_write_json(versions / f"v{project['version']:04d}_{stamp}.json", project)
        atomic_write_json(folder / "project.kitchen.json", project)
        self.projects[project["project_id"]] = project
        return project

    def load(self, project_id):
        return copy.deepcopy(self.projects[project_id])

    def create(self, name):
        p = default_project(name)
        return self.save(p)

    def add_reference(self, project, source_path):
        folder = self.path_for(project)
        refs = folder / "references"
        refs.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        dest = refs / f"{uuid.uuid4().hex[:8]}_{src.name}"
        shutil.copy2(src, dest)
        project.setdefault("references", []).append({
            "id": new_object_id("REF"), "filename": dest.name,
            "source_name": src.name, "path": str(dest.relative_to(folder)), "added_at": now_iso()
        })
        return project

    def versions(self, project):
        folder = self.path_for(project) / "versions"
        return sorted(folder.glob("v*.json"), reverse=True) if folder.exists() else []

    def restore_version(self, project, version_file):
        data = json.loads(Path(version_file).read_text(encoding="utf-8"))
        data["updated_at"] = now_iso()
        data["history"] = project.get("history", []) + [{"action": "restore", "from": Path(version_file).name, "at": now_iso()}]
        return self.save(data, snapshot=True)


class OllamaClient:
    def __init__(self, base_url=OLLAMA_URL):
        self.base_url = base_url.rstrip("/")

    def _request(self, path, payload=None, timeout=60):
        url = self.base_url + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {e.code}: {detail[:500]}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Не удалось подключиться к Ollama: {e.reason}") from e
        except TimeoutError as e:
            raise RuntimeError("Таймаут Ollama") from e

    def tags(self):
        return self._request("/api/tags", timeout=10).get("models", [])

    def chat(self, model, messages, images=None, options=None):
        msgs = copy.deepcopy(messages)
        if images and msgs:
            msgs[-1]["images"] = images
        payload = {"model": model, "messages": msgs, "stream": False}
        if options:
            payload["options"] = options
        return self._request("/api/chat", payload, timeout=600).get("message", {}).get("content", "")


SYSTEM_PROMPT = '''Ты — локальный AI-ассистент Kitchen AI Designer Package 01. Отвечай по-русски.
Источник истины проекта — структурированный Kitchen JSON, а не изображения.
На этом этапе не выдумывай 3D-рендер и не утверждай, что Blender построил сцену.
Помогай описывать и структурировать кухню, сохранять стабильные object IDs и точечно менять свойства.
Если пользователь задаёт параметры кухни, в конце ответа добавляй блок <KITCHEN_PATCH> с JSON-массивом операций.
Формат операции: {"target":"ROOM_01|...","property":"room.width|...","value":...}.
Если изменения не относятся к структуре проекта, блок можно не добавлять.
Никогда не удаляй объекты без явного запроса пользователя.
'''


def parse_patch(text):
    m = re.search(r"<KITCHEN_PATCH>\s*(.*?)\s*</KITCHEN_PATCH>", text, re.S | re.I)
    if not m:
        return [], text.strip()
    raw = m.group(1).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("changes", [])
        if not isinstance(data, list):
            return [], text.strip()
        return data, re.sub(r"\s*<KITCHEN_PATCH>.*?</KITCHEN_PATCH>\s*", "", text, flags=re.S | re.I).strip()
    except Exception:
        return [], text.strip()


def set_nested(obj, path, value):
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        if isinstance(cur, dict):
            cur = cur.setdefault(p, {})
        else:
            return False
    if isinstance(cur, dict):
        cur[parts[-1]] = value
        return True
    return False


def apply_changes(project, changes):
    applied = []
    for change in changes:
        target = str(change.get("target", "")).strip()
        prop = str(change.get("property", "")).strip()
        if not target or not prop:
            continue
        if target == "ROOM_01" and prop.startswith("room."):
            ok = set_nested(project, prop, change.get("value"))
        else:
            obj = project.setdefault("objects", {}).setdefault(target, {"id": target})
            ok = set_nested(obj, prop, change.get("value"))
        if ok:
            applied.append(change)
    if applied:
        project.setdefault("history", []).append({"action": "patch", "changes": applied, "at": now_iso()})
    return project, applied


def hardware_info():
    info = {"os": platform.platform(), "cpu": platform.processor() or platform.machine(), "ram_gb": None, "gpu": "Не определено", "vram_gb": None, "disk_free_gb": None}
    if psutil:
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        info["disk_free_gb"] = round(psutil.disk_usage(str(Path.home())).free / (1024 ** 3), 1)
    if os.name == "nt":
        try:
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"], text=True, timeout=5, stderr=subprocess.DEVNULL)
            gpus = [x.strip() for x in out.splitlines() if x.strip()]
            if gpus:
                info["gpu"] = "; ".join(gpus)
        except Exception:
            pass
    return info


def recommend_profile(hw):
    ram = hw.get("ram_gb") or 0
    gpu = (hw.get("gpu") or "").lower()
    if ram >= 32 or any(x in gpu for x in ["rtx 40", "rtx 50", "rx 7900", "rx 7800"]):
        return "Pro"
    if ram >= 16:
        return "Standard"
    return "Lite"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — Package 01")
        self.geometry("1280x820")
        self.minsize(980, 650)
        self.configure(bg="#15171b")
        self.store = ProjectStore()
        self.client = OllamaClient()
        self.project = None
        self.models = []
        self.model_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Готово")
        self.profile_var = tk.StringVar(value="Lite")
        self._setup_style()
        self._build_ui()
        self._load_or_create()
        # Low-end-safe default; the user can switch to Standard/Pro on stronger PCs.
        self.after(250, self.refresh_ollama)

    def _setup_style(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass
        style.configure("TFrame", background="#15171b")
        style.configure("TLabel", background="#15171b", foreground="#e8eaed")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#ffffff")
        style.configure("Muted.TLabel", foreground="#9aa0aa")
        style.configure("TButton", padding=(10, 7), background="#2a2e36", foreground="#ffffff")
        style.map("TButton", background=[("active", "#3a404b")])
        style.configure("TCombobox", fieldbackground="#20232a", background="#20232a", foreground="#ffffff")
        style.configure("Treeview", background="#1d2026", fieldbackground="#1d2026", foreground="#e8eaed", rowheight=28)
        style.configure("Treeview.Heading", background="#2a2e36", foreground="#ffffff")

    def _build_ui(self):
        top = ttk.Frame(self); top.pack(fill="x", padx=16, pady=(14, 8))
        ttk.Label(top, text="Kitchen AI Designer", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="Package 01 · local-first", style="Muted.TLabel").pack(side="left", padx=12)
        ttk.Button(top, text="Проверить железо", command=self.show_hardware).pack(side="right")
        ttk.Button(top, text="Обновить модели", command=self.refresh_ollama).pack(side="right", padx=8)

        body = ttk.Frame(self); body.pack(fill="both", expand=True, padx=16, pady=8)
        left = ttk.Frame(body, width=270); left.pack(side="left", fill="y", padx=(0, 10)); left.pack_propagate(False)
        ttk.Label(left, text="Проекты", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        self.project_list = tk.Listbox(left, bg="#1d2026", fg="#e8eaed", selectbackground="#39475d", relief="flat", highlightthickness=0, font=("Segoe UI", 10))
        self.project_list.pack(fill="both", expand=True)
        self.project_list.bind("<<ListboxSelect>>", self.on_project_select)
        ttk.Button(left, text="＋ Новый проект", command=self.new_project).pack(fill="x", pady=8)
        ttk.Button(left, text="Версии / откат", command=self.restore_version).pack(fill="x")

        center = ttk.Frame(body); center.pack(side="left", fill="both", expand=True)
        toolbar = ttk.Frame(center); toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, text="Модель Ollama:").pack(side="left")
        self.model_combo = ttk.Combobox(toolbar, textvariable=self.model_var, state="normal", width=32)
        self.model_combo.pack(side="left", padx=8)
        ttk.Label(toolbar, text="Профиль:").pack(side="left", padx=(16, 0))
        profile = ttk.Combobox(toolbar, textvariable=self.profile_var, values=["Lite", "Standard", "Pro"], state="readonly", width=12)
        profile.pack(side="left", padx=8)
        ttk.Button(toolbar, text="Сохранить", command=self.save_project).pack(side="right")
        ttk.Button(toolbar, text="Добавить план / фото", command=self.attach).pack(side="right", padx=8)

        chat_wrap = ttk.Frame(center); chat_wrap.pack(fill="both", expand=True)
        self.chat = tk.Text(chat_wrap, wrap="word", bg="#1b1e23", fg="#e8eaed", insertbackground="#ffffff", relief="flat", padx=16, pady=14, font=("Segoe UI", 11), state="disabled")
        scroll = ttk.Scrollbar(chat_wrap, command=self.chat.yview); self.chat.configure(yscrollcommand=scroll.set)
        self.chat.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        self.chat.tag_configure("user", foreground="#9dc7ff", spacing1=8)
        self.chat.tag_configure("assistant", foreground="#e8eaed", spacing1=8)
        self.chat.tag_configure("system", foreground="#8e96a3", spacing1=5)

        bottom = ttk.Frame(center); bottom.pack(fill="x", pady=(10, 0))
        self.input = tk.Text(bottom, height=4, bg="#20232a", fg="#ffffff", insertbackground="#ffffff", relief="flat", padx=12, pady=10, font=("Segoe UI", 11))
        self.input.pack(side="left", fill="both", expand=True)
        self.input.bind("<Control-Return>", lambda e: self.send_message())
        ttk.Button(bottom, text="Отправить\nCtrl+Enter", command=self.send_message).pack(side="right", padx=(8, 0), fill="y")

        right = ttk.Frame(body, width=280); right.pack(side="left", fill="y", padx=(10, 0)); right.pack_propagate(False)
        ttk.Label(right, text="Kitchen JSON", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        self.project_info = tk.Text(right, bg="#1b1e23", fg="#cfd5df", relief="flat", font=("Consolas", 9), state="disabled", wrap="none")
        self.project_info.pack(fill="both", expand=True)
        ttk.Label(right, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

    def _load_or_create(self):
        self.store.refresh()
        if self.store.projects:
            self.project = next(iter(self.store.projects.values()))
        else:
            self.project = self.store.create("Моя кухня")
        self.refresh_project_list()
        self.render_project()

    def refresh_project_list(self):
        self.project_list.delete(0, "end")
        self.project_ids = []
        for pid, p in self.store.projects.items():
            self.project_ids.append(pid)
            self.project_list.insert("end", p.get("name", pid))
        if self.project:
            try: self.project_list.selection_set(self.project_ids.index(self.project["project_id"]))
            except ValueError: pass

    def on_project_select(self, _event=None):
        sel = self.project_list.curselection()
        if not sel: return
        self.project = self.store.load(self.project_ids[sel[0]])
        self.render_project()

    def render_project(self):
        self.chat.configure(state="normal"); self.chat.delete("1.0", "end")
        for msg in self.project.get("chat", []):
            role = msg.get("role")
            text = msg.get("content", "")
            self.chat.insert("end", ("Вы" if role == "user" else "Kitchen AI") + ":\n", "user" if role == "user" else "assistant")
            self.chat.insert("end", text + "\n\n", "user" if role == "user" else "assistant")
        self.chat.configure(state="disabled"); self.chat.see("end")
        self.project_info.configure(state="normal"); self.project_info.delete("1.0", "end")
        display = {k: v for k, v in self.project.items() if k not in ("chat", "history")}
        self.project_info.insert("1.0", json.dumps(display, ensure_ascii=False, indent=2))
        self.project_info.configure(state="disabled")

    def new_project(self):
        name = simpledialog.askstring("Новый проект", "Название проекта:", parent=self)
        if not name: return
        self.project = self.store.create(name.strip())
        self.refresh_project_list(); self.render_project()

    def save_project(self):
        if not self.project: return
        self.project = self.store.save(self.project, snapshot=True)
        self.refresh_project_list(); self.render_project(); self.status_var.set(f"Сохранено · версия {self.project['version']}")

    def attach(self):
        if not self.project: return
        files = filedialog.askopenfilenames(title="Выберите план или фотографии", filetypes=[("Изображения/PDF/DXF", "*.png *.jpg *.jpeg *.webp *.pdf *.dxf"), ("Все файлы", "*.*")])
        if not files: return
        for f in files:
            try: self.project = self.store.add_reference(self.project, f)
            except Exception as e: messagebox.showerror("Вложение", f"Не удалось добавить {f}: {e}")
        self.save_project()

    def refresh_ollama(self):
        self.status_var.set("Проверка Ollama…")
        def work():
            try:
                models = self.client.tags()
                names = [m.get("name") for m in models if m.get("name")]
                self.after(0, lambda: self._models_ready(names))
            except Exception as e:
                self.after(0, lambda: self.status_var.set(str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _models_ready(self, names):
        self.models = names
        values = ["Auto"] + names
        self.model_combo["values"] = values
        if names:
            if self.model_var.get() not in values: self.model_var.set("Auto")
            self.status_var.set(f"Ollama подключена · {len(names)} моделей")
        else:
            self.status_var.set("Ollama подключена, моделей нет")


    def resolve_model(self, selected):
        if selected and selected.lower() != "auto":
            return selected
        if not self.models:
            return ""
        profile = self.profile_var.get()
        names = self.models
        preferred = []
        if profile == "Pro":
            preferred = ["qwen3.6", "qwen3", "qwen", "llama3.3", "llama3.1"]
        elif profile == "Standard":
            preferred = ["qwen3.6", "qwen3", "qwen", "llama3.1", "llama3"]
        else:
            preferred = ["qwen3", "qwen", "llama3.2", "llama3.1", "llama3"]
        for key in preferred:
            for name in names:
                if key in name.lower():
                    return name
        return names[0]

    def send_message(self):
        text = self.input.get("1.0", "end").strip()
        if not text: return
        model = self.resolve_model(self.model_var.get().strip())
        if not model:
            messagebox.showwarning("Ollama", "Выберите модель или дождитесь списка Ollama.")
            return
        self.input.delete("1.0", "end")
        self.project.setdefault("chat", []).append({"role": "user", "content": text, "at": now_iso()})
        self.render_project()
        self.status_var.set(f"Запрос к {model}…")
        self._set_input_enabled(False)
        threading.Thread(target=self._chat_worker, args=(model, text), daemon=True).start()

    def _set_input_enabled(self, enabled):
        self.input.configure(state="normal" if enabled else "disabled")

    def _chat_worker(self, model, text):
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in self.project.get("chat", [])[-20:]:
                if m.get("role") in ("user", "assistant"):
                    messages.append({"role": m["role"], "content": m["content"]})
            images = []
            for ref in self.project.get("references", [])[-4:]:
                if Path(ref.get("path", "")).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    p = self.store.path_for(self.project) / ref["path"]
                    if p.exists() and p.stat().st_size < 8_000_000:
                        images.append(base64.b64encode(p.read_bytes()).decode("ascii"))
            # The Lite profile is intended for low-end office PCs such as
            # i3-9100F + 8 GB RAM + GT 1030 2 GB. Force CPU inference
            # to avoid CUDA/PTX runner crashes and keep the GPU free.
            options = None
            if self.profile_var.get() == "Lite":
                options = {
                    "num_gpu": 0,
                    "num_ctx": 2048,
                    "num_batch": 32,
                    "num_thread": 4
                }

            reply = self.client.chat(model, messages, images=images or None, options=options)
            changes, clean = parse_patch(reply)
            self.after(0, lambda: self._chat_done(clean, changes))
        except Exception as e:
            self.after(0, lambda: self._chat_error(str(e)))

    def _chat_done(self, reply, changes):
        self.project, applied = apply_changes(self.project, changes)
        self.project.setdefault("chat", []).append({"role": "assistant", "content": reply, "at": now_iso(), "applied_changes": applied})
        self.project = self.store.save(self.project, snapshot=True)
        self.render_project(); self._set_input_enabled(True)
        self.status_var.set(f"Готово · применено изменений: {len(applied)}")

    def _chat_error(self, error):
        self.project.setdefault("chat", []).append({"role": "assistant", "content": "Ошибка: " + error, "at": now_iso()})
        self.render_project(); self._set_input_enabled(True); self.status_var.set("Ошибка запроса")

    def show_hardware(self):
        hw = hardware_info(); profile = recommend_profile(hw); self.profile_var.set(profile)
        msg = "\n".join([f"ОС: {hw['os']}", f"CPU: {hw['cpu']}", f"RAM: {hw['ram_gb']} GB", f"GPU: {hw['gpu']}", f"VRAM: {hw['vram_gb'] or 'не определено'}", f"Свободно на диске: {hw['disk_free_gb']} GB", f"Рекомендуемый профиль: {profile}"])
        messagebox.showinfo("Проверка железа", msg)

    def restore_version(self):
        if not self.project: return
        files = self.store.versions(self.project)
        if not files:
            messagebox.showinfo("Версии", "Сохранённых версий пока нет."); return
        win = tk.Toplevel(self); win.title("Версии проекта"); win.geometry("650x420"); win.configure(bg="#15171b")
        lb = tk.Listbox(win, bg="#1d2026", fg="#e8eaed", selectbackground="#39475d")
        lb.pack(fill="both", expand=True, padx=14, pady=14)
        for f in files: lb.insert("end", f.name)
        def restore():
            s = lb.curselection()
            if not s: return
            if not messagebox.askyesno("Откат", "Создать новую версию из выбранного состояния?", parent=win): return
            self.project = self.store.restore_version(self.project, files[s[0]])
            self.refresh_project_list(); self.render_project(); win.destroy()
        ttk.Button(win, text="Восстановить", command=restore).pack(pady=(0, 14))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
