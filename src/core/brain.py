import google.generativeai as genai
import chromadb
import os

# Configure Gemini
# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("NV_API_KEY")

if not GENAI_API_KEY:
    # Fallback to provided key
    GENAI_API_KEY = "AIzaSyD38c0J_CDF4Mf-3TQPIASBQtd1yMJb4EY" 
    print("[WARNING] using fallback API key in brain.py")

genai.configure(api_key=GENAI_API_KEY)

# Initialize ChromaDB
try:
    client = chromadb.PersistentClient(path="./aura_memory.db")
    collection = client.get_or_create_collection(name="user_memory")
    print("Memory system initialized.")
except Exception as e:
    print(f"Error initializing memory: {e}")
    collection = None

def process_input(input_data):
    text = input_data.get('text', '')
    emotion = input_data.get('emotion', 'neutral')
    gesture = input_data.get('gesture', 'none')
    
    # Valid interaction check: Need at least text or a gesture
    if not text and (not gesture or gesture == 'none'):
        return "I didn't catch that."

    # Construct Query
    if text:
        user_input_desc = f"User said: \"{text}\""
    else:
        user_input_desc = "User processed a visual gesture."

    query = f"{user_input_desc} Emotion: {emotion}. Gesture: {gesture}."
    
    context = ""
    if collection:
        try:
            # Query memory
            results = collection.query(query_texts=[query], n_results=3)
            if results['documents']:
                context = "\n".join(results['documents'][0])
        except Exception as e:
            print(f"Error querying memory: {e}")
    
    # Improved System Prompt
    system_instruction = (
        "You are AURA, a highly intelligent and empathetic AI friend. "
        "You have eyes (camera) and ears (microphone). "
        "INTERACTION RULES:\n"
        "1. If the user speaks, respond naturally.\n"
        "2. VITAL: If 'Gesture' in input is NOT 'none', you MUST acknowledge it IMMEDIATELY in your text.\n"
        "   - 'victory' -> Say something like 'Peace!', 'Yay!', or 'You rock!'.\n"
        "   - 'thumbs_up' -> Say 'Awesome!', 'Great job!', or 'Liked it?'.\n"
        "   - 'open_palm' -> Say 'High five!', 'Hello!', or 'I see you!'.\n"
        "   - 'fist' -> Say 'Bump!', 'Power!', or 'Strong!'.\n"
        "3. EMOTION AWARENESS: You receive the user's emotion (e.g. 'happy', 'sad', 'angry', 'neutral').\n"
        "   - If 'happy', match the energy! \n"
        "   - If 'sad', be empathetic and ask what's wrong.\n"
        "   - If 'neutral', just chat normally.\n"
        "4. LEARN from the user. Refer to the 'Memory Context' below to recall past details.\n"
        "5. Keep responses concise (1-2 sentences) and conversational."
    )
    
    full_prompt = (
        f"{system_instruction}\n\n"
        f"Memory Context:\n{context}\n\n"
        f"Current Situation:\n{query}\n"
        f"Response:"
    )
    
    # Priority list of models to try
    # 1. 2.0 Flash Exp (Often separate quota)
    # 2. 2.0 Flash (Standard)
    # 3. 2.5 Flash (Newest)
    # 4. Pro Latest (Legacy fallback)
    candidates = [
        'gemini-2.0-flash-exp',
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-pro-latest'
    ]

    response = "I'm having trouble connecting."

    for model_name in candidates:
        try:
            # print(f"Trying model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            response_obj = model.generate_content(full_prompt)
            response = response_obj.text
            # If successful, break the loop
            break 
        except Exception as e:
            # print(f"Model {model_name} failed: {e}")
            error_str = str(e)
            if "429" in error_str:
                continue # Try next model
            if "404" in error_str:
                continue # Try next model
            # If it's a critical error (like safety), maybe stop or try next.
            continue
            
    # Save to memory
    if collection:
        try:
            # We save the interaction: Query -> Response
            memory_entry = f"{query} -> AURA: {response}"
            collection.add(documents=[memory_entry], ids=[str(hash(memory_entry))])
        except Exception as e:
            print(f"Error saving to memory: {e}")
            
    return response