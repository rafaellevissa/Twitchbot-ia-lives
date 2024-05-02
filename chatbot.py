import os
import csv
from datetime import datetime
from twitchio.ext import commands
from openai import OpenAI

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Twitch Bot Configurations
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
CHANNEL_NAME = os.getenv("CHANNEL_NAME")
ALLOWED_TO_QUESTION = os.getenv("ALLOWED_TO_QUESTION").split(',')
CSV_FILENAME = os.path.join("perguntas_live-" + datetime.now().strftime("%Y-%m-%d") + ".csv")

# OpenAI Configurations
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# CSV File Configurations (DON'T CHANGE)
CSV_ROW = {"Tema":0, "Pergunta":1, "Data":2, "Respondido":3}

client = OpenAI(
    api_key=OPENAI_API_KEY,
)

# Twitch Bot Implementation
class DevOpsTriviaBot(commands.Bot):
    def __init__(self):
        super().__init__(token=TWITCH_TOKEN, prefix='!', initial_channels=[CHANNEL_NAME])
        self.openai_api = client

    async def event_ready(self):
        print(f"Logado como: {self.nick}")
        print(f"ID: {self.user_id}")
        self.live = await self.fetch_channel(CHANNEL_NAME)
        print(f'Titulo da live: {self.live.title}')
        print("########################################")

    async def event_message(self, message):
        try:
            if message.author and message.author.name.lower() in ALLOWED_TO_QUESTION:
                await self.handle_commands(message)
        except Exception as e:
            print(e)

    @commands.command(name='pergunta')
    async def cmd_get_question(self, ctx):
        # Generate a question from ChatGPT
        unanswered_question = self.get_unanswered_question()
        if unanswered_question:
            await ctx.send(f'[Bot]: {unanswered_question}')
            print("Enviando pergunta:", unanswered_question)
            self.mark_question_asked(unanswered_question)
        else:
            await self.generate_and_send_questions(ctx)  # Await the coroutine

    def get_unanswered_question(self):
        # Read the CSV file to get unanswered questions
        try:
            with open(CSV_FILENAME, mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) >= 4 and row[CSV_ROW["Respondido"]] == "No":
                        return row[CSV_ROW["Pergunta"]]
        except FileNotFoundError:
            return None
        return None

    def mark_question_asked(self, question):
        # Update the status of the question in the CSV file
        with open(CSV_FILENAME, mode='r', newline='') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        for row in rows:
            if len(row) >= 4 and row[CSV_ROW["Pergunta"]] == question:
                row[CSV_ROW["Respondido"]] = "Yes"
                break

        with open(CSV_FILENAME, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    async def generate_and_send_questions(self, ctx):
        # Generate questions from ChatGPT
        prompt = "Me faça dez pergunta sobre o tema dessa live: " + self.live.title
        questions = self.generate_questions(prompt)

        # Send the first question to Twitch chat
        if questions:
            first_question = questions[0]
            print("Enviando pergunta:", first_question)
            await ctx.send(f'[Bot]: {first_question}')
            self.save_to_csv(self.live.title, questions)  # Corrected method name
            self.mark_question_asked(first_question)

    def generate_questions(self, prompt):
        # Use ChatGPT to generate a question
        print("Gerando perguntas...")
        response = self.openai_api.chat.completions.create(
            model="gpt-3.5-turbo", # gpt-4-turbo
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=1.0
        )
        generated_questions = response.choices[0].message.content.split('\n')
        generated_questions = [question.strip()[3:].strip() for question in generated_questions if question.strip()]
        return generated_questions
    
    def save_to_csv(self, theme, questions):
        # Save the generated questions to a CSV file
        with open(CSV_FILENAME, mode='a', newline='') as file:
            writer = csv.writer(file)
            for question in questions:
                writer.writerow([theme, question, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "No"])

# Main function to run the bot
def main():
    bot = DevOpsTriviaBot()
    bot.run()

if __name__ == "__main__":
    main()