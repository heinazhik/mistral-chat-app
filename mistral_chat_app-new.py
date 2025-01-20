import sys
import json
from datetime import datetime
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QPushButton, QComboBox, QHBoxLayout,
    QFileDialog, QMessageBox, QLabel, QFormLayout, QListWidget, QListWidgetItem, QSplitter, QInputDialog, QMenu,
    QScrollArea, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QTextCharFormat, QColor, QKeySequence, QIcon, QAction
from PyQt6.QtCore import Qt, QFile, QTextStream, QDir
from mistralai import Mistral  # Updated import for Mistral API v1.0

class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mistral Chat App")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left pane: All Chats
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_pane.setMaximumWidth(300)  # Set width to 1/4 of the window

        self.all_chats_list = QListWidget()
        self.all_chats_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)  # Enable horizontal scrolling
        self.load_chat_histories()
        self.all_chats_list.itemDoubleClicked.connect(self.load_selected_chat)
        left_layout.addWidget(self.all_chats_list)

        # Delete Chat Button
        self.delete_chat_button = QPushButton("Delete Chat")
        self.delete_chat_button.clicked.connect(self.delete_selected_chat)
        left_layout.addWidget(self.delete_chat_button)

        # New Chat Button
        self.new_chat_button = QPushButton("New Chat")
        self.new_chat_button.clicked.connect(self.new_chat)
        left_layout.addWidget(self.new_chat_button)

        main_layout.addWidget(left_pane)

        # Right pane: Chat Display and Input
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)

        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_display.customContextMenuRequested.connect(self.copy_context_menu)
        right_layout.addWidget(self.chat_display)

        # User Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setMaxLength(32000)
        self.input_field.returnPressed.connect(self.send_message)
        right_layout.addWidget(self.input_field)

        # Buttons
        button_layout = QHBoxLayout()
        self.attach_file_button = QPushButton(QIcon.fromTheme("document-open"), "Attach File")
        self.attach_file_button.clicked.connect(self.attach_file)
        button_layout.addWidget(self.attach_file_button)

        self.send_button = QPushButton(QIcon.fromTheme("mail-send"), "Send")
        self.send_button.clicked.connect(self.send_message)
        button_layout.addWidget(self.send_button)

        self.emoji_button = QPushButton(QIcon.fromTheme("face-smile"), "Emoji")
        self.emoji_button.clicked.connect(self.open_emoji_dialog)
        button_layout.addWidget(self.emoji_button)

        right_layout.addLayout(button_layout)
        main_layout.addWidget(right_pane)

        # Configuration drop-downs and system prompt
        config_layout = QFormLayout()
        self.api_key_combo = QComboBox()
        self.api_key_combo.setEditable(True)
        self.api_key_combo.setPlaceholderText("Enter your Mistral API key")
        config_layout.addRow("API Key:", self.api_key_combo)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["mistral-large", "mistral-small", "mistral-next", "codestral-latest"])
        self.model_combo.setCurrentText("codestral-latest")
        config_layout.addRow("Model:", self.model_combo)

        self.system_prompt_field = QLineEdit()
        self.system_prompt_field.setPlaceholderText("Enter system prompt")
        self.system_prompt_field.setText("Imagine that you are an expert software developer who is able to create innovative, user-friendly and advanced software solutions for users. Make your answer technical, but in a language that most non-technical people can understand. Also, format your reply using Whatsapp style text formatting. Carefully review and evaluate each reported problem/bug or message and then think deeply and carefully about a solution before recommending it. Try to simulate and test any generated code or script before replying.")
        config_layout.addRow("System Prompt:", self.system_prompt_field)

        right_layout.addLayout(config_layout)

        # Chat history
        self.chat_history = []
        self.current_chat_file = None

        # Set Stylesheet for Modern Look
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QTextEdit { background-color: white; border: 1px solid #ccc; padding: 10px; }
            QLineEdit { background-color: white; border: 1px solid #ccc; padding: 10px; }
            QPushButton { background-color: #007acc; color: white; border: none; padding: 10px; margin: 5px; }
            QPushButton:hover { background-color: #005a8c; }
            QListWidget { background-color: #e0e0e0; border: 1px solid #ccc; padding: 10px; }
            QListWidgetItem { padding: 5px; }
            QSplitter::handle { background-color: #ccc; width: 5px; }
        """)

    def load_chat_histories(self):
        self.all_chats_list.clear()
        chat_dir = QDir("chats_history")
        if not chat_dir.exists():
            chat_dir.mkpath(".")
        chat_files = chat_dir.entryList(["chat_history_*.json"], QDir.Filter.Files)
        chat_files.sort(reverse=True)  # Sort files by timestamp (most recent first)
        for chat_file in chat_files:
            item = QListWidgetItem(chat_file)
            self.all_chats_list.addItem(item)

    def load_selected_chat(self, item):
        chat_file = item.text()
        self.current_chat_file = os.path.join("chats_history", chat_file)
        with open(self.current_chat_file, 'r') as file:
            self.chat_history = json.load(file)
        self.update_chat_display()

    def new_chat(self):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.current_chat_file = os.path.join("chats_history", f"chat_history_{timestamp}.json")
        self.chat_history = []
        self.update_chat_display()
        self.auto_save_chat_history()  # Create and save the new chat file
        self.load_chat_histories()  # Refresh the chat list
        self.all_chats_list.setCurrentRow(0)  # Select the new chat
        QMessageBox.information(self, "New Chat", "A new chat has been created.")  # Feedback

    def delete_selected_chat(self):
        selected_item = self.all_chats_list.currentItem()
        if selected_item:
            confirm = QMessageBox.question(self, "Delete Chat", "Are you sure you want to delete this chat?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                chat_file = selected_item.text()
                os.remove(os.path.join("chats_history", chat_file))
                self.load_chat_histories()  # Refresh the chat list

    def update_chat_display(self):
        self.chat_display.clear()
        for entry in self.chat_history:
            timestamp = entry.get("timestamp", "")
            role = entry.get("role", "")
            content = entry.get("content", "")
            self.add_message_to_chat_display(role, content, timestamp)

    def send_message(self):
        if not self.current_chat_file:
            QMessageBox.warning(self, "Error", "Please select a chat history or create a new chat.")
            return

        user_message = self.input_field.text().strip()  # Remove leading/trailing whitespace
        if not user_message:
            QMessageBox.warning(self, "Error", "Message cannot be empty.")
            return

        timestamp = datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        self.add_message_to_chat_display("You", user_message, timestamp)
        self.input_field.clear()

        # Get AI response
        response = self.get_ai_response(user_message)
        timestamp = datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        self.add_message_to_chat_display("AI", response, timestamp)

        # Add to chat history
        self.chat_history.append({"role": "user", "content": user_message, "timestamp": timestamp})
        self.chat_history.append({"role": "bot", "content": response, "timestamp": timestamp})

        # Auto-save chat history
        self.auto_save_chat_history()

    def get_ai_response(self, message):
        api_key = self.api_key_combo.currentText()
        if not api_key:
            return "Please enter a valid API key."

        model = self.model_combo.currentText()
        system_prompt = self.system_prompt_field.text()

        try:
            client = Mistral(api_key=api_key)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            chat_response = client.chat.complete(model=model, messages=messages)
            return chat_response.choices[0].message.content
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}. Please check your API key and internet connection."

    def add_message_to_chat_display(self, sender, message, timestamp):
        format = QTextCharFormat()
        if sender == "You":
            format.setForeground(QColor("blue"))
            sender_display = "You"
        else:
            format.setForeground(QColor("green"))
            sender_display = "AI"
        self.chat_display.setCurrentCharFormat(format)
        self.chat_display.append(f"[{timestamp}] {sender_display}: {message}")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())  # Auto-scroll

    def attach_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Attach File", "", "Text Files (*.txt)", options=options)
        if file_name:
            file_size = os.path.getsize(file_name)
            if file_size > 1024 * 1024:  # 1 MB limit
                QMessageBox.warning(self, "Error", "File size exceeds 1 MB limit.")
            elif file_name.endswith(".txt"):
                with open(file_name, 'r') as file:
                    file_content = file.read()
                self.input_field.setText(file_content)
            else:
                QMessageBox.warning(self, "Error", "Only .txt files are supported.")

    def open_emoji_dialog(self):
        emojis = ["😊", "😢", "😄", "😍", "🤔", "😎", "😂", "😢", "😭", "👏", "👍", "👎", "❤", "💔", "🎉", "🎁", "🎈", "🔑", "🔒", "🔓"]
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Emoji")
        dialog_layout = QVBoxLayout(dialog)

        emoji_list = QListWidget()
        emoji_list.addItems(emojis)
        dialog_layout.addWidget(emoji_list)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.add_selected_emoji(emoji_list))
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(add_button)
        button_layout.addWidget(close_button)
        dialog_layout.addLayout(button_layout)

        dialog.exec()

    def add_selected_emoji(self, emoji_list):
        selected_items = emoji_list.selectedItems()
        if selected_items:
            emoji = selected_items[0].text()
            cursor = self.input_field.cursorPosition()
            self.input_field.insert(emoji)
            self.input_field.setCursorPosition(cursor + len(emoji))
            QMessageBox.information(self, "Emoji Added", f"Emoji '{emoji}' has been added to your message.")  # Feedback

    def copy_context_menu(self, position):
        menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.chat_display.copy)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        menu.addAction(copy_action)
        menu.exec(self.chat_display.mapToGlobal(position))

    def auto_save_chat_history(self):
        if self.current_chat_file:
            with open(self.current_chat_file, 'w') as file:
                json.dump(self.chat_history, file, indent=4)
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.current_chat_file = os.path.join("chats_history", f"chat_history_{timestamp}.json")
            with open(self.current_chat_file, 'w') as file:
                json.dump(self.chat_history, file, indent=4)
            self.load_chat_histories()
            self.all_chats_list.setCurrentRow(self.all_chats_list.count() - 1)

def main():
    app = QApplication(sys.argv)
    chat_app = ChatApp()
    chat_app.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

