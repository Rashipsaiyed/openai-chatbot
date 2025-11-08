import tkinter as tk
from tkinter import ttk, scrolledtext
from openai import OpenAI
from dotenv import load_dotenv
import os, requests, re, json, webbrowser

# --------------------------
# SETUP
# --------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
HISTORY_FILE = "chat_history.json"
CATEGORIES = ["business", "entertainment", "general", "health", "science", "sports", "technology"]
chat_history = []

# --------------------------
# UTILITIES
# --------------------------
def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=2)

def get_news(topic="latest"):
    topic_lower = topic.lower().strip()
    if topic_lower in CATEGORIES:
        url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=5&category={topic_lower}&apiKey={NEWS_API_KEY}"
    else:
        query = topic.replace(" ", "+")
        url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=5&q={query}&apiKey={NEWS_API_KEY}"

    response = requests.get(url).json()
    if response.get("status") != "ok":
        return f"⚠️ Error fetching news: {response.get('message', 'Unknown error')}"

    articles = response.get("articles", [])
    if not articles:
        return f"❌ No recent news found for '{topic}'."

    result = []
    for i, a in enumerate(articles, 1):
        title = a.get("title", "No title")
        source = a.get("source", {}).get("name", "")
        url = a.get("url", "")
        result.append({"index": i, "title": title, "source": source, "url": url})
    return result

def get_weather(city):
    if not WEATHER_API_KEY:
        return "⚠️ WEATHER_API_KEY missing."
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    resp = requests.get(url).json()
    if resp.get("cod") != 200:
        return f"❌ No weather found for '{city}'."
    name = resp.get("name")
    country = resp.get("sys", {}).get("country")
    temp = resp.get("main", {}).get("temp")
    desc = resp.get("weather")[0].get("description")
    humidity = resp.get("main", {}).get("humidity")
    wind = resp.get("wind", {}).get("speed")
    return (f"🌤️ Weather in {name}, {country}:\n"
            f"Temperature: {temp}°C\nCondition: {desc}\n"
            f"Humidity: {humidity}%\nWind Speed: {wind} m/s")

def detect_topic(user_input):
    user_lower = user_input.lower()
    ignore_words = ["show", "me", "give", "please", "recent", "latest", "some", "top", "the", "news"]
    for w in ignore_words:
        user_lower = user_lower.replace(w, "")
    user_lower = user_lower.strip()
    for cat in CATEGORIES:
        if cat in user_lower:
            return cat
    words = user_lower.split()
    return " ".join(words) if words else "latest"

def detect_city(user_input):
    match = re.search(r"(?:in|at)\s+([A-Za-z\s]+)", user_input.lower())
    if match:
        return match.group(1).strip()
    return None

# --------------------------
# GUI FUNCTIONS
# --------------------------
def open_link(event):
    tag = event.widget.tag_names(tk.CURRENT)[0]
    if tag.startswith("link_"):
        url = tag.split("_", 1)[1]
        webbrowser.open(url)

def append_chat(text, sender="bot", links=None):
    chat_window.configure(state='normal')
    if sender == "bot":
        chat_window.insert(tk.END, "🤖 Bot:\n", 'bot_name')
        if links:
            chat_window.insert(tk.END, f"📰 Top News\n\n", 'title')
            for article in links:
                chat_window.insert(tk.END, f"{article['index']}. {article['title']} ({article['source']})\n", 'bot_text')
                tag_name = f"link_{article['url']}"
                chat_window.insert(tk.END, f"🔗 Open Article\n\n", (tag_name,))
                chat_window.tag_config(tag_name, foreground="#0077cc", underline=True)
                chat_window.tag_bind(tag_name, "<Button-1>", open_link)
        else:
            chat_window.insert(tk.END, text + "\n\n", 'bot_text')
    else:
        chat_window.insert(tk.END, f"🧑 You: {text}\n\n", 'user_text')
    chat_window.configure(state='disabled')
    chat_window.see(tk.END)

