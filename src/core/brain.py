import ollama
import chromadb

client = chromadb.PersistentClient(path="./aura_memory.db")
collection = client.get_or_create_collection(name="user_memory")

def process_input(input_data):
    query = f"User said: {input_data['text']}, emotion: {input_data['emotion']}"
    results = collection.query(query_texts=[query], n_results=2)
    context = "\n".join(results['documents'][0]) if results['documents'] else ""
    
    prompt = f"You are AURA, a kind friend. Use context: {context}. Respond empathetically and suggest actions if needed."
    response = ollama.generate(model="llama3.1", prompt=prompt + query)['response']
    
    collection.add(documents=[query + " -> " + response], ids=[str(hash(query))])
    return response