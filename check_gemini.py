import os
key = os.environ.get("GEMINI_API_KEY")
print("key set:", bool(key), "| length:", len(key) if key else 0)
if key:
    from google import genai
    client = genai.Client(api_key=key)
    names = [m.name for m in client.models.list() if "gemini" in m.name.lower()]
    print(len(names), "Gemini models available. First 15:")
    for n in names[:15]:
        print("  ", n)