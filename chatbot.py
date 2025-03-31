from openai import OpenAI
import os
import json
import base64
import re  
from dotenv import load_dotenv

# load environment variables
load_dotenv()

# decode the API key
encoded_api_key = os.getenv("OPENAI_API_KEY_BASE64")
if encoded_api_key:
    openai_api_key = base64.b64decode(encoded_api_key).decode("utf-8")
else:
    raise ValueError("API key not found in environment variables!")

# initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# load sensitive keywords from JSON file
with open("sensitive_keywords.json", "r") as file:
    data = json.load(file)
    HIGH_SENSITIVITY_KEYWORDS = data["high_sensitivity_keywords"]
    MEDIUM_SENSITIVITY_KEYWORDS = data["medium_sensitivity_keywords"]

# load topics and their associated keywords from JSON file
with open("topics.json", "r") as file:
    data = json.load(file)
    TOPICS = data["topics"]

class InputGuardrails:
    def __init__(self):
        self.topic_keywords = TOPICS  # load predefined topics

    def detect_sensitive_info(self, text):
        """
        Detects sensitive information in user input, including keywords, phone numbers, emails, and credit card numbers.
        Returns a tuple (is_sensitive, response_message) where is_sensitive is a boolean and response_message is a string.
        """
        text_lower = text.lower()

        # check for high sensitivity keywords
        for keyword in HIGH_SENSITIVITY_KEYWORDS:
            if keyword in text_lower:
                return True, "I’m sorry, but I can’t process requests containing sensitive information."

        # check for medium sensitivity keywords
        for keyword in MEDIUM_SENSITIVITY_KEYWORDS:
            if keyword in text_lower:
                if keyword == "email":
                    return True, "I can help you with general questions, but for security reasons, I cannot process email addresses. Please visit our support page for assistance."
                elif keyword == "phone number":
                    return True, "I’m unable to process phone numbers directly. Please contact our support team for further assistance."
                elif keyword == "password":
                    return True, "For security reasons, I cannot assist with password-related issues. Please use our password recovery tool."

        # check for phone numbers using regex
        phone_regex = r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
        if re.search(phone_regex, text):
            return True, "I’m unable to process phone numbers directly. Please contact our support team for further assistance."

        # check for email addresses using regex
        email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        if re.search(email_regex, text):
            return True, "I can help you with general questions, but for security reasons, I cannot process email addresses. Please visit our support page for assistance."

        # check for credit card numbers using regex
        credit_card_regex = r"\b(?:\d[ -]*?){13,16}\b"
        if re.search(credit_card_regex, text):
            return True, "I’m sorry, but I can’t process requests containing sensitive information."

        return False, None

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
        # check for sensitive information
        is_sensitive, sensitive_response = self.detect_sensitive_info(user_input)
        if is_sensitive:
            return False, sensitive_response

        # check for offensive or harmful content
        if self.moderate_input(user_input):
            return False, "I’m sorry, but your message contains inappropriate content. Please rephrase."

        # check if the input is on-topic
        detected_topic = self.detect_topic(user_input)
        if detected_topic == "unknown":
            return False, "I'm sorry, I can only assist with support-related topics."

        return True, user_input

class OutputGuardrails:
    def __init__(self):
        pass

    def detect_sensitive_info(self, text):
        """
        Detects sensitive information in chatbot responses.
        Returns True if sensitive information is found, otherwise False.
        """
        text_lower = text.lower()

        # check for high sensitivity keywords
        for keyword in HIGH_SENSITIVITY_KEYWORDS:
            if keyword in text_lower:
                return True
            return False

        # check for medium sensitivity keywords
        for keyword in MEDIUM_SENSITIVITY_KEYWORDS:
            if keyword in text_lower:
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
        # check for sensitive information
        if self.detect_sensitive_info(text):
            return False, "I’m sorry, but I can’t provide that information."

        # check for offensive or harmful content
        if self.moderate_output(text):
            return False, "I’m sorry, but I can’t provide that information."

        return True, text

class Chatbot:
    def __init__(self):
        # store conversation history for context with system prompt
        self.history = [
            {
                "role": "system",
                "content": "You are a helpful customer support assistant."
            }
        ]  
        self.input_guardrails = InputGuardrails()
        self.output_guardrails = OutputGuardrails()

    def chat(self, user_input):
        """
        Handles the chat interaction with the user.
        """
        # 1: validate user input
        is_input_valid, sanitized_input = self.input_guardrails.validate_input(user_input)
        if not is_input_valid:
            return sanitized_input

        # 2: append user message to history
        self.history.append({"role": "user", "content": sanitized_input})

        # 3: generate a response using OpenAI's Chat API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.history
        )

        # 4: extract the assistant's reply
        assistant_reply = response.choices[0].message.content

        # 5: validate the assistant's reply
        is_output_valid, validated_reply = self.output_guardrails.validate_output(assistant_reply)
        if not is_output_valid:
            return validated_reply

        # 6: append the assistant's reply to history
        self.history.append({"role": "assistant", "content": validated_reply})

        return validated_reply

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