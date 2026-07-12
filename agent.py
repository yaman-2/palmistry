import os
# Load environment variables from local .env file if it exists
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                try:
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val
                except ValueError:
                    pass
import re
import sqlite3
import sys
import uuid
import pandas as pd
import numpy as np
import cv2
import requests
from PIL import Image
from mistralai import Mistral
import base64
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CHUNKS_CSV_FILE = os.path.join(DATA_DIR, "youtube_semantic_chunks.csv")
ASTRO_CSV_FILE = os.path.join(DATA_DIR, "astrologylinkdata.csv")

# ==========================================
# Common Helpers
# ==========================================
def get_mistral_client():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None
    try:
        return Mistral(api_key=api_key)
    except Exception as e:
        return None

# ==========================================
# Core Logic: Option 1
# ==========================================
def get_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
        if parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    raise ValueError("Invalid YouTube URL")

def get_metadata(url):
    ydl_opts = {'quiet': True, 'extract_flat': True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', 'Unknown Title'),
            'channel': info.get('channel', 'Unknown Channel')
        }

def get_transcript(video_id):
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        # Priority 1: Manually created transcripts (highest accuracy)
        try:
            transcript = transcript_list.find_manually_created_transcript(['hi', 'en', 'en-US', 'en-GB', 'en-IN'])
        except Exception:
            # Priority 2: Auto-generated transcripts
            try:
                transcript = transcript_list.find_generated_transcript(['hi', 'en', 'en-US', 'en-GB', 'en-IN'])
            except Exception:
                # Priority 3: Fallback to any transcript available
                transcript = next(iter(transcript_list))
                
        def get_text(t):
            fetched = t.fetch()
            return " ".join([snippet['text'] if isinstance(snippet, dict) else snippet.text for snippet in fetched])
            
        en_text = ""
        hi_text = ""
        
        try:
            if transcript.language_code.startswith('en'):
                en_text = get_text(transcript)
            else:
                en_text = get_text(transcript.translate('en'))
        except Exception:
            pass
            
        try:
            if transcript.language_code.startswith('hi'):
                hi_text = get_text(transcript)
            else:
                hi_text = get_text(transcript.translate('hi'))
        except Exception:
            pass
            
        return {"en": en_text, "hi": hi_text}
    except Exception as e:
        return None

