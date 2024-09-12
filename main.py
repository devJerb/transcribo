import os
import gc
import psutil

import streamlit as st
import moviepy.editor as mp
import speech_recognition as sr

from uuid import uuid4
from pydub import AudioSegment
from typing import List, Optional


MEMORY_LIMIT_GB = 1


def create_temp_dir(directory: str = "./temp") -> str:
    if not os.path.exists(directory):
        os.mkdir(directory)
    return directory


def extract_audio(video_file: str, temp_dir: str) -> Optional[str]:
    """
    Extracts audio from the provided video file.

    Args:
        video_file (str): Path to the video file.
        temp_dir (str): Path to the temporary directory.

    Returns:
        Optional[str]: Path to the extracted audio file or None if failed.
    """
    try:
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")

        video = mp.VideoFileClip(video_file)
        audio_path = os.path.join(temp_dir, f"{str(uuid4())}.mp3")
        video.audio.write_audiofile(
            audio_path, codec="mp3", bitrate="64k"
        )  # Lower quality
        video.close()  # Free memory
        return audio_path
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"Unable to extract audio: {e}")
    return None


def check_memory_usage(limit_gb=1.5):
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    mem_in_gb = mem_info.rss / (1024**1)  # Convert to GB

    if mem_in_gb > limit_gb:
        st.error("Memory usage exceeded! Processing stopped to prevent crashes.")
        st.stop()


def to_chunks(audio_file: str, chunk_duration: int, temp_dir: str) -> List[str]:
    """
    Splits an audio file into smaller chunks.

    Args:
        audio_file (str): Path to the audio file.
        chunk_length_ms (float): Length of each chunk in milliseconds.
        temp_dir (str): Path to the temporary directory.

    Returns:
        List[str]: List of paths to audio chunks or empty list if failed.
    """
    try:
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Video file not found: {audio_file}")

        video = mp.VideoFileClip(audio_file)
        duration = video.duration  # Get the total duration of the video in seconds
        num_chunks = int(duration // chunk_duration) + 1
        chunks = []

        # Process each chunk
        for i in range(num_chunks):
            check_memory_usage(
                MEMORY_LIMIT_GB
            )  # Check memory before processing each chunk

            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, duration)

            # Extract a subclip from the video
            subclip = video.subclip(start_time, end_time)
            chunk_path = os.path.join(temp_dir, f"video_chunk_{i}.mp4")
            subclip.write_videofile(chunk_path, codec="libx264", audio_codec="aac")
            subclip.close()  # Free memory after processing the chunk
            gc.collect()  # Force garbage collection to free up memory

            chunks.append(chunk_path)

        video.close()  # Free memory after processing the entire video
        return chunks

    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"Unable to process video: {e}")
    return []


def transcribe_audio(audio_file: str) -> str:
    """
    Transcribes the provided audio file using Google Speech Recognition.

    Args:
        audio_file (str): Path to the audio file.

    Returns:
        str: Transcription result or '[Inaudible response]' if failed.
    """
    recognizer = sr.Recognizer()

    try:
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                print("Unable to understand inaudible response.")
            except sr.RequestError as e:
                print(f"Google API request failed: {e}")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"Transcription failed: {e}")

    return "[Inaudible response]"


def main():
    st.set_page_config(page_title="Transcribo")
    st.title("Video to Text Transcription 📠")
    st.write("Upload a video file, and it will be transcribed to text.")

    # Create the temp directory for storing files
    temp_dir = create_temp_dir()

    video_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"])

    if video_file is not None:
        temp_video = os.path.join(temp_dir, f"{str(uuid4())}.mp4")

        try:
            # Save the uploaded video temporarily
            with open(temp_video, "wb") as file:
                file.write(video_file.getbuffer())

            st.video(temp_video)

            # Extract audio and display progress
            with st.spinner("Extracting audio..."):
                audio_path = extract_audio(temp_video, temp_dir)
                if audio_path:
                    st.success("Audio extracted successfully. 🚀")
                else:
                    st.error("Failed to extract audio.")
                    return

            # Split audio into chunks
            with st.spinner("Splitting audio into chunks..."):
                audio_chunks = to_chunks(audio_path, 80000, temp_dir)
                if audio_chunks:
                    st.success(f"Audio split into {len(audio_chunks)} chunks. 🛰")
                else:
                    st.error("Failed to split audio into chunks.")
                    return

            transcription_placeholder = st.empty()
            transcription_result = ""

            # Transcribe each chunk
            for i, chunk in enumerate(audio_chunks):
                with st.spinner(f"Transcribing chunk {i + 1} / {len(audio_chunks)}..."):
                    chunk_transcription = transcribe_audio(chunk)
                    transcription_result += f"{chunk_transcription}"

                    # Update the placeholder per chunk progress
                    transcription_placeholder.text_area(
                        "Transcription Result (real-time)",
                        f"{transcription_result}.",
                        height=300,
                    )

            st.success("Transcription completed for all chunks. 🎇")

        except Exception as e:
            st.error(f"An error occurred: {e}")

        finally:
            # Clean up temporary files
            try:
                temp_files = os.listdir(temp_dir)
                for file in temp_files:
                    file_path = os.path.join(temp_dir, file)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                # Optionally remove the directory itself if empty
                if not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                print(f"Unable to clean up temporary data, {e}")


if __name__ == "__main__":
    main()
