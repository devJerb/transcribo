import os
import streamlit as st
import speech_recognition as sr
from uuid import uuid4
from pydub import AudioSegment
from typing import List, Optional
import tempfile
import gc
import shutil
from pydub.utils import which


AudioSegment.converter = "./ffmpeg"
AudioSegment.ffprobe = "./ffprobe"


def create_temp_dir() -> str:
    return tempfile.mkdtemp(prefix="transcribo_")


def extract_audio(video_file: str, temp_dir: str) -> Optional[str]:
    try:
        st.info("Extracting audio from video...")
        audio_path = os.path.join(temp_dir, f"{uuid4()}.wav")
        audio = AudioSegment.from_file(video_file)
        audio.export(audio_path, format="wav")
        st.success("Audio extraction completed.")
        return audio_path
    except Exception as e:
        st.error(f"Unable to extract audio: {e}")
        return None


def to_chunks(audio_file: str, chunk_length_ms: int, temp_dir: str) -> List[str]:
    try:
        audio = AudioSegment.from_wav(audio_file)
        chunks = []
        for i, chunk in enumerate(audio[::chunk_length_ms]):
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
        return chunks
    except Exception as e:
        st.error(f"Unable to create chunks: {e}")
        return []


def transcribe_audio(audio_file: str) -> str:
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return "[Inaudible]"
    except sr.RequestError as e:
        st.error(f"Google API request failed: {e}")
    except Exception as e:
        st.error(f"Transcription failed: {e}")
    return "[Error]"


def clean_temp_dir(temp_dir: str):
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        st.error(f"Error cleaning temporary directory: {e}")


def main():
    st.set_page_config(page_title="Transcribo")
    st.info(
        "Available for videos that have a duration of less than 1 hour and 30 minutes."
    )
    st.title("Video to Text Transcription 📠")
    st.write("Upload a video file, and it will be transcribed to text.")

    temp_dir = create_temp_dir()

    video_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"])

    if video_file is not None:
        try:
            temp_video_path = os.path.join(temp_dir, f"{uuid4()}.mp4")
            with open(temp_video_path, "wb") as temp_video:
                temp_video.write(video_file.getbuffer())

            # Check video duration (Optional: Remove if duration check isn't required)
            st.video(temp_video_path)

            st.write("Step 1: Extracting Audio")
            audio_path = extract_audio(temp_video_path, temp_dir)
            if not audio_path:
                st.error("Failed to extract audio.")
                return

            st.write("Step 2: Splitting Audio into Chunks")
            with st.spinner("Splitting audio into chunks..."):
                audio_chunks = to_chunks(
                    audio_path, 30000, temp_dir
                )  # 30 second chunks
                if audio_chunks:
                    st.success(f"Audio split into {len(audio_chunks)} chunks. 🧩")
                else:
                    st.error("Failed to split audio into chunks.")
                    return

            st.write("Step 3: Transcribing Audio Chunks")
            transcription_placeholder = st.empty()
            transcription_result = []

            transcription_progress = st.progress(0)
            transcription_status = st.empty()

            for i, chunk in enumerate(audio_chunks):
                progress = (i + 1) / len(audio_chunks)
                transcription_progress.progress(
                    progress, f"Transcribing chunk {i + 1} / {len(audio_chunks)}"
                )

                chunk_transcription = transcribe_audio(chunk)
                transcription_result.append(chunk_transcription)

                transcription_placeholder.text_area(
                    "Transcription Result (real-time)",
                    " ".join(transcription_result),
                    height=300,
                )

                # Clean up chunk file
                os.remove(chunk)
                gc.collect()

            transcription_status.success("Transcription completed. 🚀")

        except Exception as e:
            st.error(f"An error occurred: {e}")

        finally:
            # Clean up temporary files
            clean_temp_dir(temp_dir)
            gc.collect()


if __name__ == "__main__":
    main()