async def correct_transcript(text, language="English"):
    if not text or not text.strip():
        return text
    
    client = get_mistral_client()
    if not client:
        return text
        
    system_prompt = (
        f"You are an expert in Astrology. I will provide an auto-generated {language} transcript of an astrology video. "
        "It contains spelling mistakes, misheard words, and incorrect jargon related to astrology (like planets, rashis, doshas, etc.). "
        "Your ONLY task is to return the exact same transcript, but with all mistakes corrected. "
        "DO NOT summarize. DO NOT translate. Keep the original language and length. DO NOT add conversational text. Just output the corrected text."
    )
    
    try:
        response = await client.chat.complete_async(
            model='mistral-large-latest',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return text

async def process_youtube(url):
    try:
        video_id = get_video_id(url)
    except ValueError as e:
        return {"error": str(e)}

    try:
        metadata = get_metadata(url)
        title = metadata['title']
        channel = metadata['channel']
    except Exception as e:
        title = "Unknown"
        channel = "Unknown"
    
    transcripts = get_transcript(video_id)
    if not transcripts or (not transcripts['en'] and not transcripts['hi']):
        return {"error": "Could not retrieve transcript. The video might not have captions."}

    en_transcript = transcripts['en']
    hi_transcript = transcripts['hi']

    if en_transcript:
        en_transcript = await correct_transcript(en_transcript, "English")
    if hi_transcript:
        hi_transcript = await correct_transcript(hi_transcript, "Hindi")

    new_data = {
        'URL': [url],
        'Video ID': [video_id],
        'Title': [title],
        'Channel': [channel],
        'Transcript': [en_transcript if en_transcript else hi_transcript],
        'Transcript_EN': [en_transcript],
        'Transcript_HI': [hi_transcript]
    }
    df_new = pd.DataFrame(new_data)

    if os.path.exists(ASTRO_CSV_FILE):
        df_existing = pd.read_csv(ASTRO_CSV_FILE)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(ASTRO_CSV_FILE, index=False)
    return {"success": True, "title": title, "saved_to": ASTRO_CSV_FILE}

# ==========================================
# Core Logic: Option 2
# ==========================================
def find_best_chunk(query):
    if not os.path.exists(CHUNKS_CSV_FILE):
        return None, "Chunks CSV not found. Please ensure Option 1 with chunking was run previously."
    df = pd.read_csv(CHUNKS_CSV_FILE)
    if df.empty:
        return None, "No chunks found in CSV."
        
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_emb = model.encode([query])[0]
    chunk_texts = df['Text'].tolist()
    chunk_embs = model.encode(chunk_texts)
    similarities = cosine_similarity([query_emb], chunk_embs)[0]
    best_idx = np.argmax(similarities)
    return df.iloc[best_idx], None

def extract_frames_from_local(video_path, start_time, end_time, max_frames=8):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30
    
    start_frame = int(max(0, start_time - 1) * fps)
    end_frame = int((end_time + 1) * fps)
    total_segment_frames = end_frame - start_frame
    if total_segment_frames <= 0: return []
        
    step = max(1, total_segment_frames // max_frames)
    frames = []
    
    for i in range(start_frame, end_frame, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            frames.append(pil_img)
        if len(frames) >= max_frames:
            break
    cap.release()
    return frames

async def query_local_video(query, video_path):
    if not os.path.exists(video_path):
        return {"error": "Video file not found!"}

    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set."}

    best_chunk, err = find_best_chunk(query)
    if err:
        return {"error": err}
    
    start_time = float(best_chunk['Start_Time'])
    end_time = float(best_chunk['End_Time'])
    chunk_text = best_chunk['Text']
    
    chunk_text = await correct_transcript(chunk_text, "Hindi or English")
    
    frames = extract_frames_from_local(video_path, start_time, end_time, max_frames=10)
    gif_path = os.path.join(DATA_DIR, "output.gif")
    
    if frames:
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=300, loop=0)
    
    system_prompt = (
        "You are a strict AI assistant analyzing a specific segment of a video. "
        "You MUST answer using ONLY the provided transcript and visual context. "
        "If the question cannot be answered using the provided context, you MUST refuse to answer and say exactly: 'Main sirf is video ke context se hi answer de sakta hu.' "
        "Do not use your general knowledge."
    )
    prompt_text = (
        f"The user's question is: '{query}'\n"
        f"Here is the spoken transcript for this segment:\n\"{chunk_text}\"\n"
        "I have also provided a sequence of frames from this exact segment."
    )
    
    content = [{"type": "text", "text": prompt_text}]
    import io
    for frame in frames:
        buffered = io.BytesIO()
        frame.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        content.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_str}"})
    
    try:
        response = await client.chat.complete_async(
            model='pixtral-12b-2409',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            temperature=0.0
        )
        return {
            "success": True, 
            "answer": response.choices[0].message.content, 
            "context_preview": chunk_text[:200],
            "gif_saved_at": gif_path if frames else None
        }
    except Exception as e:
        return {"error": f"Error querying Mistral: {str(e)}"}

async def query_local_videos_batch(query, video_paths):
    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set."}

    best_chunk, err = find_best_chunk(query)
    if err:
        return {"error": err}
    
    start_time = float(best_chunk['Start_Time'])
    end_time = float(best_chunk['End_Time'])
    chunk_text = best_chunk['Text']
    
    chunk_text = await correct_transcript(chunk_text, "Hindi or English")
    
    system_prompt = (
        "You are a strict AI assistant analyzing a specific segment of a video. "
        "You MUST answer using ONLY the provided transcript and visual context. "
        "If the question cannot be answered using the provided context, you MUST refuse to answer and say exactly: 'Main sirf is video ke context se hi answer de sakta hu.' "
        "Do not use your general knowledge."
    )
    
    results = []
    for idx, path in enumerate(video_paths):
        if not os.path.exists(path):
            results.append({"video": path, "error": "Video file not found!"})
            continue
            
        frames = extract_frames_from_local(path, start_time, end_time, max_frames=10)
        gif_path = os.path.join(DATA_DIR, f"output_batch_{idx}.gif")
        
        if frames:
            frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=300, loop=0)
        
        prompt_text = (
            f"The user's question is: '{query}'\n"
            f"Here is the spoken transcript for this segment:\n\"{chunk_text}\"\n"
            "I have also provided a sequence of frames from this exact segment."
        )
        content = [{"type": "text", "text": prompt_text}]
        import io
        for frame in frames:
            buffered = io.BytesIO()
            frame.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            content.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_str}"})
        
        try:
            response = await client.chat.complete_async(
                model='pixtral-12b-2409',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.0
            )
            results.append({
                "video": path,
                "success": True, 
                "answer": response.choices[0].message.content, 
                "gif_saved_at": gif_path if frames else None
            })
        except Exception as e:
            results.append({"video": path, "error": f"Error querying Mistral: {str(e)}"})
            
    return {
        "success": True, 
        "results": results, 
        "context_preview": chunk_text[:200]
    }

