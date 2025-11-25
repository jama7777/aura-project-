import ollama
import chromadb
import os

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
    
    if not text:
        return "I didn't catch that."

    query = f"User said: {text}, emotion: {emotion}"
    
    context = ""
    if collection:
        try:
            results = collection.query(query_texts=[query], n_results=2)
            if results['documents']:
                context = "\n".join(results['documents'][0])
        except Exception as e:
            print(f"Error querying memory: {e}")
    
    prompt = f"You are AURA, a kind friend. Use context: {context}. Respond empathetically and suggest actions if needed. Keep it short."
    
    try:
        # Check if ollama is reachable (simple check)
        # For now, just try generate
        response_obj = ollama.generate(model="llama3.1", prompt=prompt + "\n" + query)
        response = response_obj['response']
    except Exception as e:
        print(f"Error generating response from Ollama: {e}")
        return "I'm having trouble thinking right now. Is my brain (Ollama) running?"
    
    if collection:
        try:
            collection.add(documents=[query + " -> " + response], ids=[str(hash(query))])
        except Exception as e:
            print(f"Error saving to memory: {e}")
            
    return response