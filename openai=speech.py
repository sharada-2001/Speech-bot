from flask import Flask, render_template, request, jsonify, url_for
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
import os

app = Flask(__name__)


# Set environment variables (if not already set in your environment)
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://talkybot.openai.azure.com/"
os.environ["AZURE_OPENAI_KEY"] = "db9b62bb7a0546939b23cf6151c53e17"
os.environ["AZURE_SPEECH_KEY"] = "e18d4c861cb74e2c88bb1c75ba799fa5"

# Initialize Azure OpenAI and Speech services
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15"
)
deployment_id = "OpenAi"
speech_config = speechsdk.SpeechConfig(subscription=os.getenv("AZURE_SPEECH_KEY"), region="swedencentral")
default_language = "en-US"
speech_config.speech_recognition_language = default_language
speech_config.speech_synthesis_voice_name = 'en-US-JennyMultilingualNeural'
tts_sentence_end = [".", "!", "?", ";", "。", "！", "？", "；", "\n"]

def ask_openai(prompt, language="en-US"):
    try:
        response = client.chat.completions.create(model=deployment_id, max_tokens=200, stream=True, messages=[
            {"role": "user", "content": prompt}
        ])
        collected_messages = []
        bot_response = ""

        if language == "es-ES":
            speech_config.speech_synthesis_voice_name = 'es-ES-ElviraNeural'
        elif language == "hi-IN":
            speech_config.speech_synthesis_voice_name = 'hi-IN-AnanyaNeural'
        elif language == "mr-IN":
            speech_config.speech_synthesis_voice_name = 'mr-IN-AarohiNeural'
        elif language == "ta-IN":
            speech_config.speech_synthesis_voice_name = 'ta-IN-PallaviNeural'
        else:
            speech_config.speech_synthesis_voice_name = 'en-US-JennyMultilingualNeural'

        # Ensure the static directory exists
        static_dir = os.path.join(app.root_path, 'static')
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        audio_filename = os.path.join(static_dir, 'output.wav')
        audio_output_config = speechsdk.audio.AudioOutputConfig(filename=audio_filename)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_output_config)

        for chunk in response:
            if len(chunk.choices) > 0:
                chunk_message = chunk.choices[0].delta.content
                if chunk_message is not None:
                    collected_messages.append(chunk_message)
                    if chunk_message in tts_sentence_end:
                        text = ''.join(collected_messages).strip()
                        if text != '':
                            bot_response += text + " "
                            print(f"Speech synthesized to speaker for: {text}")
                            speech_synthesizer.speak_text_async(text).get()
                            collected_messages.clear()

        return bot_response.strip(), audio_filename
    except Exception as e:
        print(f"Error: {e}")
        return f"An error occurred while processing your request: {e}", ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('prompt')
    language = data.get('language', default_language)
    bot_response, audio_filename = ask_openai(prompt, language)
    if audio_filename:
        timestamp = int(os.path.getmtime(audio_filename))
        audio_url = url_for('static', filename=os.path.basename(audio_filename)) + f"?v={timestamp}"
    else:
        audio_url = ""
    return jsonify({"response": bot_response, "audio_url": audio_url})


if __name__ == '__main__':
    app.run(debug=True)