# ==========================================
# Core Logic: Option 3
# ==========================================
async def qa_open_source(query):
    if not os.path.exists(ASTRO_CSV_FILE):
        return {"error": f"{ASTRO_CSV_FILE} not found."}
        
    df = pd.read_csv(ASTRO_CSV_FILE)
    if df.empty:
        return {"error": "No data found in CSV."}
        
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_emb = model.encode([query])[0]
    
    all_chunks = []
    chunk_sources = []
    
    for idx, row in df.iterrows():
        transcript = str(row['Transcript'])
        if pd.isna(transcript) or not transcript.strip() or transcript.lower() == 'none':
            continue
        words = transcript.split()
        chunk_size = 300
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            all_chunks.append(chunk)
            chunk_sources.append(row['Title'])
            
    if not all_chunks:
        return {"error": "No transcripts found to search."}
        
    chunk_embs = model.encode(all_chunks)
    similarities = cosine_similarity([query_emb], chunk_embs)[0]
    top_indices = np.argsort(similarities)[-3:][::-1]
    
    context = ""
    for idx in top_indices:
        context += f"Source ({chunk_sources[idx]}): {all_chunks[idx]}\n\n"
        
    system_prompt = (
        "You are a strict AI assistant. Your ONLY job is to answer the user's question based strictly on the provided Context.\n"
        "IMPORTANT RULES:\n"
        "1. If the answer is not in the context, you MUST say exactly: 'Main sirf video ke context se hi answer de sakta hu.'\n"
        "2. DO NOT use your general knowledge to answer.\n"
        "3. DO NOT answer general or outside queries.\n"
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n"
    
    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set in .env."}
        
    import asyncio
    for attempt in range(3):
        try:
            response = await client.chat.complete_async(
                model='mistral-large-latest',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            return {
                "success": True, 
                "answer": response.choices[0].message.content,
                "context_preview": context[:200]
            }
        except Exception as e:
            if attempt == 2:
                return {"error": f"Error querying Mistral: {str(e)}"}
            print(f"Mistral API attempt {attempt+1} failed: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3)


# ==========================================
# Core Logic: Option 4 (Document Q&A)
# ==========================================
import io
async def qa_document(file_bytes, filename, query):
    text_content = ""
    
    # 1. Parse File
    if filename.lower().endswith('.txt') or filename.lower().endswith('.csv'):
        text_content = file_bytes.decode('utf-8', errors='ignore')
    elif filename.lower().endswith('.pdf'):
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        except ImportError:
            return {"error": "PyPDF2 is not installed. Run 'pip install PyPDF2' to process PDFs."}
        except Exception as e:
            return {"error": f"Error reading PDF: {e}"}
    else:
        return {"error": "Unsupported file format. Please upload .txt, .pdf, or .csv files."}
        
    if not text_content.strip():
        return {"error": "The document is empty or text could not be extracted."}
        
    return await qa_text(text_content, query)

async def qa_text(text_content, query):
    if not text_content.strip():
        return {"error": "The provided text is empty."}

    # 2. Chunking & Semantic Search
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_emb = model.encode([query])[0]
    
    words = text_content.split()
    chunk_size = 300
    all_chunks = []
    
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        all_chunks.append(chunk)
        
    chunk_embs = model.encode(all_chunks)
    similarities = cosine_similarity([query_emb], chunk_embs)[0]
    top_indices = np.argsort(similarities)[-3:][::-1]
    
    context = ""
    for idx in top_indices:
        context += f"Document Snippet: {all_chunks[idx]}\n\n"
        
    system_prompt = (
        "You are a strict AI assistant. Your ONLY job is to answer the user's question based strictly on the provided Document Context.\n"
        "IMPORTANT RULES:\n"
        "1. If the answer is not in the context, you MUST say exactly: 'Main sirf diye gaye context se hi answer de sakta hu.'\n"
        "2. DO NOT use your general knowledge to answer.\n"
        "3. DO NOT answer general or outside queries.\n"
    )
    user_prompt = f"Document Context:\n{context}\n\nQuestion: {query}\n"
    
    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set in .env."}
        
    import asyncio
    for attempt in range(3):
        try:
            response = await client.chat.complete_async(
                model='mistral-large-latest',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            return {
                "success": True, 
                "answer": response.choices[0].message.content,
                "context_preview": context[:200]
            }
        except Exception as e:
            if attempt == 2:
                return {"error": f"Error querying Mistral: {str(e)}"}
            print(f"Mistral API attempt {attempt+1} failed: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3)

# ==========================================
# Core Logic: Option 6 (Visual Palm Reading)
# ==========================================
_clip_model = None

def get_clip_model():
    global _clip_model
    if _clip_model is None:
        _clip_model = SentenceTransformer('clip-ViT-B-32')
    return _clip_model

def load_reference_data():
    csv_path = os.path.join(DATA_DIR, "palm_references", "context.csv")
    images_dir = os.path.join(DATA_DIR, "palm_references", "images")
    if not os.path.exists(csv_path):
        return None, "Reference context.csv not found."
    df = pd.read_csv(csv_path)
    
    reference_images = []
    contexts = []
    
    for idx, row in df.iterrows():
        img_name = str(row['Image_Name']).strip()
        context = str(row['Context']).strip()
        img_path = os.path.join(images_dir, img_name)
        if os.path.exists(img_path):
            reference_images.append(Image.open(img_path).convert("RGB"))
            contexts.append(context)
            
    if not reference_images:
        return None, "No valid reference images found in the directory."
        
    return {"images": reference_images, "contexts": contexts}, None

async def qa_palm_images(user_image_paths):
    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set."}
        
    ref_data, err = load_reference_data()
    if err:
        return {"error": err}
        
    model = get_clip_model()
    ref_embs = model.encode(ref_data["images"])
    
    user_images = []
    for p in user_image_paths:
        if os.path.exists(p):
            user_images.append(Image.open(p).convert("RGB"))
            
    if not user_images:
        return {"error": "No valid user images provided."}
        
    user_embs = model.encode(user_images)
    
    retrieved_contexts = set()
    for u_emb in user_embs:
        similarities = cosine_similarity([u_emb], ref_embs)[0]
        best_idx = np.argmax(similarities)
        retrieved_contexts.add(ref_data["contexts"][best_idx])
        
    combined_context = "\n- " + "\n- ".join(retrieved_contexts)
    
    system_prompt = (
        "You are an expert Palmistry reader. "
        "I will provide you with several images of the user's palms, along with some retrieved astrological context based on visual similarity to our database. "
        "Your task is to analyze the provided images carefully and generate a comprehensive, accurate palm reading, incorporating the insights from the provided context."
    )
    
    prompt_text = "Here is the retrieved context based on visual patterns matched in the user's hands:\n" + combined_context + "\nHere are the user's hand images. Please provide a detailed palm reading based on these patterns."
    
    content = [{"type": "text", "text": prompt_text}]
    import io
    for img in user_images:
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        content.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_str}"})
    
    try:
        response = await client.chat.complete_async(
            model='pixtral-12b-2409',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            temperature=0.2
        )
        return {
            "success": True, 
            "answer": response.choices[0].message.content, 
            "matched_context": combined_context
        }
    except Exception as e:
        return {"error": f"Error querying Mistral: {str(e)}"}


# ==========================================
# CLI Wrappers
# ==========================================
def option1_process_youtube():
    print("\n--- Process YouTube URL ---")
    url = input("Enter YouTube Video URL: ").strip()
    if not url:
        print("URL cannot be empty.")
        return
    print("Processing...")
    res = process_youtube(url)
    if "error" in res:
        print(f"Error: {res['error']}")
    else:
        print(f"\nSuccess! Data saved to {res['saved_to']}")

def option2_process_local_video():
    print("\n--- Query & Extract Local Video ---")
    query = input("Enter your question: ").strip()
    if not query: return
    video_path = input("Enter local video file path: ").strip().strip('\"\'')
    
    print("Processing...")
    res = query_local_video(query, video_path)
    if "error" in res:
        print(f"Error: {res['error']}")
    else:
        print(f"\n[Matched Context]: {res['context_preview']}...")
        if res.get('gif_saved_at'):
            print(f"GIF saved to {res['gif_saved_at']}")
        print("\n" + "="*50)
        print("GEMINI AI ANSWER:")
        print("="*50)
        print(res['answer'])
        print("="*50)

def option3_qa_open_source():
    print("\n--- Q&A on Saved Data (Local Open Source AI) ---")
    query = input("Enter your question: ").strip()
    if not query: return
    
    print("Processing (this may take a moment)...")
    res = qa_open_source(query)
    if "error" in res:
        print(f"Error: {res['error']}")
    else:
        print(f"\n[Matched Context Preview]: {res['context_preview']}...")
        print("\n" + "="*50)
        print("OLLAMA (Llama 3) ANSWER:")
        print("="*50)
        print(res['answer'])
        print("="*50)


# ==========================================
# Core Logic: Option 7 (Astrology Chat RAG)
# ==========================================
ASTROLOGY_BOOKS_DIR = os.path.join(DATA_DIR, "astrology_books")
os.makedirs(ASTROLOGY_BOOKS_DIR, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def get_astrology_context(query, max_chunks=3):
    if not os.path.exists(ASTROLOGY_BOOKS_DIR):
        return ""
    
    pdf_files = [f for f in os.listdir(ASTROLOGY_BOOKS_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        return ""
        
    all_text = ""
    for file in pdf_files:
        path = os.path.join(ASTROLOGY_BOOKS_DIR, file)
        all_text += extract_text_from_pdf(path)
        
    if not all_text.strip():
        return ""
        
    # Split by double newlines or single newlines
    paragraphs = [p.strip() for p in all_text.split("\n\n") if len(p.strip()) > 50]
    if not paragraphs:
        paragraphs = [p.strip() for p in all_text.split("\n") if len(p.strip()) > 50]
        
    if not paragraphs:
        return ""
        
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_emb = model.encode([query])[0]
        paragraph_embs = model.encode(paragraphs)
        similarities = cosine_similarity([query_emb], paragraph_embs)[0]
        top_indices = np.argsort(similarities)[-max_chunks:][::-1]
        
        matched = [paragraphs[idx] for idx in top_indices if similarities[idx] > 0.15]
        return "\n\n".join(matched)
    except Exception as e:
        print(f"Error doing semantic search: {e}")
        return all_text[:2000]

async def qa_astrology(user_info, query, history):
    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set."}
        
    context = get_astrology_context(query)
    
    system_prompt = (
        f"You are a professional Vedic Astrologer AI.\n"
        f"Client Birth Details:\n"
        f"- Name: {user_info['name']}\n"
        f"- Date of Birth: {user_info['dob']}\n"
        f"- Time of Birth: {user_info['time']}\n"
        f"- Place of Birth: {user_info['place']}\n\n"
    )
    if context:
        system_prompt += f"Relevant Astrological Reference Context:\n{context}\n\n"
        
    system_prompt += (
        "Instructions:\n"
        "- Provide a professional, warm, and spiritually guiding analysis.\n"
        "- Focus on Vedic astrology principles (e.g. planets, houses, transits) if relevant.\n"
        "- Answer the client's query directly based on their birth chart and the reference texts.\n"
        "- Keep responses concise and structured so they read beautifully in a chat interface.\n"
        "- Speak directly to the client (e.g., 'Your chart indicates...')."
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({
            "role": role,
            "content": msg["content"]
        })
        
    messages.append({
        "role": "user",
        "content": query
    })
    
    import asyncio
    for attempt in range(3):
        try:
            response = await client.chat.complete_async(
                model='mistral-large-latest',
                messages=messages,
                temperature=0.7
            )
            return {
                "success": True,
                "response": response.choices[0].message.content
            }
        except Exception as e:
            if attempt == 2:
                return {"error": f"Error querying Mistral: {str(e)}"}
            print(f"Mistral API attempt {attempt+1} failed: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3)

def extract_text_from_bytes(file_bytes):
    text_content = ""
    try:
        from pypdf import PdfReader
        pdf_reader = PdfReader(io.BytesIO(file_bytes))
        for page in pdf_reader.pages:
            t = page.extract_text()
            if t:
                text_content += t + "\n"
    except Exception as e:
        print(f"Error reading PDF from bytes: {e}")
    return text_content

async def qa_uploaded_documents(document_ids, query, history):
    client = get_mistral_client()
    if not client:
        return {"error": "MISTRAL_API_KEY environment variable not set."}
        
    # Get filenames mappings from DB to print pretty sources
    filename_map = {}
    try:
        init_docs_db()
        conn = sqlite3.connect(DB_DOCS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename FROM documents")
        rows = cursor.fetchall()
        conn.close()
        filename_map = {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"Error fetching filename map: {e}")

    all_paragraphs = []
    
    for doc_id in document_ids:
        doc_path = os.path.join(DATA_DIR, "uploaded_documents", f"{doc_id}.txt")
        if not os.path.exists(doc_path):
            continue
            
        with open(doc_path, "r", encoding="utf-8") as f:
            all_text = f.read()
            
        if not all_text.strip():
            continue
            
        filename = filename_map.get(doc_id, f"Document-{doc_id[:8]}")
        
        paragraphs = [p.strip() for p in all_text.split("\n\n") if len(p.strip()) > 50]
        if not paragraphs:
            paragraphs = [p.strip() for p in all_text.split("\n") if len(p.strip()) > 50]
            
        for p in paragraphs:
            all_paragraphs.append({
                "text": p,
                "source": filename
            })
            
    if not all_paragraphs:
        return {"error": "No document content found to search."}
        
    # Semantic Search Context Retrieval
    context = ""
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_emb = model.encode([query])[0]
        
        texts = [p["text"] for p in all_paragraphs]
        paragraph_embs = model.encode(texts)
        similarities = cosine_similarity([query_emb], paragraph_embs)[0]
        top_indices = np.argsort(similarities)[-5:][::-1] # select top 5 matches
        
        matched = []
        for idx in top_indices:
            if similarities[idx] > 0.15:
                item = all_paragraphs[idx]
                matched.append(f"Source ({item['source']}):\n{item['text']}")
                
        context = "\n\n".join(matched)
    except Exception as e:
        print(f"Error doing semantic search on uploaded documents: {e}")
        context = "\n\n".join([f"Source ({p['source']}):\n{p['text']}" for p in all_paragraphs[:3]])

    system_prompt = (
        "You are a helpful AI assistant tasked with answering questions about the provided documents.\n"
        "You MUST answer using ONLY the provided document contexts below.\n"
        "If you do not know the answer or if the answer is not in the context, be honest and state that the documents do not contain that information.\n\n"
    )
    if context:
        system_prompt += f"Document Reference Context:\n{context}\n\n"
        
    system_prompt += "Guidelines:\n- Be precise, direct, and reference the specific source filename where applicable (e.g. 'According to foundations.pdf...')."
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({
            "role": role,
            "content": msg["content"]
        })
        
    messages.append({
        "role": "user",
        "content": query
    })
    
    import asyncio
    for attempt in range(3):
        try:
            response = await client.chat.complete_async(
                model='mistral-large-latest',
                messages=messages,
                temperature=0.2
            )
            return {
                "success": True,
                "response": response.choices[0].message.content
            }
        except Exception as e:
            if attempt == 2:
                return {"error": f"Error querying Mistral: {str(e)}"}
            print(f"Mistral API attempt {attempt+1} failed: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3)

# ==========================================
# Persistent Document Chat SQLite DB
# ==========================================
DB_DOCS_PATH = os.path.join(DATA_DIR, "documents.db")

def init_docs_db():
    conn = sqlite3.connect(DB_DOCS_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            uploaded_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_document_to_db(doc_id, filename):
    try:
        init_docs_db()
        conn = sqlite3.connect(DB_DOCS_PATH)
        cursor = conn.cursor()
        import datetime
        uploaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT OR REPLACE INTO documents (id, filename, uploaded_at)
            VALUES (?, ?, ?)
        ''', (doc_id, filename, uploaded_at))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding document to DB: {e}")

def get_all_documents():
    try:
        init_docs_db()
        conn = sqlite3.connect(DB_DOCS_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, filename, uploaded_at FROM documents ORDER BY uploaded_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "filename": r[1], "uploaded_at": r[2]} for r in rows]
    except Exception as e:
        print(f"Error fetching documents: {e}")
        return []

# Run DB initialization on startup
init_docs_db()

def main():
    while True:
        print("\n===============================")
        print(" YouTube Agent - Main Menu")
        print("===============================")
        print("1. Process YouTube URL (Extract transcript)")
        print("2. Extract & Query Local Video (Create GIF from exact timestamp)")
        print("3. Q&A on Saved Data (Local Open Source AI - Llama 3)")
        print("4. Exit")
        choice = input("Select an option (1-4): ").strip()
        
        if choice == '1': option1_process_youtube()
        elif choice == '2': option2_process_local_video()
        elif choice == '3': option3_qa_open_source()
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
