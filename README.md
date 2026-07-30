# Basic Password Generator

A lightweight desktop application built with Python and Tkinter that generates random passwords based on user-defined criteria. This project was created to practice Python programming, GUI development, and basic software documentation.

> **Repository:** `dev-projects`
> **Project Folder:** `Basic-Password-Generator`

---

# Table of Contents

* Overview
* Features
* Technologies Used
* Project Structure
* Installation
* Running the Application
* Building an Executable
* How It Works
* Code Structure
* Future Improvements
* Screenshots
* Author

---

# Overview

The Basic Password Generator is a desktop application that allows users to generate random passwords while choosing the desired password length and the types of characters to include.

The application provides a simple graphical user interface (GUI) designed using Tkinter, making it easy to use without requiring any command-line interaction.

This project serves as a beginner-friendly demonstration of:

* Python programming
* GUI development with Tkinter
* Random password generation
* Event-driven programming

---

# Features

* Generate random passwords
* Select a custom password length
* Include lowercase letters
* Include uppercase letters
* Include numbers
* Include punctuation symbols
* Copy generated password to the clipboard
* Lightweight graphical user interface

---

# Technologies Used

| Technology | Purpose                                       |
| ---------- | --------------------------------------------- |
| Python 3   | Main programming language                     |
| Tkinter    | Graphical User Interface                      |
| ttk        | Modern Tkinter widgets                        |
| random     | Random character selection                    |
| string     | Character sets (letters, digits, punctuation) |

---

# Project Structure

```
Basic-Password-Generator/
│
├── password_generator.py
├── README.md
└── screenshots/
    ├── main-window.png
    └── generated-password.png
```

---

# Installation

## Clone the repository

```bash
git clone https://github.com/Jade-Kester/dev-projects.git
```

Navigate to the project folder.

```bash
cd dev-projects/Basic-Password-Generator
```

---

# Requirements

* Python 3.10 or newer

No external Python packages are required.

---

# Running the Application

Run the following command:

```bash
python password_generator.py
```

---

# Building an Executable

Install PyInstaller:

```bash
pip install pyinstaller
```

Generate the executable:

```bash
python -m PyInstaller --onefile --windowed password_generator.py
```

The executable will be located inside:

```
dist/
```

---

# How It Works

The application follows a simple workflow.

1. The user selects the desired password length.
2. The user chooses which character types to include.
3. The **Generate** button is clicked.
4. The program creates a pool of available characters.
5. Random characters are selected until the requested password length is reached.
6. The generated password is displayed.
7. The password can be copied to the clipboard using the **Copy** button.

---

# Code Structure

## Main Window

Creates the application window, sets its title, size, and appearance.

---

## Variables

Stores the states of the checkboxes and the selected password length.

---

## `generate_password()`

Responsible for generating a password.

### Process

* Reads all selected options.
* Creates a valid character pool.
* Validates user input.
* Generates a random password.
* Displays the generated password.

---

## `copy_password()`

Copies the generated password to the system clipboard.

---

# User Interface

The graphical interface contains:

* Password display area
* Generate button
* Copy button
* Password length selector
* Lowercase checkbox
* Uppercase checkbox
* Numbers checkbox
* Punctuation checkbox

---

# Future Improvements

Potential improvements include:

* Password strength indicator
* Save generated passwords
* Dark mode
* Keyboard shortcuts

---

# Screenshots

Add screenshots inside the `screenshots` folder.

Example:

```
screenshots/
    main-window.png
    generated-password.png
```

Then display them in the README.

```markdown
![Main Window](screenshots/main-window.png)

![Generated Password](screenshots/generated-password.png)
```

---

# Learning Outcomes

Through this project, I learned how to:

* Design graphical user interfaces using Tkinter
* Create event-driven applications
* Work with Python's built-in libraries
* Generate random passwords
* Handle user input and validation
* Organize a Python project for GitHub
* Package Python applications into standalone executables using PyInstaller

---

# License

This project is intended for educational and portfolio purposes.

---

# Author

**Jade Kester Marcelo**

Computer Engineering Graduate

Python • Software Development • Cybersecurity
