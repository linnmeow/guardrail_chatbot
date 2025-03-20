from openai import OpenAI
import os
import json
import base64
import re  # Import regex for pattern matching
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

# Load sensitive keywords from JSON file
with open("sensitive_keywords.json", "r") as file:
    data = json.load(file)
    SENSITIVE_KEYWORDS = data["sensitive_keywords"]

# Load topics and their associated keywords from JSON file
with open("topics.json", "r") as file:
    data = json.load(file)
    TOPICS = data["topics"]

# Input Guardrails
class InputGuardrails:
    def __init__(self):
        self.topic_keywords = TOPICS  # Load topics from JSON

    def detect_sensitive_info(self, text):
        """
        Detects sensitive information in user input, including keywords, phone numbers, emails, and credit card numbers.
        """
        # Check for sensitive keywords
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in text.lower():
                return True

        # Check for phone numbers using regex
        phone_regex = r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
        if re.search(phone_regex, text):
            return True

        # Check for email addresses using regex
        email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        if re.search(email_regex, text):
            return True

        # Check for credit card numbers using regex
        credit_card_regex = r"\b(?:\d[ -]*?){13,16}\b"
        if re.search(credit_card_regex, text):
            return True

        return False

    def moderate_input(self, text):
        """
        Uses OpenAI Moderation API to check for offensive or harmful content.
        """
        moderation_response = client.moderations.create(input=text)
        return moderation_response.results[0].flagged

    def detect_topic(self, user_input):
        """
        Determines the topic of user input using keyword matching.
        """
        user_input = user_input.lower()
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                return topic
        return "unknown"

    def validate_input(self, user_input):
        """
        Validates user input for sensitive information, offensive content, and topic relevance.
        """
        # Check for sensitive information
        if self.detect_sensitive_info(user_input):
            return False, "I’m sorry, but I can’t process requests containing sensitive information."

        # Check for offensive or harmful content
        if self.moderate_input(user_input):
            return False, "I’m sorry, but your message contains inappropriate content. Please rephrase."

        # Check if the input is on-topic
        detected_topic = self.detect_topic(user_input)
        if detected_topic == "unknown":
            return False, "I'm sorry, I can only assist with support-related topics."

        return True, user_input

# Output Guardrails
class OutputGuardrails:
    def __init__(self):
        pass

    def detect_sensitive_info(self, text):
        """
        Detects sensitive information in chatbot responses.
        """
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in text.lower():
                return True
        return False

    def moderate_output(self, text):
        """
        Uses OpenAI Moderation API to check for offensive or harmful content in chatbot responses.
        """
        moderation_response = client.moderations.create(input=text)
        return moderation_response.results[0].flagged

    def validate_output(self, text):
        """
        Validates the chatbot's response to ensure it is safe and compliant.
        """
        # Check for sensitive information
        if self.detect_sensitive_info(text):
            return False, "I’m sorry, but I can’t provide that information."

        # Check for offensive or harmful content
        if self.moderate_output(text):
            return False, "I’m sorry, but I can’t provide that information."

        return True, text

# Define the chatbot
class Chatbot:
    def __init__(self):
        self.history = []  # Store conversation history for context
        self.input_guardrails = InputGuardrails()
        self.output_guardrails = OutputGuardrails()

    def chat(self, user_input):
        """
        Handles the chat interaction with the user.
        """
        # Step 1: Validate user input
        is_input_valid, sanitized_input = self.input_guardrails.validate_input(user_input)
        if not is_input_valid:
            return sanitized_input

        # Step 2: Append user message to history
        self.history.append({"role": "user", "content": sanitized_input})

        # Step 3: Generate a response using OpenAI's Chat API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.history
        )

        # Step 4: Extract the assistant's reply
        assistant_reply = response.choices[0].message.content

        # Step 5: Validate the assistant's reply
        is_output_valid, validated_reply = self.output_guardrails.validate_output(assistant_reply)
        if not is_output_valid:
            return validated_reply

        # Step 6: Append the assistant's reply to history
        self.history.append({"role": "assistant", "content": validated_reply})

        return validated_reply

# Main function to run the chatbot
def main():
    chatbot = Chatbot()
    print("Welcome to the Customer Support Chatbot!")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "goodbye", "bye", "thanks"]:
            print("Chatbot: Goodbye! Have a great day.")
            break
        response = chatbot.chat(user_input)
        print(f"Chatbot: {response}")

if __name__ == "__main__":
    main()