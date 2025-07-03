import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk
from ctypes import CDLL, Structure, c_char_p, c_int, byref, POINTER, c_char
import os
import re

# --- CTYPES WRAPPER FOR C LIBRARY ---

class Suggestion(Structure):
    _fields_ = [("word", c_char * 50),
                ("dist", c_int)]

class CSpellChecker:
    def __init__(self, library_path):
        self.lib = None
        self.loaded = False

        print(f"Attempting to load C library from: {library_path}")
        try:
            self.lib = CDLL(library_path)
            print("C library loaded successfully.")
        except OSError as e:
            messagebox.showerror("Library Load Error", f"Could not load C library: {e}\n"
                                                      f"Please ensure '{os.path.basename(library_path)}' "
                                                       "is compiled correctly for your OS and architecture "
                                                       "and is in the same directory as gui.py.")
            return

        self.lib.load_dictionary.argtypes = [c_char_p]
        self.lib.load_dictionary.restype = c_int

        self.lib.is_word_correct.argtypes = [c_char_p]
        self.lib.is_word_correct.restype = c_int

        self.lib.get_suggestions.argtypes = [c_char_p, c_int, POINTER(Suggestion)]
        self.lib.get_suggestions.restype = c_int

        self.lib.cleanup.argtypes = []
        self.lib.cleanup.restype = None

    def load_dictionary(self, filename):
        if self.lib is None:
            print("C library not loaded, cannot load dictionary.")
            return False
        
        print(f"Calling C load_dictionary with: {filename}")
        success = self.lib.load_dictionary(filename.encode('utf-8'))
        self.loaded = bool(success)
        print(f"Dictionary load success: {self.loaded}")
        return self.loaded

    def is_word_correct(self, word):
        if not self.loaded or self.lib is None:
            return False
        return bool(self.lib.is_word_correct(word.encode('utf-8')))

    def get_suggestions(self, word, tolerance=2):
        if not self.loaded or self.lib is None:
            print(f"Skipping get_suggestions for '{word}': Library/dictionary not loaded.")
            return []

        suggestions_array = (Suggestion * 5)()
        
        print(f"Calling C get_suggestions for: '{word}' with tolerance {tolerance}")
        num_found = self.lib.get_suggestions(word.encode('utf-8'), tolerance, suggestions_array)
        print(f"C get_suggestions returned {num_found} results.")

        python_suggestions = []
        for i in range(num_found):
            decoded_word = suggestions_array[i].word.decode('utf-8')
            python_suggestions.append({
                "word": decoded_word,
                "dist": suggestions_array[i].dist
            })
            print(f"  Received C suggestion: {decoded_word} (dist: {suggestions_array[i].dist})")
        return python_suggestions

    def cleanup(self):
        if self.lib:
            print("Calling C cleanup function.")
            self.lib.cleanup()
        self.loaded = False
        self.lib = None

# --- MODERN TKINTER GUI APPLICATION ---

