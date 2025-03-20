from openai import OpenAI
import os
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Decode the API key
encoded_api_key = os.getenv("OPENAI_API_KEY_BASE64")
if encoded_api_key:
    openai_api_key = base64.b64decode(encoded_api_key).decode("utf-8")
else:
    raise ValueError("API key not found in environment variables!")
# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Define the chatbot
class Chatbot:
    def __init__(self):
        self.history = []  # Store conversation history for context

    def chat(self, user_input):
        """
        Handles the chat interaction with the user.
        """
        # Append user message to history
        self.history.append({"role": "user", "content": user_input})

        # Generate a response using OpenAI's Chat API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.history
        )

        # Extract the assistant's reply
        assistant_reply = response.choices[0].message.content

        # Append the assistant's reply to history
        self.history.append({"role": "assistant", "content": assistant_reply})

        return assistant_reply

# Main function to run the chatbot
def main():
    chatbot = Chatbot()
    print("Welcome to the Customer Support Chatbot!")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["thanks", "goodbye", "bye"]:
            print("Chatbot: Goodbye! Have a great day.")
            break
        response = chatbot.chat(user_input)
        print(f"Chatbot: {response}")

if __name__ == "__main__":
    main()