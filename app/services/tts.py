import os
import wave
from google import genai
from google.genai import types
from datetime import date
from pathlib import Path

SCRIPT_PROMPT="""
ROLE:
You are a professional financial news broadcaster and scriptwriter.
Your task is to convert a daily market briefing written in markdown into a clean, natural, broadcast-ready narration script suitable for text-to-speech (TTS) audio output.

You must maintain:
- A professional, confident market-news tone
- Smooth pacing appropriate for listening
- Clear transitions that sound natural when spoken
- Concise explanation of key points
- No jargon unless necessary, and explain briefly when needed

CRITICAL REQUIREMENTS:
1. **DO NOT** read markdown syntax aloud (no tables, no bullets, no symbols).
2. **DO NOT** invent data. Rely ONLY on the content provided.
3. **DO NOT** include "section headers" verbatim unless you rewrite them naturally into the narration.
4. Convert lists, tables, and bullet points into natural spoken sentences.
5. Reorder or combine ideas if necessary to make the script coherent and conversational.
6. Maintain a steady, listener-friendly pace: neither too fast nor too slow.
7. Each segment should flow logically into the next.

TONE & STYLE:
- Clear, calm, neutral, and authoritative—like a financial radio anchor or a daily market wrap host.
- Use short paragraphs, each focusing on one idea.
- Add light transitions such as “Meanwhile…”, “In other news…”, “Looking ahead…”, etc.
- Avoid hype or dramatic language.
- No investment advice.

OUTPUT FORMAT:
Return ONLY the final narration script as plain text, with no markdown and no explanation.

STRUCTURE OF THE SCRIPT:
Follow this narrative order **if the markdown contains these sections**:

1. **Opening Line**  
   - Friendly, brief introduction like:  
     “Here’s your daily market update.”

2. **Index Performance Summary**  
   - Summarize market indices in smooth spoken language.  
   - Example: “The S&P 500 edged higher today, rising half a percent…”

3. **Key Headlines**  
   - Read 3–6 key themes as short, natural sentences.  
   - Combine or group related news stories.

4. **Market Commentary**  
   - Provide a brief, natural-sounding explanation of what drove sentiment today.  
   - No speculation—summarize what the markdown already indicates.

5. **Closing Line**  
   - Simple professional sign-off.  
     e.g., “That’s the market briefing for today. Thanks for listening.”

GENERAL RULES:
- The script MUST be easy for a TTS model to read aloud.
- Do not include timestamps, metadata, URLs, or source names unless included in the briefing.
- Avoid very long sentences. Break them into shorter phrases suitable for audio.
- If the markdown contains tables or percentages, convert them into natural language.
- If something is unclear in the briefing, phrase it cautiously:  
  “The report notes…”, “According to the summary…”

"""

# The TTS model to use
MODEL_ID = "gemini-2.5-flash-preview-tts"

# The audio parameters returned by the model
# The standard output rate for the Gemini TTS models is 24000 Hz.
AUDIO_CHANNELS = 1
AUDIO_RATE = 24000
SAMPLE_WIDTH = 2 # 2 bytes for 16-bit audio (16 / 8 = 2)

# --- Helper Function to Save WAV File ---
def save_wave_file(filename: str, pcm_data: bytes, channels: int, rate: int, sample_width: int):
    """Saves raw PCM audio data into a standard WAV file."""
    print(f"Saving audio to {filename}...")
    try:
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
        print(f"✅ Success! Audio file saved as {filename}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

def generate_script(daily_brief:str, use_existing:bool = True):
    today = date.today().isoformat()
    base_dir = Path(__file__).resolve().parents[2] / "data" / "daily_brief"
    base_dir.mkdir(parents=True, exist_ok=True)
    script_path = base_dir / f"{today}-daily-briefing-script.txt"
    if script_path.exists() and use_existing:
        with open(script_path, "r") as f:
            return f.read()
    
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=daily_brief,
        config={"system_instruction":SCRIPT_PROMPT}
    )
    script = response.text
    with open(script_path, "w") as f:
        f.write(script)
    return script

# --- Main Generation Logic ---
def synthesize_speech(script:str):
    
    today = date.today().isoformat()
    base_dir = Path(__file__).resolve().parents[2] / "data" / "daily_brief" / "voice"
    base_dir.mkdir(parents=True, exist_ok=True)
    save_file_path = base_dir / f"{today}-daily-briefing.wav"
    # 1. Initialize the client
    client = genai.Client()

    # 2. Configure the request for audio output
    config = types.GenerateContentConfig(
        # The key setting to request audio instead of text
        response_modalities=["AUDIO"],
        # Optional: You can specify a voice name here for more control.
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name='Alnilam'
                    )
            )
        )
    )

    print(f"Generating voice using model: {MODEL_ID}...")

    # 3. Call generate_content with the prompt and audio config
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=script,
        config=config
    )

    # 4. Extract the raw audio data
    try:
        # The raw audio data is in the first part of the first candidate's content
        inline_data = response.candidates[0].content.parts[0].inline_data
        audio_data = inline_data.data
        
        # 5. Save the data to a WAV file
        save_wave_file(
            filename=str(save_file_path),
            pcm_data=audio_data,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            sample_width=SAMPLE_WIDTH
        )

    except IndexError:
        print("❌ Error: Could not find audio data in the response. The prompt may have been blocked or the configuration was incorrect.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


if __name__ == "__main__":
    test_script = "The DJI maintains a strong multi-timeframe uptrend, backed by robust bullish momentum indicators. While recent volume on upside moves is moderate, it doesn't detract from the established trend's strength. Expanding volatility implies larger moves, requiring careful risk management. The overall technical structure suggests continued upside, targeting the year high and potentially beyond. Long positions are favored, with accumulation on minor pullbacks or confirmed breakouts offering the best risk-reward opportunities for mid-to-long term investors."
    synthesize_speech(test_script)
