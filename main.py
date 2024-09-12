import os
import streamlit as st
import moviepy.editor as mp
import speech_recognition as sr
from uuid import uuid4
from pydub import AudioSegment
from typing import List, Optional
import tempfile
import gc
import shutil


def create_temp_dir() -> str:
    temp_dir = "/temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir


def extract_audio(video_file: str, temp_dir: str) -> Optional[str]:
    try:
        with mp.VideoFileClip(video_file) as video:
            audio_path = os.path.join(temp_dir, f"{uuid4()}.wav")
            video.audio.write_audiofile(audio_path, codec="pcm_s16le")
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
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
    except Exception as e:
        st.error(f"Error cleaning temporary directory: {e}")


def main():
    st.set_page_config(page_title="Transcribo")
    st.title("Video to Text Transcription 📠")
    st.write("Upload a video file, and it will be transcribed to text.")

    temp_dir = create_temp_dir()

    video_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"])

    if video_file is not None:
        try:
            temp_video_path = os.path.join(temp_dir, f"{uuid4()}.mp4")
            with open(temp_video_path, "wb") as temp_video:
                temp_video.write(video_file.getbuffer())

            st.video(temp_video_path)

            with st.spinner("Extracting audio..."):
                audio_path = extract_audio(temp_video_path, temp_dir)
                if audio_path:
                    st.success("Audio chunk extracted successfully. 🧩")
                else:
                    st.error("Failed to extract audio.")
                    return

            with st.spinner("Splitting audio into chunks..."):
                audio_chunks = to_chunks(
                    audio_path, 30000, temp_dir
                )  # 30 second chunks
                if audio_chunks:
                    st.success(f"Audio split into {len(audio_chunks)} chunks. 🧩")
                else:
                    st.error("Failed to split audio into chunks.")
                    return

            transcription_placeholder = st.empty()
            transcription_result = []

            progress_bar = st.progress(0)
            for i, chunk in enumerate(audio_chunks):
                progress = (i + 1) / len(audio_chunks)
                progress_bar.progress(
                    progress, f"{i + 1} / {len(audio_chunks)} chunks completed"
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

            st.success("Transcription completed. 🚀")

        except Exception as e:
            st.error(f"An error occurred: {e}")

        finally:
            # Clean up temporary files
            clean_temp_dir(temp_dir)
            gc.collect()


if __name__ == "__main__":
    main()