class SpellCheckerApp:
    def __init__(self, master):
        self.master = master
        master.title("✨ Smart Spell Checker")
        master.geometry("1000x750")
        master.minsize(800, 600)
        
        # Modern color scheme
        self.colors = {
            'primary': '#2E86AB',      # Modern blue
            'secondary': '#A23B72',    # Accent purple-pink
            'success': '#10B981',      # Green for correct
            'error': '#EF4444',        # Red for errors
           'warning': '#F59E0B',      # Orange for warnings
            'background': '#F8FAFC',   # Light gray background
            'surface': '#FFFFFF',      # White surfaces
            'text_primary': '#1F2937', # Dark gray text
            'text_secondary': '#6B7280', # Medium gray text
            'border': '#E5E7EB',       # Light border
            'hover': '#F3F4F6'         # Hover state
        }
        
        # Configure the main window
        master.configure(bg=self.colors['background'])
        
        # Configure modern styling
        self.setup_styles()
        
        # Main container with padding
        self.main_container = tk.Frame(master, bg=self.colors['background'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configure grid weights
        self.main_container.grid_rowconfigure(2, weight=3)  # Input area
        self.main_container.grid_rowconfigure(4, weight=4)  # Preview area
        self.main_container.grid_rowconfigure(6, weight=2)  # Suggestions area
        self.main_container.grid_columnconfigure(0, weight=2)
        self.main_container.grid_columnconfigure(1, weight=1)
        
        self.c_spell_checker = None
        
        # Set up file paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.name == 'posix':
            self.C_LIB_PATH = os.path.join(script_dir, 'spellcheckfunc.so')
        elif os.name == 'nt':
            self.C_LIB_PATH = os.path.join(script_dir, 'spellcheckfunc.dll')
        else:
            messagebox.showerror("OS Error", "Unsupported operating system for C library.")
            master.destroy()
            return

        self.DICT_PATH = os.path.join(script_dir, 'hi.txt')
        
        # Create the interface
        self.create_header()
        self.create_input_section()
        self.create_preview_section()
        self.create_suggestions_section()
        self.create_status_bar()
        
        # Initialize variables
        self.current_incorrect_word_obj = None
        self.current_original_token = None
        self.current_replacement_idx = -1
        
        # Load library and dictionary
        self._load_files_directly()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Add subtle animations
        self.setup_animations()

    def setup_styles(self):
        """Configure modern TTK styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure modern button style
        self.style.configure('Modern.TButton',
                           font=('Segoe UI', 10, 'bold'),
                           padding=(20, 10),
                           borderwidth=0,
                           focuscolor='none')
        
        self.style.map('Modern.TButton',
                      background=[('active', self.colors['primary']),
                                ('pressed', '#1E5F7A'),
                                ('!active', self.colors['primary'])],
                      foreground=[('active', 'white'),
                                ('pressed', 'white'),
                                ('!active', 'white')])
        
        # Secondary button style
        self.style.configure('Secondary.TButton',
                           font=('Segoe UI', 10),
                           padding=(15, 8),
                           borderwidth=1,
                           focuscolor='none')
        
        self.style.map('Secondary.TButton',
                      background=[('active', self.colors['hover']),
                                ('!active', self.colors['surface'])],
                      foreground=[('!active', self.colors['text_primary'])],
                      bordercolor=[('!active', self.colors['border'])])

    def create_header(self):
        """Create modern header with title and status"""
        header_frame = tk.Frame(self.main_container, bg=self.colors['background'])
        header_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 30))
        
        # Main title
        title_label = tk.Label(header_frame, 
                              text="✨ Smart Spell Checker",
                              font=('Segoe UI', 24, 'bold'),
                              fg=self.colors['text_primary'],
                              bg=self.colors['background'])
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_indicator = tk.Frame(header_frame, 
                                       width=12, height=12,
                                       bg=self.colors['warning'])
        self.status_indicator.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Reload button
        self.reload_btn = ttk.Button(header_frame,
                                   text="🔄 Reload Library",
                                   style='Secondary.TButton',
                                   command=self._load_files_directly)
        self.reload_btn.pack(side=tk.RIGHT, padx=(0, 15))

    def create_input_section(self):
        """Create modern input section"""
        # Input label and counter
        input_header = tk.Frame(self.main_container, bg=self.colors['background'])
        input_header.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        
        input_label = tk.Label(input_header,
                              text="📝 Enter your text:",
                              font=('Segoe UI', 14, 'bold'),
                              fg=self.colors['text_primary'],
                              bg=self.colors['background'])
        input_label.pack(side=tk.LEFT)
        
        self.char_counter = tk.Label(input_header,
                                   text="0 characters",
                                   font=('Segoe UI', 10),
                                   fg=self.colors['text_secondary'],
                                   bg=self.colors['background'])
        self.char_counter.pack(side=tk.RIGHT)
        
        # Input text area with modern styling
        input_container = tk.Frame(self.main_container, 
                                 bg=self.colors['surface'],
                                 relief=tk.FLAT,
                                 bd=2,
                                 highlightbackground=self.colors['border'],
                                 highlightthickness=2)
        input_container.grid(row=2, column=0, sticky='nsew', pady=(0, 20))
        
        self.sentence_text = scrolledtext.ScrolledText(
            input_container,
            wrap=tk.WORD,
            height=6,
            font=('Segoe UI', 12),
            bd=0,
            relief=tk.FLAT,
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['primary'],
            selectbackground=self.colors['primary'],
            selectforeground='white',
            padx=15,
            pady=15
        )
        self.sentence_text.pack(fill=tk.BOTH, expand=True)
        self.sentence_text.bind("<KeyRelease>", self.on_text_change)
        self.sentence_text.bind("<FocusIn>", lambda e: self.animate_focus(input_container, True))
        self.sentence_text.bind("<FocusOut>", lambda e: self.animate_focus(input_container, False))

    def create_preview_section(self):
        """Create modern preview section"""
        # Preview header
        preview_label = tk.Label(self.main_container,
                               text="👀 Live Preview:",
                               font=('Segoe UI', 14, 'bold'),
                               fg=self.colors['text_primary'],
                               bg=self.colors['background'])
        preview_label.grid(row=3, column=0, sticky='w', pady=(0, 10))
        
        # Stats panel
        self.create_stats_panel()
        
        # Preview container
        preview_container = tk.Frame(self.main_container,
                                   bg=self.colors['surface'],
                                   relief=tk.FLAT,
                                   bd=2,
                                   highlightbackground=self.colors['border'],
                                   highlightthickness=2)
        preview_container.grid(row=4, column=0, sticky='nsew', pady=(0, 20))
        preview_container.grid_rowconfigure(0, weight=1)
        preview_container.grid_columnconfigure(0, weight=1)
        
        # Canvas for scrollable content
        self.preview_canvas = tk.Canvas(preview_container,
                                      bg=self.colors['surface'],
                                      highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, sticky='nsew')
        
        # Scrollbar
        preview_scrollbar = ttk.Scrollbar(preview_container,
                                        orient=tk.VERTICAL,
                                        command=self.preview_canvas.yview)
        preview_scrollbar.grid(row=0, column=1, sticky='ns')
        self.preview_canvas.configure(yscrollcommand=preview_scrollbar.set)
        
        # Inner frame for word labels
        self.preview_inner_frame = tk.Frame(self.preview_canvas, bg=self.colors['surface'])
        self.canvas_window = self.preview_canvas.create_window(
            (0, 0), window=self.preview_inner_frame, anchor="nw"
        )
        
        # Bind events
        self.preview_canvas.bind('<Configure>', self.on_canvas_configure)
        self.preview_inner_frame.bind('<Configure>', 
            lambda e: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))

    def create_stats_panel(self):
        """Create statistics panel"""
        stats_frame = tk.Frame(self.main_container, bg=self.colors['background'])
        stats_frame.grid(row=3, column=1, sticky='new', padx=(20, 0), pady=(0, 10))
        
        # Stats cards
        self.create_stat_card(stats_frame, "Words", "0", self.colors['primary'], 0)
        self.create_stat_card(stats_frame, "Errors", "0", self.colors['error'], 1)
        self.create_stat_card(stats_frame, "Accuracy", "100%", self.colors['success'], 2)

    def create_stat_card(self, parent, title, value, color, row):
        """Create individual stat card"""
        card = tk.Frame(parent, bg=self.colors['surface'], relief=tk.FLAT, bd=1,
                       highlightbackground=self.colors['border'], highlightthickness=1)
        card.grid(row=row, column=0, sticky='ew', pady=2)
        card.grid_columnconfigure(0, weight=1)
        
        # Value
        value_label = tk.Label(card, text=value, font=('Segoe UI', 16, 'bold'),
                             fg=color, bg=self.colors['surface'])
        value_label.grid(row=0, column=0, pady=(10, 2))
        
        # Title
        title_label = tk.Label(card, text=title, font=('Segoe UI', 10),
                             fg=self.colors['text_secondary'], bg=self.colors['surface'])
        title_label.grid(row=1, column=0, pady=(0, 10))
        
        # Store references for updates
        if title == "Words":
            self.words_stat = value_label
        elif title == "Errors":
            self.errors_stat = value_label
        elif title == "Accuracy":
            self.accuracy_stat = value_label

    def create_suggestions_section(self):
        """Create modern suggestions section"""
        suggestions_label = tk.Label(self.main_container,
                                   text="💡 Suggestions:",
                                   font=('Segoe UI', 14, 'bold'),
                                   fg=self.colors['text_primary'],
                                   bg=self.colors['background'])
        suggestions_label.grid(row=5, column=0, sticky='w', pady=(0, 10))
        
        # Suggestions container
        suggestions_container = tk.Frame(self.main_container, bg=self.colors['background'])
        suggestions_container.grid(row=6, column=0, columnspan=2, sticky='nsew')
        suggestions_container.grid_rowconfigure(0, weight=1)
        suggestions_container.grid_columnconfigure(0, weight=2)
        suggestions_container.grid_columnconfigure(1, weight=1)
        
        # Suggestions list
        list_frame = tk.Frame(suggestions_container,
                            bg=self.colors['surface'],
                            relief=tk.FLAT,
                            bd=2,
                            highlightbackground=self.colors['border'],
                            highlightthickness=2)
        list_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        self.suggestions_listbox = tk.Listbox(
            list_frame,
            font=('Segoe UI', 11),
            bd=0,
            relief=tk.FLAT,
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['primary'],
            selectforeground='white',
            activestyle='none',
            highlightthickness=0
        )
        self.suggestions_listbox.grid(row=0, column=0, sticky='nsew', padx=15, pady=15)
        self.suggestions_listbox.bind("<<ListboxSelect>>", self.apply_suggestion)
        
        # Action buttons
        actions_frame = tk.Frame(suggestions_container, bg=self.colors['background'])
        actions_frame.grid(row=0, column=1, sticky='new')
        
        self.manual_replace_button = ttk.Button(
            actions_frame,
            text="✏️ Manual Replace",
            style='Secondary.TButton',
            command=self.manual_replace_word,
            state=tk.DISABLED
        )
        self.manual_replace_button.pack(fill=tk.X, pady=(0, 10))
        
        self.ignore_button = ttk.Button(
            actions_frame,
            text="🚫 Ignore Word",
            style='Secondary.TButton',
            state=tk.DISABLED
        )
        self.ignore_button.pack(fill=tk.X)

    def create_status_bar(self):
        """Create modern status bar"""
        self.status_frame = tk.Frame(self.master, bg=self.colors['surface'],
                                   height=40, relief=tk.FLAT,
                                   bd=1, highlightbackground=self.colors['border'],
                                   highlightthickness=1)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_frame.pack_propagate(False)
        
        self.status_text = tk.Label(self.status_frame,
                                  text="Initializing...",
                                  font=('Segoe UI', 10),
                                  fg=self.colors['text_secondary'],
                                  bg=self.colors['surface'],
                                  anchor=tk.W)
        self.status_text.pack(side=tk.LEFT, padx=15, pady=10)

    def setup_animations(self):
        """Setup subtle animations"""
        self.animation_states = {}

    def animate_focus(self, widget, focused):
        """Animate widget focus state"""
        if focused:
            widget.configure(highlightbackground=self.colors['primary'])
        else:
            widget.configure(highlightbackground=self.colors['border'])

    def on_text_change(self, event=None):
        """Handle text changes with live updates"""
        text = self.sentence_text.get("1.0", tk.END).strip()
        char_count = len(text)
        self.char_counter.config(text=f"{char_count} characters")
        
        # Debounced spell checking
        if hasattr(self, '_check_timer'):
            self.master.after_cancel(self._check_timer)
        self._check_timer = self.master.after(300, self.check_sentence)

    def update_stats(self, word_count, error_count):
        """Update statistics display"""
        accuracy = 100 if word_count == 0 else int(((word_count - error_count) / word_count) * 100)
        
        self.words_stat.config(text=str(word_count))
        self.errors_stat.config(text=str(error_count))
        self.accuracy_stat.config(text=f"{accuracy}%")
        
        # Update stat colors based on values
        if error_count == 0:
            self.errors_stat.config(fg=self.colors['success'])
            self.accuracy_stat.config(fg=self.colors['success'])
        else:
            self.errors_stat.config(fg=self.colors['error'])
            if accuracy >= 90:
                self.accuracy_stat.config(fg=self.colors['success'])
            elif accuracy >= 70:
                self.accuracy_stat.config(fg=self.colors['warning'])
            else:
                self.accuracy_stat.config(fg=self.colors['error'])

    def update_status_indicator(self, status):
        """Update status indicator color"""
        colors = {
            'ready': self.colors['success'],
            'checking': self.colors['warning'],
            'error': self.colors['error']
        }
        self.status_indicator.config(bg=colors.get(status, self.colors['warning']))

    def on_canvas_configure(self, event):
        """Handle canvas resize"""
        canvas_width = event.width
        self.preview_canvas.itemconfig(self.canvas_window, width=canvas_width - 20)
        self.check_sentence()

    def _load_files_directly(self):
        """Load C library and dictionary with better feedback"""
        if self.c_spell_checker:
            self.c_spell_checker.cleanup()
            self.c_spell_checker = None

        self.status_text.config(text="🔄 Loading C Library and Dictionary...")
        self.update_status_indicator('checking')
        self.master.update_idletasks()

        self.c_spell_checker = CSpellChecker(self.C_LIB_PATH)
        if self.c_spell_checker.lib is None:
            self.status_text.config(text="❌ Error: C Library failed to load")
            self.update_status_indicator('error')
            return

        if self.c_spell_checker.load_dictionary(self.DICT_PATH):
            self.status_text.config(text="✅ Ready - Dictionary loaded successfully")
            self.update_status_indicator('ready')
            self.check_sentence()
        else:
            self.status_text.config(text="❌ Error: Failed to load dictionary")
            self.update_status_indicator('error')
            if self.c_spell_checker:
                self.c_spell_checker.cleanup()
            self.c_spell_checker = None

    def check_sentence(self, event=None):
        """Enhanced spell checking with better visual feedback"""
        if not self.c_spell_checker or not self.c_spell_checker.loaded:
            self.clear_preview()
            self.suggestions_listbox.delete(0, tk.END)
            self.manual_replace_button.config(state=tk.DISABLED)
            self.ignore_button.config(state=tk.DISABLED)
            self.reset_selection()
            return

        current_sentence = self.sentence_text.get("1.0", tk.END).strip()
        
        if not current_sentence:
            self.clear_preview()
            self.update_stats(0, 0)
            return
        
        self.clear_preview()
        self.suggestions_listbox.delete(0, tk.END)
        self.manual_replace_button.config(state=tk.DISABLED)
        self.ignore_button.config(state=tk.DISABLED)
        self.reset_selection()

        tokens = re.findall(r"(\w+|[^\w\s]+|\s+)", current_sentence)
        self.all_tokens = tokens
        
        word_count = 0
        error_count = 0
        
        # Create word labels with modern styling
        for i, token in enumerate(tokens):
            word_lower = token.lower()
            is_error = False
            
            if word_lower.isalpha():
                word_count += 1
                if not self.c_spell_checker.is_word_correct(word_lower):
                    is_error = True
                    error_count += 1
            
            word_label = self.create_word_label(token, is_error, i)
            word_label.pack(side=tk.LEFT, padx=1, pady=2)
        
        # Update statistics
        self.update_stats(word_count, error_count)
        
        # Update canvas scroll region
        self.preview_inner_frame.update_idletasks()
        self.preview_canvas.config(scrollregion=self.preview_canvas.bbox("all"))
        
        if error_count > 0:
            self.status_text.config(text=f"📝 Found {error_count} potential error{'s' if error_count != 1 else ''}")
        else:
            self.status_text.config(text="✨ Perfect! No spelling errors found")

    def create_word_label(self, token, is_error, index):
        """Create styled word label"""
        if is_error:
            label = tk.Label(self.preview_inner_frame,
                           text=token,
                           font=('Segoe UI', 12, 'bold'),
                           fg='white',
                           bg=self.colors['error'],
                           padx=6,
                           pady=2,
                           cursor="hand2",
                           relief=tk.FLAT)
            label.bind("<Button-1>", lambda e: self.select_incorrect_word(label, token, index))
            label.bind("<Enter>", lambda e: label.config(bg='#DC2626'))  # Darker red on hover
            label.bind("<Leave>", lambda e: self.on_word_leave(label))
        else:
            label = tk.Label(self.preview_inner_frame,
                           text=token,
                           font=('Segoe UI', 12),
                           fg=self.colors['text_primary'],
                           bg=self.colors['surface'])
        
        return label

    def on_word_leave(self, label):
        """Handle mouse leave on error word"""
        try:
            # Check if widget still exists before configuring
            if label.winfo_exists():
                if label == self.current_incorrect_word_obj:
                    label.config(bg=self.colors['secondary'])  # Keep selected color
                else:
                    label.config(bg=self.colors['error'])  # Return to error color
        except tk.TclError:
            # Widget has been destroyed, ignore the error
            pass

    def clear_preview(self):
        """Clear preview area"""
        # Reset selection before destroying widgets to avoid invalid widget references
        if self.current_incorrect_word_obj:
            self.current_incorrect_word_obj = None
            self.current_original_token = None
            self.current_replacement_idx = -1
        
        for widget in self.preview_inner_frame.winfo_children():
            widget.destroy()

    def select_incorrect_word(self, word_label_obj, original_token, index_in_tokens):
        """Select incorrect word with modern styling"""
        print(f"\n--- select_incorrect_word called ---")
        print(f"  Selected word: '{original_token}' (Index: {index_in_tokens})")

        # Reset previous selection
        if self.current_incorrect_word_obj:
            self.current_incorrect_word_obj.config(bg=self.colors['error'])

        # Set new selection
        self.current_incorrect_word_obj = word_label_obj
        self.current_original_token = original_token
        self.current_replacement_idx = index_in_tokens
        self.current_incorrect_word_obj.config(bg=self.colors['secondary'])

        # Enable action buttons
        self.manual_replace_button.config(state=tk.NORMAL)
        self.ignore_button.config(state=tk.NORMAL)

        # Get and display suggestions
        self.suggestions_listbox.delete(0, tk.END)
        word_for_suggestions = original_token.lower()
        suggestions = self.c_spell_checker.get_suggestions(word_for_suggestions)

        if suggestions:
            for sug in suggestions:
                display_text = f"{sug['word']}"
                if sug['dist'] > 0:
                    display_text += f" (similarity: {max(0, 100-sug['dist']*10)}%)"
                self.suggestions_listbox.insert(tk.END, display_text)
            self.status_text.config(text=f"💡 {len(suggestions)} suggestion{'s' if len(suggestions) != 1 else ''} for '{original_token}'")
        else:
            self.suggestions_listbox.insert(tk.END, "No suggestions found")
            self.status_text.config(text=f"🔍 No suggestions found for '{original_token}'")

    def apply_suggestion(self, event=None):
        """Apply selected suggestion"""
        if self.current_replacement_idx == -1:
            return

        selected_indices = self.suggestions_listbox.curselection()
        if not selected_indices:
            return

        selected_item_index = selected_indices[0]
        full_suggestion_text = self.suggestions_listbox.get(selected_item_index)
        
        if full_suggestion_text == "No suggestions found":
            return
            
        suggested_word = full_suggestion_text.split(' ')[0]
        self._replace_selected_word(suggested_word)

    def manual_replace_word(self):
        """Handle manual word replacement"""
        if self.current_replacement_idx == -1:
            messagebox.showwarning("No Selection", "Please select a word to replace first.")
            return

        new_word = simpledialog.askstring(
            "Manual Replacement",
            f"Replace '{self.current_original_token}' with:",
            parent=self.master,
            initialvalue=self.current_original_token
        )
        
        if new_word:
            self._replace_selected_word(new_word)

    def _replace_selected_word(self, replacement_word):
        """Replace selected word and refresh display"""
        if self.current_replacement_idx == -1:
            return

        self.all_tokens[self.current_replacement_idx] = replacement_word
        new_sentence = "".join(self.all_tokens)

        # Update text widget
        self.sentence_text.delete("1.0", tk.END)
        self.sentence_text.insert("1.0", new_sentence)

        # Refresh spell checking
        self.check_sentence()
        self.status_text.config(text=f"✅ Replaced with '{replacement_word}' - Rechecking...")

        # Reset selection
        self.reset_selection()

    def reset_selection(self):
        """Reset current selection state"""
        self.suggestions_listbox.delete(0, tk.END)
        self.manual_replace_button.config(state=tk.DISABLED)
        self.ignore_button.config(state=tk.DISABLED)
        
        # Safely reset the current selection
        if self.current_incorrect_word_obj:
            try:
                # Check if the widget still exists before trying to configure it
                if self.current_incorrect_word_obj.winfo_exists():
                    self.current_incorrect_word_obj.config(bg=self.colors['error'])
            except tk.TclError:
                # Widget has been destroyed, ignore the error
                pass
            finally:
                self.current_incorrect_word_obj = None
            
        self.current_original_token = None
        self.current_replacement_idx = -1

    def on_closing(self):
        """Handle application closing"""
        if self.c_spell_checker:
            self.c_spell_checker.cleanup()
        self.master.destroy()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    root = tk.Tk()
    
    # Set window icon and additional properties
    try:
        # Try to set a modern appearance
        root.tk.call('tk', 'scaling', 1.2)  # Improve DPI scaling
    except:
        pass
    
    app = SpellCheckerApp(root)
    root.mainloop()