def send_message():
    user_text = entry.get().strip()
    if not user_text:
        return
    append_chat(user_text, sender="user")
    entry.delete(0, tk.END)

    if user_text.lower() in ["exit", "quit"]:
        root.destroy()
        return
    elif user_text.lower() in ["clear memory", "reset chat"]:
        chat_window.configure(state='normal')
        chat_window.insert(tk.END, "🧹 Chat history cleared.\n", 'bot_text')
        chat_window.configure(state='disabled')
        chat_history.clear()
        save_history()
        return
    elif user_text.lower() == "history":
        if not chat_history:
            append_chat("No previous searches.", sender="bot")
        else:
            text = "📜 Previous searches:\n" + "\n".join([item['topic'] for item in chat_history])
            append_chat(text, sender="bot")
        return

    if "weather" in user_text.lower():
        city = detect_city(user_text)
        if city:
            reply = get_weather(city)
            chat_history.append({"topic": f"weather:{city}", "response": reply})
            save_history()
            append_chat(reply, sender="bot")
        else:
            append_chat("❌ Please specify a city, e.g., 'Weather in Mumbai'.", sender="bot")
        return

    elif "news" in user_text.lower():
        topic = detect_topic(user_text)
        news_articles = get_news(topic)
        if isinstance(news_articles, str):
            append_chat(news_articles, sender="bot")
        else:
            append_chat("", sender="bot", links=news_articles)
        chat_history.append({"topic": topic, "response": "news"})
        save_history()
        return

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides news and weather updates."},
            {"role": "user", "content": user_text}
        ],
    )
    reply = response.choices[0].message.content
    chat_history.append({"topic": "chat", "user": user_text, "response": reply})
    save_history()
    append_chat(reply, sender="bot")

# --------------------------
# GUI LAYOUT (Compact Version)
# --------------------------
root = tk.Tk()
root.title("🧠 Smart News & Weather Chatbot")
root.geometry("900x550")
root.configure(bg="#f0f4f8")

style = ttk.Style()
style.configure("TNotebook.Tab", padding=[10, 6], font=("Segoe UI", 11, "bold"))
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
style.configure("TFrame", background="#f0f4f8")

notebook = ttk.Notebook(root)
notebook.pack(padx=10, pady=10, fill='both', expand=True)

chat_frame = ttk.Frame(notebook)
notebook.add(chat_frame, text="💬 Chat")

# Reduced height here ↓↓↓
chat_window = scrolledtext.ScrolledText(
    chat_frame, wrap=tk.WORD, width=90, height=18,
    state='disabled', bg="#ffffff", font=("Segoe UI", 10)
)
chat_window.pack(padx=10, pady=10, fill='both', expand=True)
chat_window.tag_config('user_text', foreground="#0066cc")
chat_window.tag_config('bot_name', foreground="#009933", font=("Segoe UI", 10, "bold"))
chat_window.tag_config('bot_text', foreground="#333333", font=("Segoe UI", 10))
chat_window.tag_config('title', foreground="#0055aa", font=("Segoe UI", 11, "bold"))

bottom_frame = ttk.Frame(chat_frame)
bottom_frame.pack(fill='x', padx=10, pady=(0, 10))

entry = ttk.Entry(bottom_frame, width=80, font=("Segoe UI", 10))
entry.pack(side=tk.LEFT, padx=(0, 5))
entry.bind("<Return>", lambda e: send_message())

send_button = ttk.Button(bottom_frame, text="Send 🚀", command=send_message)
send_button.pack(side=tk.LEFT)

topic_frame = ttk.Frame(chat_frame)
topic_frame.pack(pady=(3, 10))
for topic in ["Technology", "Sports", "Health", "Business"]:
    btn = ttk.Button(topic_frame, text=topic, width=14,
                     command=lambda t=topic.lower(): (entry.delete(0, tk.END), entry.insert(0, f"Show me {t} news"), send_message()))
    btn.pack(side=tk.LEFT, padx=5)

append_chat("👋 Hello! I can show you the latest news or weather. Try 'Technology news' or 'Weather in Delhi'.", sender="bot")
root.mainloop()
