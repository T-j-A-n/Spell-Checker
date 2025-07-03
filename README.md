# Spell-Checker
A high-performance hybrid spell-checking tool that combines the speed of C with the flexibility and user-friendliness of Python. This project provides a simple GUI for checking spelling and receiving real-time suggestions, powered by a C-based backend that uses Levenshtein distance for intelligent correction.

---

## 🛠 Features

- ⚡ **Fast Spell Checking:** Backend written in C for speed and efficiency.
- 🔠 **Intelligent Suggestions:** Uses Levenshtein distance to suggest corrections.
- 🖥 **Python GUI:** Interactive and easy-to-use graphical interface using `tkinter`.
- 🔁 **Real-Time Feedback:** Instantly shows whether input is correct and provides suggestions.
- 📦 **Modular Design:** Clean separation of frontend and backend for easy extensibility.

---

## 📁 Project Structure
```bash
hybrid-spell-checker/
│
├── backend/
│   ├── spellchecker.c    
│   ├── dictionary.txt      
│   └── Makefile.so           
│
├── gui/
│   └── main.py              # Python GUI built using tkinter
│
│
└── README.md                # This file
```

---

## 🚀 Getting Started

### 🔧 Prerequisites

- C Compiler (e.g., `gcc`)
- Python 3.x
- `tkinter` (usually comes pre-installed with Python)

### 🔨 Build Backend

Navigate to the `backend/` directory and run:

Use the following shell script to compile your C code (`spellchecker.c`) into a shared object file (`.so`) that Python can load using `ctypes`.

```bash
#!/bin/bash

# Exit immediately if any command fails
set -e

echo "🔧 Building the C backend into a shared library..."

# Name of the output shared object
OUTPUT_LIB="libspellchecker.so"
# Name of the C source file
SOURCE_FILE="spellchecker.c"

# Compile the shared object
gcc -Wall -fPIC -shared -o $OUTPUT_LIB $SOURCE_FILE

echo "✅ Build complete: $OUTPUT_LIB created."
```
## 🐍 Using the Shared Library in Python

Here's how to load and call a C function from the shared object using `ctypes`:

```python
import ctypes

# Load the shared library
lib = ctypes.CDLL('./libspellchecker.so')

# Example: call a function named 'hello' from C
lib.hello()
```

### 🔽 Clone the Repository

```bash
git clone https://github.com/yourusername/hybrid-spell-checker.git
cd hybrid-spell-checker
```
