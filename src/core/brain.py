import google.generativeai as genai
import chromadb
import os

# Configure Gemini
GENAI_API_KEY = "AIzaSyAyq1urrux5d0amkeyQ-XycxD37mR8YizY"
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
        "2. If the user makes a gesture (like thumbs_up, victory, open_palm), respond to it VISUALLY and emotionally. "
        "   - E.g., for 'victory', say 'Yay! Peace!' or 'You're doing great!'. "
        "   - E.g., for 'thumbs_up', say 'Awesome!'.\n"
        "3. LEARN from the user. Refer to the 'Memory Context' below to recall past details.\n"
        "4. Keep responses concise (1-2 sentences) and conversational."
    )
    
    full_prompt = (
        f"{system_instruction}\n\n"
        f"Memory Context:\n{context}\n\n"
        f"Current Situation:\n{query}\n"
        f"Response:"
    )
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response_obj = model.generate_content(full_prompt)
        response = response_obj.text
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL GEMINI ERROR: {e}")
        return "I'm having trouble connecting to my brain. Please check the server logs."
    
    # Save to memory
    if collection:
        try:
            # We save the interaction: Query -> Response
            memory_entry = f"{query} -> AURA: {response}"
            collection.add(documents=[memory_entry], ids=[str(hash(memory_entry))])
        except Exception as e:
            print(f"Error saving to memory: {e}")
            
    return response