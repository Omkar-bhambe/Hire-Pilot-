from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))


def generate_voice(text, filename="voice.mp3"):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # you can try: alloy, verse, aria
            input=text
        )

        file_path = f"static/{filename}"

        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path

    except Exception as e:
        print("Voice Error:", e)
        return None