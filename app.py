import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import re

class VocabFilterApp:
    def __init__(self, root):
        self.root = root
        # 正式更新软件名称与版本号
        self.root.title("IELTS ContextVocab (V1.0.0)") 
        self.root.geometry("1200x900")
        
        # --- 路径配置 ---
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.vocab_dir = os.path.join(self.base_dir, "Daily_Plan_Numbered")
        self.passage_dir = os.path.join(self.base_dir, "Daily_Plan_Passages")
        self.progress_file = os.path.join(self.base_dir, "learning_progress.json")
        self.config_file = os.path.join(self.base_dir, "app_config.json")
        
        # --- 数据存储 ---
        self.current_day_file = ""   
        self.file_list = []          
        self.target_words = set()    
        self.known_words = set()     
        self.essay_text = ""         
        self.all_progress_data = {}
        
        # 统计数据缓存
        self.stats_missing_count = 0
        self.stats_present_count = 0
        
        # 初始化流程
        self.check_directories()
        self.load_all_progress()
        self.setup_ui()
        self.refresh_file_list() 
        self.load_last_session() 

    def check_directories(self):
        """检查必要文件夹"""
        for d in [self.vocab_dir, self.passage_dir]:
            if not os.path.exists(d):
                os.makedirs(d)

    def setup_ui(self):
        # 1. 顶部导航与控制栏
        nav_frame = tk.Frame(self.root, pady=12, padx=15, bg="#f8f9fa", relief="flat")
        nav_frame.pack(fill="x")
        
        # 左侧：导航按钮区
        btn_frame = tk.Frame(nav_frame, bg="#f8f9fa")
        btn_frame.pack(side="left")

        tk.Button(btn_frame, text="<", command=self.prev_day, width=3, bg="white", relief="groove").pack(side="left", padx=2)
        
        self.day_var = tk.StringVar()
        self.day_combo = ttk.Combobox(btn_frame, textvariable=self.day_var, width=28, font=("Consolas", 10), state="readonly")
        self.day_combo.pack(side="left", padx=5)
        self.day_combo.bind("<<ComboboxSelected>>", self.on_day_selected)
        
        tk.Button(btn_frame, text=">", command=self.next_day, width=3, bg="white", relief="groove").pack(side="left", padx=2)
        
        # 功能按钮
        tk.Button(btn_frame, text="📤 导出生词", command=self.export_unknown_words, bg="#e3f2fd", relief="groove").pack(side="left", padx=15)

        # 右侧：统计信息栏
        stats_frame = tk.Frame(nav_frame, bg="#f8f9fa")
        stats_frame.pack(side="right")

        self.stats_label = tk.Label(
            stats_frame, 
            text="准备就绪", 
            font=("Segoe UI", 10), 
            bg="#f8f9fa", fg="#495057"
        )
        self.stats_label.pack(side="right", padx=5)

        # 2. 文本显示区
        text_frame = tk.Frame(self.root)
        text_frame.pack(expand=True, fill="both", padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.text_area = tk.Text(
            text_frame, 
            wrap="word", 
            font=("Georgia", 14),     
            spacing1=10, spacing2=5, spacing3=5,
            padx=30, pady=30,
            yscrollcommand=scrollbar.set,
            bg="white",
            selectbackground="#e9ecef"
        )
        self.text_area.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.text_area.yview)

        # 样式定义
        self.text_area.tag_configure("highlight", font=("Georgia", 14, "bold"), foreground="#d9534f", underline=True)
        self.text_area.tag_configure("known", font=("Georgia", 14, "normal"), foreground="#adb5bd", underline=False)
        self.text_area.tag_configure("separator", font=("Microsoft YaHei", 11, "bold"), foreground="#868e96", spacing1=30, spacing3=15, justify='center')
        
        # 事件绑定
        for tag in ["highlight", "known"]:
            self.text_area.tag_bind(tag, "<Enter>", lambda e: self.text_area.config(cursor="hand2"))
            self.text_area.tag_bind(tag, "<Leave>", lambda e: self.text_area.config(cursor=""))
            self.text_area.tag_bind(tag, "<Button-1>", self.on_left_click)
        
        self.text_area.bind("<Button-3>", self.on_right_click)

    def refresh_file_list(self):
        """加载文件列表"""
        try:
            self.file_list = [f for f in os.listdir(self.vocab_dir) if f.endswith(".txt")]
            self.file_list.sort() 
            self.day_combo['values'] = self.file_list
        except Exception as e:
            messagebox.showerror("错误", f"读取目录失败: {e}")

    def load_last_session(self):
        """恢复上次会话状态"""
        last_file = ""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    last_file = config.get("last_selected_file", "")
            except: pass
        
        if last_file and last_file in self.file_list:
            self.day_combo.set(last_file)
            self.on_day_selected(None)
        elif self.file_list:
            self.day_combo.current(0)
            self.on_day_selected(None)

    def save_session_state(self):
        """保存当前会话"""
        config = {"last_selected_file": self.current_day_file}
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)

    def prev_day(self):
        """上一天按钮逻辑"""
        current_idx = self.day_combo.current()
        if current_idx > 0:
            self.day_combo.current(current_idx - 1)
            self.on_day_selected(None)
        else:
            messagebox.showinfo("提示", "已经是第一天了")

    def next_day(self):
        """下一天按钮逻辑"""
        current_idx = self.day_combo.current()
        if current_idx < len(self.file_list) - 1:
            self.day_combo.current(current_idx + 1)
            self.on_day_selected(None)
        else:
            messagebox.showinfo("提示", "已经是最后一天了")

    def on_day_selected(self, event):
        """选择具体打卡日期后的自动加载逻辑"""
        vocab_filename = self.day_var.get()
        if not vocab_filename: return
        
        self.current_day_file = vocab_filename
        self.save_session_state() 
        
        # 加载词表
        vocab_path = os.path.join(self.vocab_dir, vocab_filename)
        if os.path.exists(vocab_path):
            with open(vocab_path, 'r', encoding='utf-8') as f:
                self.target_words = {line.strip().lower() for line in f if line.strip()}
        
        # 恢复记忆进度
        if self.current_day_file in self.all_progress_data:
            saved_known = set(self.all_progress_data[self.current_day_file].get("known", []))
            self.known_words = saved_known.intersection(self.target_words)
        else:
            self.known_words = set()

        # 自动加载短文
        base_name = os.path.splitext(vocab_filename)[0]
        passage_filename = f"{base_name}_Passage.txt"
        passage_path = os.path.join(self.passage_dir, passage_filename)
        
        if os.path.exists(passage_path):
            with open(passage_path, 'r', encoding='utf-8') as f:
                self.essay_text = f.read()
            self.render_text() 
        else:
            self.essay_text = f"❌ 未找到短文文件: {passage_filename}"
            self.render_text() 

    def export_unknown_words(self):
        """导生词本文件"""
        if not self.target_words:
            messagebox.showinfo("提示", "当前没有加载词表")
            return
            
        unknown_list = sorted(list(self.target_words - self.known_words))
        
        if not unknown_list:
            messagebox.showinfo("恭喜", "当前列表中的单词已全部掌握，无需导出！")
            return
            
        default_name = f"Unknown_{os.path.splitext(self.current_day_file)[0]}.txt"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt")],
            initialfile=default_name, title="导出生词本"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(unknown_list))
                messagebox.showinfo("成功", f"已导出 {len(unknown_list)} 个生词到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def render_text(self):
        """核心渲染：高亮、补全、统计"""
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", self.essay_text)
        
        if self.essay_text.startswith("❌"):
            self.text_area.config(state="disabled")
            return

        essay_lower = self.essay_text.lower()
        present_words = set()
        missing_words = []

        for word in self.target_words:
            if word in essay_lower:
                present_words.add(word)
            else:
                missing_words.append(word)

        self.stats_present_count = len(present_words)
        self.stats_missing_count = len(missing_words)

        # 高亮文中单词 (首现逻辑)
        for word in present_words:
            tag_to_use = "known" if word in self.known_words else "highlight"
            start_pos = "1.0"
            while True:
                idx = self.text_area.search(word, start_pos, stopindex=tk.END, nocase=True)
                if not idx: break
                
                end_idx = f"{idx}+{len(word)}c"
                prev_char = self.text_area.get(f"{idx}-1c", idx)
                next_char = self.text_area.get(end_idx, f"{end_idx}+1c")
                
                if (not prev_char.isalpha()) and (not next_char.isalpha()):
                    self.text_area.tag_add(tag_to_use, idx, end_idx)
                    break 
                start_pos = f"{idx}+1c"

        # 补全缺失词汇
        if missing_words:
            missing_words.sort()
            self.text_area.insert(tk.END, "\n", "normal")
            separator_text = f"———  以下单词未在文中出现 ({len(missing_words)}个)  ———\n"
            self.text_area.insert(tk.END, separator_text, "separator")
            
            for word in missing_words:
                tag_to_use = "known" if word in self.known_words else "highlight"
                self.text_area.insert(tk.END, word, tag_to_use)
                self.text_area.insert(tk.END, "    ", "normal") 
        
        self.text_area.config(state="disabled")
        self.refresh_stats()

    def on_left_click(self, event):
        """鼠标左键切换记忆状态"""
        click_index = self.text_area.index(f"@{event.x},{event.y}")
        tags = self.text_area.tag_names(click_index)
        
        target_tag = None
        if "highlight" in tags: target_tag = "highlight"
        elif "known" in tags: target_tag = "known"
            
        if target_tag:
            range_start, range_end = self.text_area.tag_prevrange(target_tag, f"{click_index}+1c")
            clicked_word = self.text_area.get(range_start, range_end).strip().lower()
            
            self.text_area.config(state="normal")
            self.text_area.tag_remove(target_tag, range_start, range_end)
            
            if target_tag == "highlight":
                self.text_area.tag_add("known", range_start, range_end)
                self.known_words.add(clicked_word)
            else:
                self.text_area.tag_add("highlight", range_start, range_end)
                if clicked_word in self.known_words:
                    self.known_words.remove(clicked_word)
            
            self.text_area.config(state="disabled")
            self.save_progress()
            self.refresh_stats()

    def on_right_click(self, event):
        """鼠标右键快速复制单词"""
        try:
            click_index = self.text_area.index(f"@{event.x},{event.y}")
            word_start = self.text_area.index(f"{click_index} wordstart")
            word_end = self.text_area.index(f"{click_index} wordend")
            selected_word = self.text_area.get(word_start, word_end).strip()
            
            if selected_word:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_word)
                self.root.update()
                
                orig_text = self.stats_label.cget("text")
                self.stats_label.config(text=f"📋 已复制: {selected_word}", fg="#007bff")
                self.root.after(1000, lambda: self.refresh_stats()) 
                
        except Exception as e:
            print(f"Copy failed: {e}")

    def load_all_progress(self):
        """加载历史进度"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.all_progress_data = json.load(f)
            except: pass

    def save_progress(self):
        """保存当前进度"""
        if not self.current_day_file: return
        self.all_progress_data[self.current_day_file] = {
            "total": len(self.target_words),
            "known": list(self.known_words),
            "unknown": list(self.target_words - self.known_words)
        }
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_progress_data, f, ensure_ascii=False, indent=2)

    def refresh_stats(self):
        """刷新右上角统计数据栏"""
        total = len(self.target_words)
        known = len(self.known_words)
        
        msg = (f"📚 词表总数: {total}   |   "
               f"✅ 文中覆盖: {self.stats_present_count}   |   "
               f"⚠️ 文中缺失: {self.stats_missing_count}   |   "
               f"🧠 已掌握: {known}/{total}")
        
        self.stats_label.config(text=msg, fg="#495057")

if __name__ == "__main__":
    root = tk.Tk()
    app = VocabFilterApp(root)
    root.mainloop()