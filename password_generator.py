import random
import string
import tkinter as tk
from tkinter import ttk


# Window #

password_generator = tk.Tk()
password_generator.title("Password Generator")
password_generator.config(bg="#ffffff")
password_generator.geometry("500x300")
password_generator.geometry("+0+0")
password_generator.resizable(False, False)


# Style #

style = ttk.Style(password_generator)
style.theme_use("clam")

style.configure("TCheckbutton", background="#ffffff", foreground="#000000")
style.configure("TButton", background="#ffffff", foreground="#000000")
style.configure("Title.TLabel", background="#ffffff", foreground="#000000", font=("", 18, "bold"))
style.configure("Result.TLabel", background="#ffffff", foreground="#000000", relief="solid", anchor="center")
style.configure("Text.TLabel", background="#ffffff", foreground="#000000")


# Variables #

lowercase_var = tk.BooleanVar(value=True)
uppercase_var = tk.BooleanVar(value=True)
numbers_var = tk.BooleanVar(value=True)
punctuation_var = tk.BooleanVar(value=True)


# Functions #

def generate_password():

    characters = ""

    if lowercase_var.get():
        characters += string.ascii_lowercase

    if uppercase_var.get():
        characters += string.ascii_uppercase

    if numbers_var.get():
        characters += string.digits

    if punctuation_var.get():
        characters += string.punctuation

    try:
        length = int(spin_box.get())
    except ValueError:
        result_label.config(text="Invalid length")
        return

    if length <= 0:
        result_label.config(text="Enter a length > 0")
        return

    if characters == "":
        result_label.config(text="Select a character set")
        return

    password = "".join(random.choice(characters) for _ in range(length))

    result_label.config(text=password)


def copy_password():

    password = result_label.cget("text")

    if password not in (
        "",
        "Invalid length",
        "Enter a length > 0",
        "Select a character set",
    ):
        password_generator.clipboard_clear()
        password_generator.clipboard_append(password)
        password_generator.update()



# Widgets #


title = ttk.Label(
    password_generator,
    text="Password Generator",
    style="Title.TLabel"
)
title.place(x=132, y=34, width=350, height=34)

result_label = ttk.Label(
    password_generator,
    text="",
    style="Result.TLabel"
)
result_label.place(x=83, y=79, width=396, height=30)

copy_button = ttk.Button(
    password_generator,
    text="Copy",
    command=copy_password
)
copy_button.place(x=25, y=81, width=47, height=30)

generate_button = ttk.Button(
    password_generator,
    text="Generate",
    command=generate_password
)
generate_button.place(x=214, y=121, width=80, height=40)

length_label = ttk.Label(
    password_generator,
    text="Length",
    style="Text.TLabel"
)
length_label.place(x=177, y=166, width=80, height=30)

spin_box = tk.Spinbox(
    password_generator,
    from_=1,
    to=100,
    increment=1,
    bg="#ffffff",
    fg="#000000",
    bd=1
)
spin_box.delete(0, tk.END)
spin_box.insert(0, "12")
spin_box.place(x=268, y=167, width=70, height=30)

uppercase_checkbox = ttk.Checkbutton(
    password_generator,
    text="Include Uppercase Letters",
    variable=uppercase_var
)
uppercase_checkbox.place(x=39, y=199, width=191, height=30)

lowercase_checkbox = ttk.Checkbutton(
    password_generator,
    text="Include Lowercase Letters",
    variable=lowercase_var
)
lowercase_checkbox.place(x=279, y=199, width=191, height=30)

numbers_checkbox = ttk.Checkbutton(
    password_generator,
    text="Include Numbers",
    variable=numbers_var
)
numbers_checkbox.place(x=39, y=232, width=191, height=30)

punctuation_checkbox = ttk.Checkbutton(
    password_generator,
    text="Include Punctuation Marks",
    variable=punctuation_var
)
punctuation_checkbox.place(x=278, y=232, width=191, height=30)


# Start Application #

password_generator.mainloop()
